"""The token-endpoint error model and its classifier, on their own. A token
endpoint's status is not the signal the ER API's is: RFC 6749 section 5.2 lets
the same refusal come back as 400 or 401, so the body decides."""
import pytest

from erclient.er_errors import (AuthError, ERClientBadCredentials,
                                ERClientBadRequest, ERClientException,
                                ERClientInternalError,
                                ERClientRateLimitExceeded,
                                ERClientServiceUnreachable,
                                classify_token_error)

TOKEN_URL = "https://fake-site.erdomain.org/oauth2/token"


def token_error(status_code=400, body="", retry_after=None):
    return AuthError.from_token_response(
        status_code=status_code, response_body=body, url=TOKEN_URL,
        grant_type="password", retry_after=retry_after)


def oauth_error(error, status_code=400):
    return token_error(status_code, '{"error": "%s"}' % error)


class TestReadingTheBody:

    def test_extracts_the_oauth_fields(self):
        auth_error = token_error(body='{"error": "invalid_grant", '
                                      '"error_description": "wrong password"}')

        assert auth_error.status_code == 400
        assert auth_error.error == "invalid_grant"
        assert auth_error.error_description == "wrong password"
        assert auth_error.url == TOKEN_URL
        assert auth_error.grant_type == "password"

    def test_keeps_the_body_verbatim(self):
        body = '{"error": "invalid_grant", "extra": [1, 2]}'

        assert token_error(body=body).response_body == body

    @pytest.mark.parametrize("body", [
        "not json at all",
        "",
        "<html><body>502 Bad Gateway</body></html>",
        "[]",
        '"a bare string"',
        '{"error": {"code": "invalid_grant"}}',
        '{"error_description": "wrong password"}',
    ])
    def test_a_body_that_is_not_an_oauth_error_leaves_error_unset(self, body):
        auth_error = token_error(502, body)

        assert auth_error.error is None
        assert auth_error.response_body == body

    def test_records_a_parsed_retry_after(self):
        assert token_error(429, retry_after=7).retry_after == 7

    def test_retry_after_defaults_to_none(self):
        assert token_error().retry_after is None

    def test_the_record_is_frozen(self):
        with pytest.raises(Exception):
            token_error().status_code = 401


class TestClassifyByOauthError:

    @pytest.mark.parametrize("error", ["invalid_grant", "invalid_client",
                                       "unauthorized_client", "access_denied",
                                       "expired_token"])
    def test_credential_errors(self, error):
        assert classify_token_error(
            oauth_error(error)) is ERClientBadCredentials

    @pytest.mark.parametrize("error", ["invalid_request",
                                       "unsupported_grant_type",
                                       "invalid_scope"])
    def test_request_errors(self, error):
        assert classify_token_error(oauth_error(error)) is ERClientBadRequest

    @pytest.mark.parametrize("status_code", [400, 401, 403, 500])
    def test_the_status_alongside_it_is_ignored(self, status_code):
        assert classify_token_error(
            oauth_error("invalid_grant", status_code)) is ERClientBadCredentials

    def test_an_unknown_code_is_not_silently_mapped_by_status(self):
        assert classify_token_error(
            oauth_error("teapot_overheated", 401)) is ERClientException


class TestClassifyByStatus:

    @pytest.mark.parametrize("status_code,expected", [
        (400, ERClientBadRequest),
        (401, ERClientBadCredentials),
        (429, ERClientRateLimitExceeded),
        (500, ERClientInternalError),
        (502, ERClientServiceUnreachable),
        (503, ERClientServiceUnreachable),
        (504, ERClientServiceUnreachable),
    ])
    def test_each_status_it_recognizes(self, status_code, expected):
        assert classify_token_error(
            token_error(status_code, "nope")) is expected

    @pytest.mark.parametrize("status_code", [402, 404, 418, 302, None])
    def test_anything_else_falls_back_to_the_base_exception(self, status_code):
        assert classify_token_error(
            token_error(status_code)) is ERClientException

    def test_nothing_to_classify_falls_back_too(self):
        assert classify_token_error(None) is ERClientException
