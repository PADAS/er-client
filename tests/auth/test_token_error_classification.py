"""Unit tests for the token-endpoint error model and its classifier.

Token endpoints do not use HTTP status the way the ER API does: per RFC 6749
section 5.2 a wrong password is ``400 invalid_grant``, and an unknown public
client is ``400`` or ``401 invalid_client``. So the OAuth ``error`` field in the
body decides which exception the caller sees, and the status is only the
fallback for bodies that are not OAuth-shaped.
"""
import pytest

from erclient.er_errors import (AuthError, ERClientBadCredentials,
                                ERClientBadRequest, ERClientException,
                                ERClientInternalError,
                                ERClientServiceUnreachable,
                                classify_token_error)


class TestAuthErrorFromTokenResponse:
    """Parsing the token endpoint's body, which may be anything at all."""

    def test_extracts_the_oauth_fields(self):
        """A well-formed OAuth error body yields error and error_description."""
        auth_error = AuthError.from_token_response(
            status_code=400,
            response_body='{"error": "invalid_grant", '
                          '"error_description": "wrong password"}',
            url="https://fake-site.erdomain.org/oauth2/token",
            grant_type="password",
        )

        assert auth_error.status_code == 400
        assert auth_error.error == "invalid_grant"
        assert auth_error.error_description == "wrong password"
        assert auth_error.url == "https://fake-site.erdomain.org/oauth2/token"
        assert auth_error.grant_type == "password"

    def test_keeps_the_body_verbatim(self):
        """The raw text is preserved, not the reparsed dict."""
        body = '{"error": "invalid_grant", "extra": [1, 2]}'

        auth_error = AuthError.from_token_response(
            status_code=400, response_body=body, url="", grant_type="password"
        )

        assert auth_error.response_body == body

    @pytest.mark.parametrize(
        "body",
        [
            "not json at all",
            "",
            "<html><body>502 Bad Gateway</body></html>",
            "[]",
            '"a bare string"',
            '{"error": {"code": "invalid_grant"}}',
        ],
        ids=[
            "plain_text",
            "empty",
            "html",
            "json_array",
            "json_string",
            "error_is_not_a_string",
        ],
    )
    def test_body_that_is_not_an_oauth_error_leaves_error_unset(self, body):
        """Anything unparseable, or parseable but not OAuth-shaped, means "no OAuth error"."""
        auth_error = AuthError.from_token_response(
            status_code=502, response_body=body, url="", grant_type="password"
        )

        assert auth_error.error is None
        assert auth_error.error_description is None
        assert auth_error.response_body == body

    def test_json_object_without_an_error_field_leaves_error_unset(self):
        """A JSON body can still carry no OAuth error code."""
        auth_error = AuthError.from_token_response(
            status_code=400,
            response_body='{"error_description": "wrong password"}',
            url="",
            grant_type="password",
        )

        assert auth_error.error is None
        assert auth_error.error_description == "wrong password"

    def test_is_frozen(self):
        """The record of a failure is not editable after the fact."""
        auth_error = AuthError.from_token_response(
            status_code=400, response_body="", url="", grant_type="password"
        )

        with pytest.raises(Exception):
            auth_error.status_code = 401


def oauth_error(error, status_code=400):
    """An AuthError for a body carrying the given OAuth error code."""
    return AuthError.from_token_response(
        status_code=status_code,
        response_body='{"error": "%s"}' % error,
        url="https://fake-site.erdomain.org/oauth2/token",
        grant_type="password",
    )


class TestClassifyByOauthError:
    """The OAuth error code decides, whatever the status alongside it."""

    @pytest.mark.parametrize(
        "error",
        ["invalid_grant", "invalid_client", "unauthorized_client", "access_denied"],
    )
    def test_credential_errors(self, error):
        assert classify_token_error(
            oauth_error(error)) is ERClientBadCredentials

    @pytest.mark.parametrize(
        "error", ["invalid_request", "unsupported_grant_type", "invalid_scope"]
    )
    def test_request_errors(self, error):
        assert classify_token_error(oauth_error(error)) is ERClientBadRequest

    @pytest.mark.parametrize("status_code", [400, 401, 403, 500])
    def test_the_status_alongside_it_is_ignored(self, status_code):
        """RFC 6749 lets a server pick the status; the body is what we trust."""
        assert (
            classify_token_error(oauth_error("invalid_grant", status_code))
            is ERClientBadCredentials
        )

    def test_unknown_error_code_falls_back_to_the_base_exception(self):
        """An OAuth code we do not recognize is not silently mapped by status."""
        assert (
            classify_token_error(oauth_error("teapot_overheated", 401))
            is ERClientException
        )


class TestClassifyByStatus:
    """With no OAuth error to go on, the status is the only signal left."""

    @pytest.mark.parametrize("status_code", [502, 503, 504])
    def test_gateway_statuses_are_service_unreachable(self, status_code):
        auth_error = AuthError.from_token_response(
            status_code=status_code,
            response_body="<html>Bad Gateway</html>",
            url="",
            grant_type="password",
        )

        assert classify_token_error(auth_error) is ERClientServiceUnreachable

    def test_500_is_an_internal_error(self):
        auth_error = AuthError.from_token_response(
            status_code=500, response_body="", url="", grant_type="password"
        )

        assert classify_token_error(auth_error) is ERClientInternalError

    def test_401_is_bad_credentials(self):
        auth_error = AuthError.from_token_response(
            status_code=401, response_body="nope", url="", grant_type="password"
        )

        assert classify_token_error(auth_error) is ERClientBadCredentials

    def test_400_is_a_bad_request(self):
        auth_error = AuthError.from_token_response(
            status_code=400,
            response_body='{"error_description": "no grant_type"}',
            url="",
            grant_type="password",
        )

        assert classify_token_error(auth_error) is ERClientBadRequest

    @pytest.mark.parametrize("status_code", [402, 404, 418, 429, 302, None])
    def test_anything_else_falls_back_to_the_base_exception(self, status_code):
        auth_error = AuthError.from_token_response(
            status_code=status_code, response_body="", url="", grant_type="password"
        )

        assert classify_token_error(auth_error) is ERClientException

    def test_no_auth_error_at_all_falls_back_to_the_base_exception(self):
        """The classifier never raises, even with nothing to classify."""
        assert classify_token_error(None) is ERClientException
