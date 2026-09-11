"""AsyncERClient refuses credentials the site's discovery document rules out.

The async mirror of ``test_mismatch_sync.py``, with one difference the sync
client cannot have: ``login()`` already raised on failure here, so a mismatch
raises out of it directly rather than returning a bool.

A caller who brought their own token never calls ``login()``, so for those the
refusal happens in ``auth_headers()``, which every API call goes through.
"""
import asyncio

import httpx
import pytest
import respx
from tests.auth.conftest import (AUTH0_ISSUER, JWT_TOKEN, JWT_WITH_ISSUER,
                                 auth_warnings, jwt_with_issuer)

from erclient.er_errors import (CREDENTIAL_SITE_MISMATCH, ERClientAuthWarning,
                                ERClientBadCredentials)

OTHER_ISSUER = "https://someone-elses-tenant.us.auth0.com"


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


class TestOpaqueTokenAtAMigratedSite:
    """A site listing only Auth0 rejects every token its own endpoint issued."""

    @pytest.mark.asyncio
    async def test_auth_headers_raises_instead_of_returning_them(
        self, token_kwargs, async_client_factory, discovery_url,
        external_only_document, opaque_token_mismatch_message,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.auth_headers()

            assert str(exc_info.value) == opaque_token_mismatch_message

    @pytest.mark.asyncio
    async def test_every_later_call_raises_too_without_refetching(
        self, token_kwargs, async_client_factory, discovery_url,
        external_only_document, opaque_token_mismatch_message,
    ):
        """A client holding a token the site cannot accept is unusable, not
        merely unlucky the first time."""
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=external_only_document))

            for _ in range(3):
                with pytest.raises(ERClientBadCredentials) as exc_info:
                    await client.auth_headers()
                assert str(exc_info.value) == opaque_token_mismatch_message

            assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_no_api_call_is_attempted(
        self, token_kwargs, async_client_factory, discovery_url,
        external_only_document, service_root,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)
            api_route = respx_mock.get(f"{service_root}/api/v1.0/user/me")

            with pytest.raises(ERClientBadCredentials):
                await client.get_me()

            assert not api_route.called

    @pytest.mark.asyncio
    async def test_two_first_callers_at_once_both_run_the_check(
        self, token_kwargs, async_client_factory, discovery_url,
        external_only_document, service_root,
    ):
        """Neither caller may skip the check because the other is mid-fetch.

        The discovery response is held until both callers have asked for it,
        so the second arrives while the first is still awaiting discovery. If
        the check were marked done before the fetch, the second would skip it
        and send the token to the API; instead both fetch and both refuse.
        """
        client = async_client_factory(**token_kwargs)
        both_arrived = asyncio.Event()
        arrivals = 0

        async def hold_until_both_arrive(request):
            nonlocal arrivals
            arrivals += 1
            if arrivals < 2:
                await both_arrived.wait()
            else:
                both_arrived.set()
            return httpx.Response(200, json=external_only_document)

        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url).mock(
                side_effect=hold_until_both_arrive)
            api_route = respx_mock.get(f"{service_root}/api/v1.0/user/me").mock(
                return_value=httpx.Response(200, json={"username": "x"}))

            # The timeout is only a guard against the old ordering, where the
            # first caller would wait forever for a second arrival that skipped
            # discovery.
            outcomes = await asyncio.wait_for(
                asyncio.gather(client.get_me(), client.get_me(),
                               return_exceptions=True),
                timeout=5)

            assert all(isinstance(outcome, ERClientBadCredentials)
                       for outcome in outcomes)
            assert route.call_count == 2
            assert not api_route.called

    @pytest.mark.asyncio
    async def test_the_reason_names_no_request_because_there_was_none(
        self, token_kwargs, async_client_factory, discovery_url,
        external_only_document, opaque_token_mismatch_message,
    ):
        """Token mode posts to no token endpoint, so there is nothing to name."""
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)

            with pytest.raises(ERClientBadCredentials):
                await client.auth_headers()

            auth_error = client.last_auth_error
            assert auth_error.error == CREDENTIAL_SITE_MISMATCH
            assert auth_error.error_description == opaque_token_mismatch_message
            assert auth_error.url is None
            assert auth_error.grant_type is None
            assert auth_error.status_code is None
            assert auth_error.response_body is None

    @pytest.mark.asyncio
    async def test_the_deprecation_warning_gives_way_to_the_error(
        self, token_kwargs, async_client_factory, discovery_url,
        external_only_document, recwarn,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)

            with pytest.raises(ERClientBadCredentials):
                await client.auth_headers()

            assert auth_warnings(recwarn.list) == []


