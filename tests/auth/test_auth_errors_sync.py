"""How ERClient surfaces a refusal from the token endpoint.

``login()`` is public and returns a bool, so a caller using it to check
credentials needs somewhere to read *why* it said False: that is
``last_auth_error``. When the failure escapes through ``auth_headers()``
instead, the same record picks the exception class.
"""
import json
from datetime import datetime
from unittest.mock import patch

import pytest
import pytz

from erclient.client import ERClient
from erclient.er_errors import (ERClientBadCredentials, ERClientBadRequest,
                                ERClientInternalError,
                                ERClientRateLimitExceeded,
                                ERClientServiceUnreachable)


class TestLastAuthError:
    """The record of the token endpoint's last refusal."""

    def test_is_none_after_construction(self, ropc_kwargs):
        """Nothing has been attempted yet, so there is nothing to report."""
        client = ERClient(**ropc_kwargs)

        assert client.last_auth_error is None

    def test_records_every_field_of_a_refusal(
        self, ropc_kwargs, default_token_url, make_requests_response
    ):
        """A failed login is described in full, even though login() only returns False."""
        body = {"error": "invalid_grant",
                "error_description": "wrong password"}
        client = ERClient(**ropc_kwargs)

        with patch(
            "erclient.client.requests.post",
            return_value=make_requests_response(400, json_data=body),
        ):
            assert client.login() is False

        auth_error = client.last_auth_error
        assert auth_error.status_code == 400
        assert auth_error.error == "invalid_grant"
        assert auth_error.error_description == "wrong password"
        assert auth_error.response_body == json.dumps(body)
        assert auth_error.url == default_token_url
        assert auth_error.grant_type == "password"

    def test_records_the_grant_type_that_was_refused(
        self, ropc_kwargs, token_response_factory, make_requests_response
    ):
        """A refused refresh is distinguishable from a refused password grant."""
        client = ERClient(**ropc_kwargs)
        responses = [
            make_requests_response(200, json_data=token_response_factory()),
            make_requests_response(400, json_data={"error": "invalid_grant"}),
        ]

        with patch("erclient.client.requests.post", side_effect=responses):
            client.login()
            assert client.refresh_token() is False

        assert client.last_auth_error.grant_type == "refresh_token"

    def test_is_cleared_by_a_later_success(
        self, ropc_kwargs, token_response_factory, make_requests_response
    ):
        """A stale failure does not outlive the login that fixed it."""
        client = ERClient(**ropc_kwargs)
        responses = [
            make_requests_response(400, json_data={"error": "invalid_grant"}),
            make_requests_response(200, json_data=token_response_factory()),
        ]

        with patch("erclient.client.requests.post", side_effect=responses):
            client.login()
            assert client.last_auth_error is not None

            client.login()

        assert client.last_auth_error is None

    def test_is_untouched_by_the_missing_refresh_token_short_circuit(
        self, ropc_kwargs, token_response_factory, make_requests_response
    ):
        """Declining to send a refresh is not a token-endpoint failure."""
        body = token_response_factory(refresh_token=None)
        client = ERClient(**ropc_kwargs)

        with patch(
            "erclient.client.requests.post",
            return_value=make_requests_response(200, json_data=body),
        ):
            client.login()

            assert client.refresh_token() is False

        assert client.last_auth_error is None

    def test_is_cleared_when_the_fallback_login_succeeds(
        self, ropc_kwargs, token_response_factory, make_requests_response
    ):
        """A refused refresh that the password grant recovers from leaves no trace."""
        client = ERClient(**ropc_kwargs)
        responses = [
            make_requests_response(200, json_data=token_response_factory()),
            make_requests_response(400, json_data={"error": "invalid_grant"}),
            make_requests_response(
                200,
                json_data=token_response_factory(
                    access_token="access-token-2"),
            ),
        ]

        with patch(
            "erclient.client.requests.post", side_effect=responses
        ) as mock_post:
            client.auth_headers()
            client.auth_expires = pytz.utc.localize(datetime.min)
            headers = client.auth_headers()

            assert mock_post.call_count == 3

        assert headers["Authorization"] == "Bearer access-token-2"
        assert client.last_auth_error is None

    def test_is_read_only(self, ropc_kwargs):
        """Callers read the record; only the client writes it."""
        client = ERClient(**ropc_kwargs)

        with pytest.raises(AttributeError):
            client.last_auth_error = None


