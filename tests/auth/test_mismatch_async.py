"""AsyncERClient refuses credentials the site's discovery document rules out.

The async mirror of ``test_mismatch_sync.py``, with one difference the sync
client cannot have: ``login()`` already raised on failure here, so a mismatch
raises out of it directly rather than returning a bool.

Password grant only, so far; the token cases arrive with the token-mode check.
"""
import httpx
import pytest
import respx
from tests.auth.conftest import auth_warnings

from erclient.er_errors import (CREDENTIAL_SITE_MISMATCH, ERClientAuthWarning,
                                ERClientBadCredentials)


class TestPasswordGrantAtAMigratedSite:
    """A site listing only Auth0 will reject whatever its token endpoint issues."""

    @pytest.mark.asyncio
    async def test_login_raises_without_posting(
        self, ropc_kwargs, async_client_factory, discovery_url,
        external_only_document, default_token_url, password_mismatch_message,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)
            token_route = respx_mock.post(default_token_url)

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.login()

            assert str(exc_info.value) == password_mismatch_message
            assert not token_route.called

    @pytest.mark.asyncio
    async def test_no_credentials_are_left_on_the_client(
        self, ropc_kwargs, async_client_factory, discovery_url,
        external_only_document,
    ):
        """A refused login must not leave a half-authenticated client behind."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)

            with pytest.raises(ERClientBadCredentials):
                await client.login()

            assert client.auth is None
            assert not client._auth_is_valid()

    @pytest.mark.asyncio
    async def test_the_reason_is_also_recorded(
        self, ropc_kwargs, async_client_factory, discovery_url,
        external_only_document, default_token_url, password_mismatch_message,
    ):
        """Same record as the sync client keeps, for callers that read it."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)

            with pytest.raises(ERClientBadCredentials):
                await client.login()

            auth_error = client.last_auth_error
            assert auth_error.error == CREDENTIAL_SITE_MISMATCH
            assert auth_error.error_description == password_mismatch_message
            assert auth_error.status_code is None
            assert auth_error.response_body is None
            assert auth_error.url == default_token_url
            assert auth_error.grant_type == "password"

    @pytest.mark.asyncio
    async def test_an_api_call_fails_before_it_reaches_the_api(
        self, ropc_kwargs, async_client_factory, discovery_url,
        external_only_document, default_token_url, service_root,
        password_mismatch_message,
    ):
        """The wrappers catch httpx errors, not this one; it reaches the caller intact."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)
            token_route = respx_mock.post(default_token_url)
            api_route = respx_mock.get(f"{service_root}/api/v1.0/user/me")

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.get_me()

            assert str(exc_info.value) == password_mismatch_message
            assert not token_route.called
            assert not api_route.called

    @pytest.mark.asyncio
    async def test_the_deprecation_warning_gives_way_to_the_error(
        self, ropc_kwargs, async_client_factory, discovery_url,
        external_only_document, recwarn,
    ):
        """One clear failure, not a warning and then a raise about something else."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)

            with pytest.raises(ERClientBadCredentials):
                await client.login()

            assert auth_warnings(recwarn.list) == []


class TestTheCheckIsPerLogin:
    """Discovery is refetched on every login, so a refusal is never sticky."""

    @pytest.mark.asyncio
    async def test_a_site_that_lists_its_own_issuer_again_can_be_logged_into(
        self, ropc_kwargs, async_client_factory, discovery_url,
        external_only_document, discovery_document, default_token_url,
        token_response,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            discovery_route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=external_only_document))
            token_route = respx_mock.post(default_token_url).mock(
                return_value=httpx.Response(200, json=token_response))

            with pytest.raises(ERClientBadCredentials):
                await client.login()

            discovery_route.return_value = httpx.Response(
                200, json=discovery_document)

            with pytest.warns(ERClientAuthWarning):
                assert await client.login() is True
            assert token_route.called
            assert client.last_auth_error is None


class TestSitesThatStillAcceptAPassword:
    """The warn-versus-raise boundary: only "Auth0 and nothing else" raises."""

    @pytest.mark.asyncio
    async def test_a_migrating_site_still_only_warns(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, default_token_url, token_response,
    ):
        """A site listing both issuers may still honour the password grant."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=discovery_document)
            token_route = respx_mock.post(default_token_url).mock(
                return_value=httpx.Response(200, json=token_response))

            with pytest.warns(ERClientAuthWarning,
                              match="still works but is deprecated"):
                assert await client.login() is True

            assert token_route.called

    @pytest.mark.asyncio
    async def test_a_site_that_has_not_migrated_says_nothing(
        self, ropc_kwargs, async_client_factory, discovery_url,
        make_discovery_document, das_issuer, default_token_url,
        token_response, recwarn,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=make_discovery_document(das_issuer))
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response)

            assert await client.login() is True
            assert auth_warnings(recwarn.list) == []


class TestWithoutDiscoveryThereIsNoCheck:
    """No document, or no permission to fetch one, means the login proceeds."""

    @pytest.mark.asyncio
    async def test_a_site_serving_no_document(
        self, ropc_kwargs, async_client_factory, discovery_url,
        default_token_url, token_response,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(404)
            token_route = respx_mock.post(default_token_url).mock(
                return_value=httpx.Response(200, json=token_response))

            assert await client.login() is True
            assert token_route.called
            assert client.last_auth_error is None

    @pytest.mark.asyncio
    async def test_a_site_we_cannot_reach_for_discovery(
        self, ropc_kwargs, async_client_factory, discovery_url,
        default_token_url, token_response,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).mock(
                side_effect=httpx.ConnectError("no route to host"))
            token_route = respx_mock.post(default_token_url).mock(
                return_value=httpx.Response(200, json=token_response))

            assert await client.login() is True
            assert token_route.called

    @pytest.mark.asyncio
    async def test_opting_out_skips_the_check_along_with_the_warning(
        self, ropc_kwargs, async_client_factory, discovery_url,
        external_only_document, default_token_url, token_response,
    ):
        """discovery=False means never asking, so there is nothing to refuse on."""
        client = async_client_factory(**ropc_kwargs, discovery=False)
        async with respx.mock as respx_mock:
            discovery_route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=external_only_document))
            token_route = respx_mock.post(default_token_url).mock(
                return_value=httpx.Response(200, json=token_response))

            assert await client.login() is True
            assert not discovery_route.called
            assert token_route.called