class TestJwtFromAnUnlistedIssuer:
    """DAS validates ``iss`` against the string discovery advertises, so a JWT
    from anywhere else is rejected on every kind of site."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "issuers", [("das",), ("das", "auth0"), ("auth0",)],
        ids=["not_migrated", "migrating", "migrated"],
    )
    async def test_it_is_refused_wherever_the_site_is_in_its_migration(
        self, service_root, async_client_factory, discovery_url,
        make_discovery_document, das_issuer, issuers, unlisted_issuer_message,
    ):
        lookup = {"das": das_issuer, "auth0": AUTH0_ISSUER}
        accepted = [lookup[name] for name in issuers]
        client = async_client_factory(service_root=service_root,
                                      token=jwt_with_issuer(OTHER_ISSUER))
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=make_discovery_document(*accepted))

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.auth_headers()

            assert str(exc_info.value) == unlisted_issuer_message(
                OTHER_ISSUER, accepted)

    @pytest.mark.asyncio
    async def test_no_api_call_is_attempted(
        self, service_root, async_client_factory, discovery_url,
        external_only_document,
    ):
        client = async_client_factory(service_root=service_root,
                                      token=jwt_with_issuer(OTHER_ISSUER))
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)
            api_route = respx_mock.get(f"{service_root}/api/v1.0/user/me")

            with pytest.raises(ERClientBadCredentials):
                await client.get_me()

            assert not api_route.called


class TestJwtsTheSiteHasNoQuarrelWith:
    """Only an issuer we can read *and* the site does not list is refused."""

    @pytest.mark.asyncio
    async def test_a_listed_issuer_differing_only_by_a_trailing_slash(
        self, service_root, async_client_factory, discovery_url,
        external_only_document, recwarn,
    ):
        client = async_client_factory(
            service_root=service_root, token=JWT_WITH_ISSUER)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)

            headers = await client.auth_headers()

            assert headers["Authorization"] == f"Bearer {JWT_WITH_ISSUER}"
            assert auth_warnings(recwarn.list) == []

    @pytest.mark.asyncio
    async def test_the_api_call_goes_through(
        self, service_root, async_client_factory, discovery_url,
        external_only_document,
    ):
        client = async_client_factory(
            service_root=service_root, token=JWT_WITH_ISSUER)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)
            api_route = respx_mock.get(
                f"{service_root}/api/v1.0/user/me").mock(
                return_value=httpx.Response(200, json={"data": {"username": "me"}}))

            assert await client.get_me() == {"username": "me"}
            assert api_route.called

    @pytest.mark.asyncio
    async def test_a_jwt_whose_payload_we_cannot_read(
        self, service_root, async_client_factory, discovery_url,
        external_only_document, recwarn,
    ):
        """Unreadable is not the same as wrong; the server still gets to judge."""
        client = async_client_factory(
            service_root=service_root, token=JWT_TOKEN)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=external_only_document)

            headers = await client.auth_headers()

            assert headers["Authorization"] == f"Bearer {JWT_TOKEN}"
            assert auth_warnings(recwarn.list) == []


class TestTokensTheSiteMayStillAccept:
    """The warn-versus-raise boundary, in token mode."""

    @pytest.mark.asyncio
    async def test_an_opaque_token_at_a_migrating_site_still_only_warns(
        self, token_kwargs, async_client_factory, discovery_url,
        discovery_document,
    ):
        """A DAS token still works for a bypass_auth0 application there."""
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=discovery_document)

            with pytest.warns(ERClientAuthWarning, match="looks like a legacy"):
                headers = await client.auth_headers()

            assert headers["Authorization"].startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_an_opaque_token_at_a_site_that_has_not_migrated(
        self, token_kwargs, async_client_factory, discovery_url,
        make_discovery_document, das_issuer, recwarn,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=make_discovery_document(das_issuer))

            headers = await client.auth_headers()

            assert headers["Authorization"].startswith("Bearer ")
            assert auth_warnings(recwarn.list) == []


class TestWithoutDiscoveryThereIsNoTokenCheck:
    """No document, or no permission to fetch one, means the token is used."""

    @pytest.mark.asyncio
    async def test_an_opaque_token_at_a_site_serving_no_document(
        self, token_kwargs, async_client_factory, discovery_url,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(404)

            headers = await client.auth_headers()

            assert headers["Authorization"].startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_a_jwt_from_an_unlisted_issuer_at_such_a_site(
        self, service_root, async_client_factory, discovery_url,
    ):
        client = async_client_factory(service_root=service_root,
                                      token=jwt_with_issuer(OTHER_ISSUER))
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(404)

            headers = await client.auth_headers()

            assert headers["Authorization"].startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_opting_out_skips_the_check_along_with_the_warning(
        self, token_kwargs, async_client_factory, discovery_url,
        external_only_document,
    ):
        client = async_client_factory(**token_kwargs, discovery=False)
        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=external_only_document))

            headers = await client.auth_headers()

            assert headers["Authorization"].startswith("Bearer ")
            assert not route.called