class TestAuthHeadersRaisesTheClassifiedError:
    """A login failure reaching auth_headers() names what went wrong."""

    @pytest.mark.parametrize(
        "status_code,json_data,text,expected_exception",
        [
            (400, {"error": "invalid_grant"}, None, ERClientBadCredentials),
            (401, {"error": "invalid_client"}, None, ERClientBadCredentials),
            (400, {"error": "invalid_request"}, None, ERClientBadRequest),
            (500, None, "", ERClientInternalError),
            (503, None, "<html>Service Unavailable</html>",
             ERClientServiceUnreachable),
        ],
        ids=[
            "invalid_grant",
            "invalid_client",
            "invalid_request",
            "bare_500",
            "bare_503",
        ],
    )
    def test_class_comes_from_the_refusal(
        self,
        ropc_kwargs,
        make_requests_response,
        status_code,
        json_data,
        text,
        expected_exception,
    ):
        """The OAuth error decides, and the status stands in when there is none."""
        client = ERClient(**ropc_kwargs)

        with patch(
            "erclient.client.requests.post",
            return_value=make_requests_response(
                status_code, json_data=json_data, text=text
            ),
        ):
            with pytest.raises(expected_exception) as exc_info:
                client.auth_headers()

        # Sibling classes, so an exact match rather than an isinstance check.
        assert type(exc_info.value) is expected_exception
        assert exc_info.value.status_code == status_code

    def test_message_carries_the_status_and_the_body(
        self, ropc_kwargs, make_requests_response
    ):
        """The endpoint's own words reach the caller, via the base __str__."""
        body = {"error": "invalid_grant",
                "error_description": "wrong password"}
        client = ERClient(**ropc_kwargs)

        with patch(
            "erclient.client.requests.post",
            return_value=make_requests_response(400, json_data=body),
        ):
            with pytest.raises(ERClientBadCredentials) as exc_info:
                client.auth_headers()

        assert exc_info.value.response_body == json.dumps(body)
        assert str(exc_info.value) == (
            "Login failed. (status_code=400) "
            f"(response_body={json.dumps(body)})"
        )

    def test_a_throttled_token_endpoint_is_a_rate_limit(
        self, ropc_kwargs, make_requests_response
    ):
        """A bare 429 says how long to wait, and the caller gets both."""
        client = ERClient(**ropc_kwargs)

        with patch(
            "erclient.client.requests.post",
            return_value=make_requests_response(
                429, text="", headers={"Retry-After": "12"}
            ),
        ):
            with pytest.raises(ERClientRateLimitExceeded) as exc_info:
                client.auth_headers()

        assert type(exc_info.value) is ERClientRateLimitExceeded
        assert exc_info.value.retry_after == 12
        assert client.last_auth_error.retry_after == 12

    def test_a_refusal_without_the_header_leaves_retry_after_unset(
        self, ropc_kwargs, make_requests_response
    ):
        """Nothing is invented for the ordinary refusal that says nothing."""
        client = ERClient(**ropc_kwargs)

        with patch(
            "erclient.client.requests.post",
            return_value=make_requests_response(
                400, json_data={"error": "invalid_grant"}
            ),
        ):
            with pytest.raises(ERClientBadCredentials) as exc_info:
                client.auth_headers()

        assert exc_info.value.retry_after is None
        assert client.last_auth_error.retry_after is None

    def test_resets_auth_before_raising(
        self, ropc_kwargs, make_requests_response
    ):
        """A failed login leaves nothing half-set behind."""
        client = ERClient(**ropc_kwargs)

        with patch(
            "erclient.client.requests.post",
            return_value=make_requests_response(
                400, json_data={"error": "invalid_grant"}
            ),
        ):
            with pytest.raises(ERClientBadCredentials):
                client.auth_headers()

        assert client.auth is None
        assert client.auth_expires == pytz.utc.localize(datetime.min)
