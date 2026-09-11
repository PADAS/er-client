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
    # Seconds the endpoint asked us to wait, from its Retry-After header; the
    # device-code poller reads it to honor a ``slow_down``.
    retry_after: Optional[int] = None

    @classmethod
    def client_refusal(cls, message, error, url, grant_type):
        """Build from our own pre-flight refusal, where no server was consulted.

        The server fields stay ``None`` — there is no status and no body,
        because nothing was sent. ``url`` and ``grant_type`` name the request
        we declined to make, and are themselves ``None`` in token mode, where
        there was no token request to begin with.

        ``error`` is one of the client-side pseudo-codes below, and the caller
        picks it: "these credentials cannot work here" and "there is no way to
        sign in interactively" are different facts about a site, and a caller
        reading ``last_auth_error`` should be able to tell them apart.
        """
        return cls(
            status_code=None,
            error=error,
            error_description=message,
            response_body=None,
            url=url,
            grant_type=grant_type,
        )

    @classmethod
    def from_token_response(cls, status_code, response_body, url, grant_type,
                            retry_after=None):
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
            retry_after=retry_after,
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


class ERClientAuthWarning(UserWarning):
    """The credentials in hand are legacy for the site they are aimed at.

    A ``UserWarning`` subclass, so it shows by default and a caller who has
    made their peace with it can silence just this category::

        warnings.filterwarnings("ignore", category=ERClientAuthWarning)
    """


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


# A client-side pseudo error code, not an RFC 6749 one: the client refused the
# credentials itself because the site's discovery document says they cannot
# work. Never sent to a server and never received from one.
CREDENTIAL_SITE_MISMATCH = "credential_site_mismatch"

# The other client-side pseudo code: there were no credentials to refuse, and
# the interactive sign-in that would have got some cannot run — discovery is
# off, no terminal is attached, the issuer override is incomplete, or the site
# names no tenant this client knows. Also never on the wire.
INTERACTIVE_SIGN_IN_UNAVAILABLE = "interactive_sign_in_unavailable"

# RFC 6749 section 5.2 error codes, plus access_denied from the device-code and
# authorization-code flows.
_OAUTH_ERROR_TO_EXCEPTION = {
    'invalid_grant': ERClientBadCredentials,
    'invalid_client': ERClientBadCredentials,
    'unauthorized_client': ERClientBadCredentials,
    'access_denied': ERClientBadCredentials,
    # RFC 8628 section 3.5: the device code went unapproved for too long, so
    # there is no credential — the user has to be asked again.
    'expired_token': ERClientBadCredentials,
    'invalid_request': ERClientBadRequest,
    'unsupported_grant_type': ERClientBadRequest,
    'invalid_scope': ERClientBadRequest,
    # Ours, not the wire's: the credentials are wrong for this site, or there
    # is no interactive sign-in available to get any.
    CREDENTIAL_SITE_MISMATCH: ERClientBadCredentials,
    INTERACTIVE_SIGN_IN_UNAVAILABLE: ERClientBadCredentials,
}

# Only consulted when the body carries no OAuth error code: a token endpoint
# that answers with HTML or an empty body tells us nothing else.
_STATUS_TO_EXCEPTION = {
    400: ERClientBadRequest,
    401: ERClientBadCredentials,
    429: ERClientRateLimitExceeded,
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
