"""Characterization tests for AsyncERClient construction and its lazy auth paths.

Every assertion here describes behavior on the current implementation, warts
included. A wart that is still locked in carries a `# wart:` comment; when a
later step fixes one, the assertion is flipped in the same commit as the source
change, so the change is deliberate rather than a surprise failure.

The async client raises ``httpx.HTTPStatusError`` out of its token requests
rather than returning a bool, so its failure behavior diverges from the sync
client's in ways these tests pin down explicitly.
"""
import logging
from datetime import datetime, timezone

import httpx
import pytest
import pytz
import respx
from tests.auth.conftest import auth_warnings
from tests.auth.respx_helpers import mock_discovery

from erclient.client import AsyncERClient
from erclient.er_errors import (ERClientAuthWarning, ERClientBadCredentials,
                                ERClientBadRequest, ERClientInternalError)
from erclient.version import __version__


class TestConstruction:
    """Construction is offline and never validates what it is given."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "kwargs_name",
        ["ropc_kwargs", "token_kwargs"],
        ids=["ropc", "pre_acquired_token"],
    )
    async def test_issues_no_http_request(
        self, request, kwargs_name, async_client_factory
    ):
        """__init__ never contacts the network, whatever credentials are supplied."""
        kwargs = request.getfixturevalue(kwargs_name)
        async with respx.mock(assert_all_called=False) as respx_mock:
            async_client_factory(**kwargs)

            assert len(respx_mock.calls) == 0

    def test_unknown_kwargs_are_silently_ignored(self, service_root, async_client_factory):
        """Unrecognized kwargs neither raise nor become attributes."""
        client = async_client_factory(
            service_root=service_root, not_a_real_option="whatever"
        )

        assert not hasattr(client, "not_a_real_option")

    def test_positional_argument_is_rejected(self, service_root):
        """The constructor is kwargs-only."""
        with pytest.raises(TypeError):
            AsyncERClient(service_root)

    def test_common_attributes_are_stored_as_given(
        self, service_root, async_client_factory
    ):
        """Credentials and identifiers are stored verbatim."""
        client = async_client_factory(
            service_root=service_root,
            username="a-user",
            password="a-password",
            client_id="a-client-id",
            provider_key="a-provider-key",
            realtime_url="https://realtime.erdomain.org",
        )

        assert client.username == "a-user"
        assert client.password == "a-password"
        assert client.client_id == "a-client-id"
        assert client.provider_key == "a-provider-key"
        assert client.realtime_url == "https://realtime.erdomain.org"
        assert client.user_agent == f"das-client/{__version__}"
        assert client.logger.name == "AsyncERClient"

    def test_omitted_attributes_default_to_none(self, service_root, async_client_factory):
        """Anything not supplied is stored as None rather than being absent."""
        client = async_client_factory(service_root=service_root)

        assert client.username is None
        assert client.password is None
        assert client.client_id is None
        assert client.provider_key is None
        assert client.realtime_url is None
        assert client.token is None

    class TestTokenUrl:
        """Where the client will post, decided entirely at construction time."""

        def test_defaults_to_relative_url_without_service_root(
            self, async_client_factory
        ):
            """Omitting service_root is accepted and produces an unusable URL."""
            client = async_client_factory()

            assert client.service_root == ""
            assert client.token_url == "/oauth2/token"  # wart: not a usable URL

        @pytest.mark.parametrize(
            "service_root_input",
            [
                "https://example.com",
                "https://example.com/",
                "https://example.com/api",
                "https://example.com/api/",
                "https://example.com/api/v1.0",
                "https://example.com/api/v2.0",
            ],
            ids=[
                "base_no_slash",
                "base_trailing_slash",
                "ends_with_api",
                "ends_with_api_slash",
                "full_v1",
                "full_v2",
            ],
        )
        def test_derives_from_normalized_service_root(
            self, service_root_input, async_client_factory
        ):
            """Built from the normalized base, so it never carries /api or a double slash."""
            client = async_client_factory(service_root=service_root_input)

            assert client.token_url == "https://example.com/oauth2/token"

        def test_explicit_value_is_used_verbatim(
            self, service_root, custom_token_url, async_client_factory
        ):
            """An explicit token_url wins; service_root does not influence it."""
            client = async_client_factory(
                service_root=service_root, token_url=custom_token_url
            )

            assert client.token_url == custom_token_url


class TestPreAcquiredToken:
    """token= mode: auth is complete at construction and never refreshed."""

    def test_sets_auth_and_pins_expiry_to_2099(self, token_kwargs, async_client_factory):
        """A supplied token is wrapped as Bearer auth that effectively never expires."""
        client = async_client_factory(**token_kwargs)

        assert client.auth == {
            "token_type": "Bearer",
            "access_token": token_kwargs["token"],
        }
        assert client.auth_expires == datetime(2099, 1, 1, tzinfo=pytz.utc)
        assert client.token == token_kwargs["token"]

    @pytest.mark.asyncio
    async def test_auth_headers_issue_no_token_request(
        self, token_kwargs, default_token_url, async_client_factory
    ):
        """auth_headers() serves the supplied token without contacting the endpoint."""
        client = async_client_factory(**token_kwargs)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            token_route = respx_mock.post(default_token_url)

            headers = await client.auth_headers()

            assert headers == {
                "Authorization": f"Bearer {token_kwargs['token']}",
                "Accept-Type": "application/json",
            }
            assert not token_route.called

    @pytest.mark.asyncio
    async def test_repeated_auth_headers_never_expire(
        self, token_kwargs, default_token_url, async_client_factory
    ):
        """The pinned 2099 expiry means repeated calls never trip a refresh."""
        client = async_client_factory(**token_kwargs)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            token_route = respx_mock.post(default_token_url)

            for _ in range(3):
                await client.auth_headers()

            assert not token_route.called

    @pytest.mark.asyncio
    async def test_token_wins_over_supplied_credentials(
        self, ropc_kwargs, token_kwargs, default_token_url, async_client_factory
    ):
        """When both are given the token is used; the credentials are kept but unused."""
        with pytest.warns(ERClientAuthWarning):
            client = async_client_factory(**{**ropc_kwargs, **token_kwargs})

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            token_route = respx_mock.post(default_token_url)

            headers = await client.auth_headers()

            assert headers["Authorization"] == f"Bearer {token_kwargs['token']}"
            assert not token_route.called
            assert client.username == ropc_kwargs["username"]
            assert client.password == ropc_kwargs["password"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("credential", ["username", "password"])
    async def test_supplying_both_kinds_of_credential_is_worth_saying(
        self, service_root, token_kwargs, async_client_factory, credential, caplog,
    ):
        """Silently ignoring half of what a caller passed is how they end up
        debugging the wrong credentials."""
        with caplog.at_level(logging.WARNING):
            with pytest.warns(ERClientAuthWarning) as recorded:
                async_client_factory(
                    **token_kwargs, **{credential: "test-value"})

        assert str(recorded[0].message) == (
            "Both token= and username/password were supplied; token= takes "
            "precedence and the username/password are ignored."
        )
        assert "token= takes precedence" in caplog.text

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"token": "not-a-real-token"},
            {"username": "test-user", "password": "test-password"},
            {"token": "", "username": "test-user", "password": "test-password"},
        ],
        ids=["token_alone", "credentials_alone", "empty_token_is_no_token"],
    )
    @pytest.mark.asyncio
    async def test_one_kind_of_credential_is_unremarkable(
        self, service_root, async_client_factory, kwargs, recwarn,
    ):
        async_client_factory(service_root=service_root, **kwargs)

        assert auth_warnings(recwarn.list) == []

    def test_empty_token_is_no_token_at_all(
        self, service_root, async_client_factory
    ):
        """token="" is falsy, so the token branch is skipped entirely.

        It used to fall through to a password grant of ``None``s. It now falls
        through to the interactive sign-in, which is what a client holding no
        credentials should do.
        """
        client = async_client_factory(service_root=service_root, token="")

        assert client.auth is None
        assert client.token == ""
        assert client._uses_device_code() is True

    def test_empty_token_alongside_credentials_still_means_the_password_grant(
        self, service_root, async_client_factory
    ):
        """The legacy path is chosen by the legacy kwargs, not by the empty one."""
        client = async_client_factory(service_root=service_root, token="",
                                      username="u", password="p")

        assert client._uses_device_code() is False

    def test_token_none_is_same_as_omitted(self, service_root, async_client_factory):
        """An explicit token=None behaves exactly like omitting the kwarg."""
        explicit = async_client_factory(
            service_root=service_root, token=None)
        omitted = async_client_factory(service_root=service_root)

        assert explicit.auth is omitted.auth is None
        assert explicit.token is omitted.token is None
        assert explicit.auth_expires == omitted.auth_expires

    @pytest.mark.asyncio
    async def test_rejected_token_surfaces_from_the_api_call(
        self, token_kwargs, default_token_url, async_client_factory
    ):
        """A bad token is discovered by the API, not by the token endpoint."""
        client = async_client_factory(**token_kwargs)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            token_route = respx_mock.post(default_token_url)
            me_route = respx_mock.get(f"{client._api_root('v1.0')}/user/me")
            me_route.return_value = httpx.Response(
                401, json={"status": {"detail": "Invalid token."}}
            )

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.get_me()

            assert me_route.called
            assert not token_route.called

        assert exc_info.value.status_code == 401


class TestPasswordGrant:
    """ROPC mode: nothing happens until the first request needs headers."""

    def test_construction_leaves_auth_unset(self, ropc_kwargs, async_client_factory):
        """Nothing is acquired eagerly."""
        client = async_client_factory(**ropc_kwargs)

        assert client.auth is None
        assert client.auth_expires == pytz.utc.localize(datetime.min)
        assert client.token is None

    class TestFirstLogin:

        @pytest.mark.asyncio
        async def test_posts_exactly_the_password_payload(
            self,
            ropc_kwargs,
            default_token_url,
            token_response,
            async_client_factory,
        ):
            """Exactly one form-encoded password grant, with no extra fields."""
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                token_route = respx_mock.post(default_token_url)
                token_route.return_value = httpx.Response(
                    200, json=token_response)

                await client.auth_headers()

                assert token_route.call_count == 1
                request = token_route.calls[0].request
                assert request.headers["content-type"] == (
                    "application/x-www-form-urlencoded"
                )
                assert dict(httpx.QueryParams(request.content.decode())) == {
                    "grant_type": "password",
                    "username": ropc_kwargs["username"],
                    "password": ropc_kwargs["password"],
                    "client_id": ropc_kwargs["client_id"],
                }

        @pytest.mark.asyncio
        @pytest.mark.parametrize(
            "expires_in", [3600, "3600"], ids=["int", "string"])
        async def test_response_is_stored_whole_with_derived_expiry(
            self,
            ropc_kwargs,
            default_token_url,
            token_response_factory,
            assert_expiry_matches,
            async_client_factory,
            expires_in,
        ):
            """The whole body becomes self.auth; expiry is now + expires_in - 300s."""
            body = token_response_factory(expires_in=expires_in)
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                respx_mock.post(default_token_url).return_value = httpx.Response(
                    200, json=body
                )

                await client.auth_headers()

            assert client.auth == body
            assert client.auth["scope"] == "read write"  # extra keys survive
            assert_expiry_matches(client.auth_expires, expires_in)

        @pytest.mark.asyncio
        async def test_authorization_header_uses_the_response_token_type(
            self,
            ropc_kwargs,
            default_token_url,
            token_response_factory,
            async_client_factory,
        ):
            """token_type comes from the response verbatim, not a hard-coded "Bearer"."""
            body = token_response_factory(
                token_type="MAC", access_token="abc123")
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                respx_mock.post(default_token_url).return_value = httpx.Response(
                    200, json=body
                )

                headers = await client.auth_headers()

            assert headers["Authorization"] == "MAC abc123"

        @pytest.mark.asyncio
        async def test_explicit_login_returns_true_on_success(
            self,
            ropc_kwargs,
            default_token_url,
            token_response,
            async_client_factory,
        ):
            """Explicit login() reports success as a bool."""
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                respx_mock.post(default_token_url).return_value = httpx.Response(
                    200, json=token_response
                )

                assert await client.login() is True

            assert client.auth == token_response

        @pytest.mark.asyncio
        async def test_uses_the_shared_http_session(
            self,
            ropc_kwargs,
            default_token_url,
            token_response,
            async_client_factory,
        ):
            """Unlike the sync client, token requests go through self._http_session.

            Closing the session is enough to stop them, which is what proves
            the coupling.
            """
            client = async_client_factory(**ropc_kwargs)
            await client.close()

            async with respx.mock(assert_all_called=False) as respx_mock:
                token_route = respx_mock.post(default_token_url)
                token_route.return_value = httpx.Response(
                    200, json=token_response)

                with pytest.raises(RuntimeError, match="client has been closed"):
                    await client.login()

                assert not token_route.called

    class TestExpiryAndRefresh:

        @pytest.mark.asyncio
        async def test_live_token_is_reused(
            self,
            ropc_kwargs,
            default_token_url,
            token_response,
            async_client_factory,
        ):
            """A second auth_headers() inside the validity window makes no request."""
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                token_route = respx_mock.post(default_token_url)
                token_route.return_value = httpx.Response(
                    200, json=token_response)

                await client.auth_headers()
                await client.auth_headers()

                assert token_route.call_count == 1

        @pytest.mark.asyncio
        async def test_expired_auth_refreshes_without_a_password_grant(
            self,
            ropc_kwargs,
            default_token_url,
            token_response_factory,
            async_client_factory,
        ):
            """On expiry the client tries refresh_token first and stops there when it works."""
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                token_route = respx_mock.post(default_token_url)
                token_route.side_effect = [
                    httpx.Response(200, json=token_response_factory()),
                    httpx.Response(
                        200,
                        json=token_response_factory(
                            access_token="access-token-2"),
                    ),
                ]

                await client.auth_headers()
                client.auth_expires = pytz.utc.localize(datetime.min)
                headers = await client.auth_headers()

                assert token_route.call_count == 2
                refresh_body = token_route.calls[1].request.content.decode()
                assert dict(httpx.QueryParams(refresh_body)) == {
                    "grant_type": "refresh_token",
                    "refresh_token": "refresh-token-1",
                    "client_id": ropc_kwargs["client_id"],
                }
                assert headers["Authorization"] == "Bearer access-token-2"

        @pytest.mark.asyncio
        async def test_failed_refresh_does_not_fall_back_to_a_password_grant(
            self,
            ropc_kwargs,
            default_token_url,
            token_response_factory,
            async_client_factory,
        ):
            """The async client diverges from the sync one here.

            ``auth_headers()`` reads as "if the refresh returns falsy, log in
            again", but the async ``_token_request`` raises instead of
            returning False, so the fallback login is unreachable.
            """
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                token_route = respx_mock.post(default_token_url)
                token_route.side_effect = [
                    httpx.Response(200, json=token_response_factory()),
                    httpx.Response(401, json={"error": "invalid_grant"}),
                    httpx.Response(
                        200,
                        json=token_response_factory(
                            access_token="access-token-3"),
                    ),
                ]

                await client.auth_headers()
                client.auth_expires = pytz.utc.localize(datetime.min)

                # wart: the sync client would retry with a password grant here
                with pytest.raises(httpx.HTTPStatusError):
                    await client.auth_headers()

                assert token_route.call_count == 2

            assert client.auth is None
            assert client.auth_expires == pytz.utc.localize(datetime.min)

        @pytest.mark.asyncio
        async def test_missing_refresh_token_goes_straight_to_a_password_grant(
            self,
            ropc_kwargs,
            default_token_url,
            token_response_factory,
            async_client_factory,
        ):
            """With no refresh token to send, expiry re-runs login() instead."""
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                token_route = respx_mock.post(default_token_url)
                token_route.side_effect = [
                    httpx.Response(
                        200, json=token_response_factory(refresh_token=None)
                    ),
                    httpx.Response(
                        200,
                        json=token_response_factory(
                            access_token="access-token-2", refresh_token=None
                        ),
                    ),
                ]

                await client.auth_headers()
                client.auth_expires = pytz.utc.localize(datetime.min)
                headers = await client.auth_headers()

                assert token_route.call_count == 2
                grant_types = [
                    dict(httpx.QueryParams(
                        call.request.content.decode()))["grant_type"]
                    for call in token_route.calls
                ]
                assert grant_types == ["password", "password"]
                assert headers["Authorization"] == "Bearer access-token-2"

        @pytest.mark.asyncio
        async def test_refresh_token_without_one_returns_false_and_sends_nothing(
            self,
            ropc_kwargs,
            default_token_url,
            token_response_factory,
            async_client_factory,
        ):
            """Called directly, refresh_token() reports the obvious rather than raising."""
            body = token_response_factory(refresh_token=None)
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                token_route = respx_mock.post(default_token_url)
                token_route.return_value = httpx.Response(200, json=body)

                await client.login()

                assert await client.refresh_token() is False
                assert token_route.call_count == 1  # only the login

            # The still-usable token is left alone.
            assert client.auth == body

        def test_auth_is_valid_tracks_the_recorded_expiry(
            self, token_kwargs, async_client_factory
        ):
            """_auth_is_valid is a pure comparison against auth_expires."""
            client = async_client_factory(**token_kwargs)

            assert client._auth_is_valid() is True

            client.auth_expires = datetime.now(tz=timezone.utc)
            assert client._auth_is_valid() is False

    class TestFailures:

        @pytest.mark.asyncio
        async def test_explicit_login_raises_after_resetting_auth(
            self, ropc_kwargs, default_token_url, async_client_factory
        ):
            """login() raises rather than returning False, and clears auth first."""
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                respx_mock.post(default_token_url).return_value = httpx.Response(
                    401, json={"error": "invalid_grant"}
                )

                with pytest.raises(httpx.HTTPStatusError):
                    await client.login()

            assert client.auth is None
            assert client.auth_expires == pytz.utc.localize(datetime.min)

        @pytest.mark.asyncio
        @pytest.mark.parametrize(
            "status_code,expected_exception",
            [
                (400, ERClientBadRequest),
                (401, ERClientBadCredentials),
                (500, ERClientInternalError),
            ],
        )
        async def test_request_wrappers_map_each_failure_status(
            self,
            ropc_kwargs,
            default_token_url,
            async_client_factory,
            status_code,
            expected_exception,
        ):
            """Through _call the token-endpoint status maps to a distinct exception.

            This body carries no OAuth error code, so the status still decides
            the class. What changed is the message: it is now the same
            "Login failed." the sync client raises, rather than the
            "ER ... ON GET ..." text the API's status handler produced.
            """
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock(assert_all_called=False) as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                respx_mock.post(default_token_url).return_value = httpx.Response(
                    status_code, json={"error_description": "no good"}
                )
                me_route = respx_mock.get(
                    f"{client._api_root('v1.0')}/user/me")

                with pytest.raises(expected_exception) as exc_info:
                    await client.get_me()

                assert not me_route.called

            assert exc_info.value.status_code == status_code
            assert "no good" in exc_info.value.response_body
            assert str(exc_info.value).startswith("Login failed.")

        @pytest.mark.asyncio
        async def test_post_form_maps_the_same_failure(
            self, ropc_kwargs, default_token_url, async_client_factory
        ):
            """_post_form routes an auth failure through the same handler."""
            client = async_client_factory(**ropc_kwargs)

            async with respx.mock as respx_mock:
                mock_discovery(respx_mock, client.service_root)
                respx_mock.post(default_token_url).return_value = httpx.Response(
                    401, json={"error_description": "no good"}
                )

                with pytest.raises(ERClientBadCredentials) as exc_info:
                    await client._post_form("activity/events", body={})

            assert str(exc_info.value).startswith("Login failed.")


class TestCustomTokenUrl:

    @pytest.mark.asyncio
    async def test_receives_the_password_grant(
        self,
        ropc_kwargs,
        custom_token_url,
        default_token_url,
        token_response,
        async_client_factory,
    ):
        """A custom token_url changes the target but not the payload."""
        client = async_client_factory(
            **ropc_kwargs, token_url=custom_token_url)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            default_route = respx_mock.post(default_token_url)
            custom_route = respx_mock.post(custom_token_url)
            custom_route.return_value = httpx.Response(
                200, json=token_response)

            await client.auth_headers()

            assert custom_route.call_count == 1
            assert not default_route.called
            body = custom_route.calls[0].request.content.decode()
            assert dict(httpx.QueryParams(body)) == {
                "grant_type": "password",
                "username": ropc_kwargs["username"],
                "password": ropc_kwargs["password"],
                "client_id": ropc_kwargs["client_id"],
            }

    @pytest.mark.asyncio
    async def test_is_never_contacted_when_a_token_is_supplied(
        self, token_kwargs, custom_token_url, async_client_factory
    ):
        """A pre-acquired token short-circuits the token endpoint, custom or not."""
        client = async_client_factory(
            **token_kwargs, token_url=custom_token_url)

        async with respx.mock(assert_all_called=False) as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            custom_route = respx_mock.post(custom_token_url)

            await client.auth_headers()

            assert not custom_route.called


class TestNoCredentials:
    """Nothing was supplied, so the client signs the user in itself."""

    def test_constructs_fine(self, service_root, async_client_factory):
        client = async_client_factory(service_root=service_root)

        assert client.auth is None
        assert client.username is None

    def test_selects_the_interactive_sign_in(
        self, service_root, async_client_factory
    ):
        """It used to post a password grant of Nones and raise the status error."""
        client = async_client_factory(service_root=service_root)

        assert client._uses_device_code() is True

    @pytest.mark.asyncio
    async def test_without_a_terminal_it_says_so_and_sends_nothing(
        self, service_root, async_client_factory, no_tty
    ):
        """The device-code path is covered in full in test_device_code_async.py."""
        client = async_client_factory(service_root=service_root)

        async with respx.mock as respx_mock:
            with pytest.raises(ERClientBadCredentials):
                await client.auth_headers()

            assert not respx_mock.calls

    @pytest.mark.asyncio
    async def test_the_password_grant_still_sends_empty_strings_for_nones(
        self, service_root, default_token_url, async_client_factory
    ):
        """httpx sends empty strings where requests drops the key entirely.

        Locked in so a library upgrade that changes it is caught here. Reached
        now with a client_id, since without one there is no password grant.
        """
        client = async_client_factory(service_root=service_root,
                                      client_id="das_web_client")

        async with respx.mock as respx_mock:
            mock_discovery(respx_mock, client.service_root)
            token_route = respx_mock.post(default_token_url)
            token_route.return_value = httpx.Response(
                400, json={"error": "invalid_request"}
            )

            with pytest.raises(httpx.HTTPStatusError):
                await client.auth_headers()

            assert token_route.calls[0].request.content.decode() == (
                "grant_type=password&username=&password=&client_id=das_web_client"
            )


class TestLifecycle:
    """Session management, which carries no auth traffic of its own."""

    @pytest.mark.asyncio
    async def test_context_manager_yields_the_client_and_closes_on_exit(
        self, token_kwargs, default_token_url
    ):
        async with respx.mock(assert_all_called=False) as respx_mock:
            token_route = respx_mock.post(default_token_url)

            async with AsyncERClient(**token_kwargs) as client:
                assert isinstance(client, AsyncERClient)
                assert not client._http_session.is_closed

            assert client._http_session.is_closed
            assert not token_route.called

    @pytest.mark.asyncio
    async def test_request_after_close_raises_rather_than_reopening(
        self, token_kwargs, async_client_factory
    ):
        """The closed session is not silently replaced, and the error is not wrapped."""
        client = async_client_factory(**token_kwargs)
        await client.close()

        assert client._http_session.is_closed

        async with respx.mock(assert_all_called=False) as respx_mock:
            respx_mock.get(f"{client._api_root('v1.0')}/user/me")

            # wart: a bare RuntimeError, not an ERClientException
            with pytest.raises(RuntimeError, match="client has been closed"):
                await client.get_me()


class TestTheBothCredentialsWarningPointsAtTheCaller:
    """The construction that supplied both is the line worth reporting."""

    def test_it_blames_the_constructor_call(self, service_root):
        with pytest.warns(ERClientAuthWarning) as record:
            AsyncERClient(service_root=service_root, token="a-token",
                          username="someone")

        assert record[0].filename == __file__
