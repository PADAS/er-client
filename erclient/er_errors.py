import json
from dataclasses import dataclass
from typing import Optional


def _as_string(value):
    return value if isinstance(value, str) else None


@dataclass(frozen=True)
class AuthError:
    """The token endpoint's last refusal, as far as we could make sense of it."""

    status_code: Optional[int] = None
    error: Optional[str] = None
    error_description: Optional[str] = None
    response_body: Optional[str] = None
    url: Optional[str] = None
    grant_type: Optional[str] = None

    @classmethod
    def from_token_response(cls, status_code, response_body, url, grant_type):
        """Build from a refused token response, taking the OAuth fields if present.

        A body that is not a JSON object, or one whose fields are not strings,
        simply means "no OAuth error" — the status is then all we have to go on.
        Never raises.
        """
        error = None
        error_description = None
        try:
            body = json.loads(response_body)
        except (TypeError, ValueError):
            body = None
        if isinstance(body, dict):
            error = _as_string(body.get('error'))
            error_description = _as_string(body.get('error_description'))

        return cls(
            status_code=status_code,
            error=error,
            error_description=error_description,
            response_body=response_body,
            url=url,
            grant_type=grant_type,
        )


class ERClientException(Exception):
    # Optional support for storing the status code, response body, and the
    # parsed Retry-After value from the server response
    def __init__(self, message=None, status_code=None, response_body=None, retry_after=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        # Seconds the server asked us to wait (parsed from the Retry-After
        # header); None when the header was absent or unparseable.
        self.retry_after = retry_after

    def __str__(self):
        base_message = super().__str__()
        status_info = f" (status_code={self.status_code})" if self.status_code else ""
        body_info = f" (response_body={self.response_body})" if self.response_body else ""
        return f"{base_message}{status_info}{body_info}"


class ERClientBadCredentials(ERClientException):
    pass


class ERClientPermissionDenied(ERClientException):
    pass


class ERClientBadRequest(ERClientException):
    pass


class ERClientRateLimitExceeded(ERClientException):
    pass


class ERClientInternalError(ERClientException):
    pass


class ERClientServiceUnreachable(ERClientException):
    pass


class ERClientNotFound(ERClientException):
    pass


# RFC 6749 section 5.2 error codes, plus access_denied from the device-code and
# authorization-code flows.
_OAUTH_ERROR_TO_EXCEPTION = {
    'invalid_grant': ERClientBadCredentials,
    'invalid_client': ERClientBadCredentials,
    'unauthorized_client': ERClientBadCredentials,
    'access_denied': ERClientBadCredentials,
    'invalid_request': ERClientBadRequest,
    'unsupported_grant_type': ERClientBadRequest,
    'invalid_scope': ERClientBadRequest,
}

# Only consulted when the body carries no OAuth error code: a token endpoint
# that answers with HTML or an empty body tells us nothing else.
_STATUS_TO_EXCEPTION = {
    400: ERClientBadRequest,
    401: ERClientBadCredentials,
    500: ERClientInternalError,
    502: ERClientServiceUnreachable,
    503: ERClientServiceUnreachable,
    504: ERClientServiceUnreachable,
}


def classify_token_error(auth_error):
    """Pick the exception class for a refused token request. Never raises.

    The OAuth ``error`` code in the body decides, since a token endpoint's
    status is not a reliable signal (RFC 6749 section 5.2 allows ``400`` or
    ``401`` for the same condition). Falls back to the status when the body was
    not OAuth-shaped, and to ``ERClientException`` when neither is recognized.
    """
    if auth_error is None:
        return ERClientException

    if auth_error.error:
        return _OAUTH_ERROR_TO_EXCEPTION.get(auth_error.error, ERClientException)

    return _STATUS_TO_EXCEPTION.get(auth_error.status_code, ERClientException)
