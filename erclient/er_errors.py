class ERClientException(Exception):
    # Optional support for storing status code and response body
    def __init__(self, message=None, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

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
