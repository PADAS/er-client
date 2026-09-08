"""How AsyncERClient surfaces a refusal from the token endpoint.

The async client raises ``httpx.HTTPStatusError`` out of its token requests, so
the classification happens one level up, in the request wrappers that already
catch it around ``auth_headers()``. Direct callers of ``login()`` and
``refresh_token()`` still see the raw httpx error, as before.
"""
import json
import logging
from datetime import datetime

import httpx
import pytest
import pytz
import respx
from tests.auth.respx_helpers import mock_discovery

from erclient.er_errors import (ERClientBadCredentials, ERClientBadRequest,
                                ERClientRateLimitExceeded)


class TestLastAuthError:
    """The record of the token endpoint's last refusal."""

    def test_is_none_after_construction(self, ropc_kwargs, async_client_factory):
        """Nothing has been attempted yet, so there is nothing to report."""
        client = async_client_factory(**ropc_kwargs)

        assert client.last_auth_error is None

    @pytest.mark.asyncio
    async def test_records_every_field_of_a_refusal(
        self, ropc_kwargs, default_token_url, async_client_factory
    ):
        """The refusal is recorded on the way out, before the httpx error escapes."""
        body = {"error": "invalid_grant",
                "error_description": "wrong password"}
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                400, json=body
            )

            with pytest.raises(httpx.HTTPStatusError):
                await client.login()

        auth_error = client.last_auth_error
        assert auth_error.status_code == 400
        assert auth_error.error == "invalid_grant"
        assert auth_error.error_description == "wrong password"
        assert json.loads(auth_error.response_body) == body
        assert auth_error.url == default_token_url
        assert auth_error.grant_type == "password"

    @pytest.mark.asyncio
    async def test_records_the_grant_type_that_was_refused(
        self,
        ropc_kwargs,
        default_token_url,
        token_response_factory,
        async_client_factory,
    ):
        """A refused refresh is distinguishable from a refused password grant."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            token_route = respx_mock.post(default_token_url)
            token_route.side_effect = [
                httpx.Response(200, json=token_response_factory()),
                httpx.Response(400, json={"error": "invalid_grant"}),
            ]

            await client.login()
            with pytest.raises(httpx.HTTPStatusError):
                await client.refresh_token()

        assert client.last_auth_error.grant_type == "refresh_token"

    @pytest.mark.asyncio
    async def test_is_cleared_by_a_later_success(
        self,
        ropc_kwargs,
        default_token_url,
        token_response_factory,
        async_client_factory,
    ):
        """A stale failure does not outlive the login that fixed it."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            token_route = respx_mock.post(default_token_url)
            token_route.side_effect = [
                httpx.Response(400, json={"error": "invalid_grant"}),
                httpx.Response(200, json=token_response_factory()),
            ]

            with pytest.raises(httpx.HTTPStatusError):
                await client.login()
            assert client.last_auth_error is not None

            await client.login()

        assert client.last_auth_error is None

    @pytest.mark.asyncio
    async def test_is_untouched_by_the_missing_refresh_token_short_circuit(
        self,
        ropc_kwargs,
        default_token_url,
        token_response_factory,
        async_client_factory,
    ):
        """Declining to send a refresh is not a token-endpoint failure."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response_factory(refresh_token=None)
            )

            await client.login()

            assert await client.refresh_token() is False

        assert client.last_auth_error is None

    def test_is_read_only(self, ropc_kwargs, async_client_factory):
        """Callers read the record; only the client writes it."""
        client = async_client_factory(**ropc_kwargs)

        with pytest.raises(AttributeError):
            client.last_auth_error = None


class TestWrappersRaiseTheClassifiedError:
    """Every wrapper that catches the httpx error classifies it the same way."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "wrapper",
        ["_call", "_post_form", "get_file"],
    )
    async def test_a_refused_password_grant_becomes_bad_credentials(
        self, ropc_kwargs, default_token_url, async_client_factory, wrapper
    ):
        """``400 invalid_grant`` is a credential problem, whatever the status says."""
        body = {"error": "invalid_grant",
                "error_description": "wrong password"}
        client = async_client_factory(**ropc_kwargs)

        calls = {
            "_call": lambda: client.get_me(),
            "_post_form": lambda: client._post_form("activity/events", body={}),
            "get_file": lambda: client.get_file("activity/events/1/file/x.jpg"),
        }

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                400, json=body
            )
            api_route = respx_mock.route(host="fake-site.erdomain.org").mock(
                return_value=httpx.Response(200, json={})
            )

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await calls[wrapper]()

            assert not api_route.called

        # The exact class, not a subclass: invalid_grant is a refused login,
        # not the ERClientBadRequest a 400 from the API would be.
        assert type(exc_info.value) is ERClientBadCredentials
        assert exc_info.value.status_code == 400
        assert json.loads(exc_info.value.response_body) == body
        assert str(exc_info.value).startswith("Login failed.")

    @pytest.mark.asyncio
    async def test_message_and_class_match_the_sync_client(
        self, ropc_kwargs, default_token_url, async_client_factory
    ):
        """Both clients now say the same thing for the same refusal."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                400, json={"error": "invalid_grant"}
            )

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.get_me()

        # The body is quoted exactly as the endpoint sent it, hence the
        # compact JSON httpx writes here.
        assert str(exc_info.value) == (
            'Login failed. (status_code=400) '
            '(response_body={"error":"invalid_grant"})'
        )

    @pytest.mark.asyncio
    async def test_a_body_with_no_oauth_error_falls_back_to_the_status(
        self, ropc_kwargs, default_token_url, async_client_factory
    ):
        """Without an OAuth code the status decides, as it effectively did before."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                400, json={"error_description": "no good"}
            )

            with pytest.raises(ERClientBadRequest) as exc_info:
                await client.get_me()

        assert type(exc_info.value) is ERClientBadRequest
        assert "no good" in exc_info.value.response_body

    @pytest.mark.asyncio
    async def test_a_throttled_token_endpoint_is_a_rate_limit(
        self, ropc_kwargs, default_token_url, async_client_factory
    ):
        """A bare 429 says how long to wait, and the caller gets both."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                429, text="", headers={"Retry-After": "12"}
            )

            with pytest.raises(ERClientRateLimitExceeded) as exc_info:
                await client.get_me()

        assert type(exc_info.value) is ERClientRateLimitExceeded
        assert exc_info.value.retry_after == 12
        assert client.last_auth_error.retry_after == 12

    @pytest.mark.asyncio
    async def test_a_refusal_without_the_header_leaves_retry_after_unset(
        self, ropc_kwargs, default_token_url, async_client_factory
    ):
        """Nothing is invented for the ordinary refusal that says nothing."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                400, json={"error": "invalid_grant"}
            )

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.get_me()

        assert exc_info.value.retry_after is None
        assert client.last_auth_error.retry_after is None

    @pytest.mark.asyncio
    async def test_logs_the_body_at_exception_level(
        self, ropc_kwargs, default_token_url, async_client_factory, caplog
    ):
        """The endpoint's body reaches the log, as it did before."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                400, json={"error": "invalid_grant"}
            )

            with caplog.at_level(logging.ERROR, logger="AsyncERClient"):
                with pytest.raises(ERClientBadCredentials):
                    await client.get_me()

        record = next(
            r for r in caplog.records if r.name == "AsyncERClient")
        assert record.levelno == logging.ERROR
        assert record.exc_info is not None
        assert "invalid_grant" in record.getMessage()

    @pytest.mark.asyncio
    async def test_a_refused_refresh_does_not_trigger_a_password_grant(
        self,
        ropc_kwargs,
        default_token_url,
        token_response_factory,
        async_client_factory,
    ):
        """The async client still does not fall back, but now it says why it failed."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            token_route = respx_mock.post(default_token_url)
            token_route.side_effect = [
                httpx.Response(200, json=token_response_factory()),
                httpx.Response(400, json={"error": "invalid_grant"}),
                httpx.Response(
                    200, json=token_response_factory(access_token="never-used")
                ),
            ]

            await client.auth_headers()
            client.auth_expires = pytz.utc.localize(datetime.min)

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.get_me()

            grant_types = [
                dict(httpx.QueryParams(call.request.content.decode()))[
                    "grant_type"]
                for call in token_route.calls
            ]
            assert grant_types == ["password", "refresh_token"]

        assert str(exc_info.value).startswith("Login failed.")
        assert client.last_auth_error.grant_type == "refresh_token"

    @pytest.mark.asyncio
    async def test_direct_refresh_token_still_raises_the_httpx_error(
        self,
        ropc_kwargs,
        default_token_url,
        token_response_factory,
        async_client_factory,
    ):
        """Classification lives in the wrappers; direct callers see httpx as before."""
        client = async_client_factory(**ropc_kwargs)

        async with respx.mock as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            token_route = respx_mock.post(default_token_url)
            token_route.side_effect = [
                httpx.Response(200, json=token_response_factory()),
                httpx.Response(400, json={"error": "invalid_grant"}),
            ]

            await client.login()

            with pytest.raises(httpx.HTTPStatusError):
                await client.refresh_token()

    def test_falls_back_to_the_response_when_nothing_was_recorded(
        self, ropc_kwargs, default_token_url, async_client_factory
    ):
        """A status error with no recorded refusal is still described, not dropped."""
        client = async_client_factory(**ropc_kwargs)
        request = httpx.Request("POST", default_token_url)
        response = httpx.Response(
            401, json={"error": "invalid_client"}, request=request)

        assert client.last_auth_error is None

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client._handle_token_error(
                httpx.HTTPStatusError(
                    "boom", request=request, response=response)
            )

        assert exc_info.value.status_code == 401
        assert str(exc_info.value).startswith("Login failed.")
