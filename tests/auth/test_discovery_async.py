"""AsyncERClient discovery: fetching the site's protected-resource metadata,
and warning when the credentials in hand look legacy for that site.

The async mirror of ``test_discovery_sync.py``. Discovery is advisory: every
failure mode has the same outcome — no metadata, nothing raised, nothing
logged above debug.

The warnings are matched here on a distinctive fragment rather than in full;
``tests/test_discovery.py`` pins the exact wording of every message.
"""
import json
import logging

import httpx
import pytest
import respx

from erclient.discovery import DISCOVERY_PATH
from erclient.er_errors import ERClientAuthWarning

AUTH0_ISSUER = "https://fake-tenant.us.auth0.com"
# A JWT-shaped token: header is real base64url, the rest is plainly fake.
JWT_TOKEN = ("eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9"
             ".DUMMY-PAYLOAD.DUMMY-SIGNATURE")


def auth_warnings(recorded):
    """Only this client's auth warnings, ignoring anything else the run emits."""
    return [w for w in recorded if issubclass(w.category, ERClientAuthWarning)]


@pytest.fixture
def discovery_url(service_root):
    return f"{service_root}{DISCOVERY_PATH}"


@pytest.fixture
def das_issuer(service_root):
    """The site's own legacy token endpoint, as it lists itself."""
    return f"{service_root}/oauth2"


@pytest.fixture
def make_discovery_document(service_root):
    """Build a document listing whichever authorization servers a test needs."""

    def _factory(*authorization_servers):
        return {
            "resource": service_root,
            "authorization_servers": list(authorization_servers),
        }

    return _factory


@pytest.fixture
def discovery_document(make_discovery_document, das_issuer):
    """A document a migrating site would serve: its own issuer plus Auth0."""
    return make_discovery_document(das_issuer, AUTH0_ISSUER)


class TestDiscoverySucceeds:
    """The happy path: a site that serves the document."""

    @pytest.mark.asyncio
    async def test_returns_and_stores_the_metadata(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, service_root,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=discovery_document)

            metadata = await client.discover()

            assert metadata.resource == service_root
            assert metadata.authorization_servers == (
                f"{service_root}/oauth2", AUTH0_ISSUER)
            assert client.protected_resource_metadata is metadata

    @pytest.mark.asyncio
    async def test_sends_no_credentials(
        self, ropc_kwargs, async_client_factory, discovery_url, discovery_document,
    ):
        """The document is public; sending auth would mean logging in first."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))

            await client.discover()

            assert "authorization" not in route.calls.last.request.headers

    @pytest.mark.asyncio
    async def test_identifies_the_client_and_asks_for_json(
        self, ropc_kwargs, async_client_factory, discovery_url, discovery_document,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))

            await client.discover()

            request = route.calls.last.request
            assert request.headers["user-agent"] == client.user_agent
            assert request.headers["accept"] == "application/json"


class TestDiscoveryFails:
    """Every failure is the same answer: no metadata, and nothing raised."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "status_code, text",
        [
            (404, ""),
            (500, "<html><body>Server Error</body></html>"),
            (200, "<html><body>Single Page App</body></html>"),
            (200, json.dumps({"resource": "https://other-site.erdomain.org",
                              "authorization_servers": [AUTH0_ISSUER]})),
        ],
        ids=["not_found", "server_error",
             "not_json", "resource_is_another_host"],
    )
    async def test_unusable_responses_yield_no_metadata(
        self, ropc_kwargs, async_client_factory, discovery_url, status_code, text,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                status_code, text=text)

            assert await client.discover() is None
            assert client.protected_resource_metadata is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exception",
        [
            httpx.ConnectError("no route to host"),
            httpx.ReadTimeout("timed out"),
        ],
        ids=["connection_error", "timeout"],
    )
    async def test_transport_errors_are_swallowed(
        self, ropc_kwargs, async_client_factory, discovery_url, exception,
    ):
        """A site we cannot reach for discovery is not a reason to refuse a login."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).mock(side_effect=exception)

            assert await client.discover() is None
            assert client.protected_resource_metadata is None

    @pytest.mark.asyncio
    async def test_a_later_failure_clears_earlier_metadata(
        self, ropc_kwargs, async_client_factory, discovery_url, discovery_document,
    ):
        """The property reports the most recent fetch, not the best one."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url)
            route.return_value = httpx.Response(200, json=discovery_document)
            await client.discover()

            route.return_value = httpx.Response(404)
            await client.discover()

            assert client.protected_resource_metadata is None


class TestDiscoveryIsSkipped:
    """Cases where there is nothing to ask, or nobody to ask."""

    @pytest.mark.asyncio
    async def test_no_metadata_before_the_first_fetch(
        self, ropc_kwargs, async_client_factory,
    ):
        client = async_client_factory(**ropc_kwargs)

        assert client.protected_resource_metadata is None

    @pytest.mark.asyncio
    async def test_a_client_without_a_service_root_asks_nobody(
        self, async_client_factory,
    ):
        client = async_client_factory(
            username="test-user", password="test-password")
        async with respx.mock(assert_all_called=False) as respx_mock:

            assert await client.discover() is None
            assert client.protected_resource_metadata is None
            assert len(respx_mock.calls) == 0

    @pytest.mark.asyncio
    async def test_opting_out_does_not_disable_an_explicit_discover(
        self, ropc_kwargs, async_client_factory, discovery_url, discovery_document,
    ):
        """discovery=False turns off the automatic fetches, not the method."""
        client = async_client_factory(**ropc_kwargs, discovery=False)
        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))

            assert await client.discover() is not None
            assert route.called


@pytest.mark.filterwarnings("ignore::erclient.er_errors.ERClientAuthWarning")
class TestLoginDiscovers:
    """A password grant is a decision about auth, so it asks the site first."""

    @pytest.mark.asyncio
    async def test_discovery_precedes_the_token_request(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, default_token_url, token_response,
    ):
        """Ordering, not just counts: the answer is worthless after the POST."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=discovery_document)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response)

            await client.login()

            assert [(call.request.method, str(call.request.url))
                    for call in respx_mock.calls] == [
                ("GET", discovery_url), ("POST", default_token_url)]

    @pytest.mark.asyncio
    async def test_every_login_refetches(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, default_token_url, token_response,
    ):
        """No cache: a site that migrates mid-process is noticed at the next login."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            discovery_route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response)

            await client.login()
            await client.login()
            await client.login()

            assert discovery_route.call_count == 3

    @pytest.mark.asyncio
    async def test_refreshing_does_not_discover(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, default_token_url, token_response,
    ):
        """A refresh decides nothing about which credentials to use."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            discovery_route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response)
            await client.login()
            discovery_route.reset()

            await client.refresh_token()

            assert not discovery_route.called

    @pytest.mark.asyncio
    async def test_opting_out_keeps_login_offline_but_for_the_token_request(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, default_token_url, token_response,
    ):
        client = async_client_factory(**ropc_kwargs, discovery=False)
        async with respx.mock as respx_mock:
            discovery_route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response)

            await client.login()
            await client.refresh_token()

            assert not discovery_route.called

    @pytest.mark.asyncio
    async def test_a_failed_discovery_does_not_stop_the_login(
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


@pytest.mark.filterwarnings("ignore::erclient.er_errors.ERClientAuthWarning")
class TestTokenModeDiscovers:
    """A caller who brought their own token never calls login(), so
    auth_headers() is the only place left to look at the site."""

    @pytest.mark.asyncio
    async def test_the_first_call_discovers(
        self, token_kwargs, async_client_factory, discovery_url, discovery_document,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))

            await client.auth_headers()

            assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_later_calls_issue_nothing(
        self, token_kwargs, async_client_factory, discovery_url, discovery_document,
    ):
        """Every API call goes through auth_headers(); only the first may fetch."""
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))

            for _ in range(6):
                await client.auth_headers()

            assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_the_token_endpoint_is_left_alone(
        self, token_kwargs, async_client_factory, discovery_url,
        discovery_document, default_token_url,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=discovery_document)
            token_route = respx_mock.post(default_token_url)

            await client.auth_headers()

            assert not token_route.called

    @pytest.mark.asyncio
    async def test_opting_out_keeps_token_mode_offline(
        self, token_kwargs, async_client_factory, discovery_url, discovery_document,
    ):
        client = async_client_factory(**token_kwargs, discovery=False)
        async with respx.mock as respx_mock:
            route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))

            await client.auth_headers()

            assert not route.called


class TestWarnsAboutLegacyCredentials:
    """The warning table, from the client's side."""

    @pytest.mark.asyncio
    async def test_password_grant_at_a_migrating_site(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, default_token_url, token_response, caplog,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=discovery_document)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response)

            with caplog.at_level(logging.WARNING):
                with pytest.warns(ERClientAuthWarning,
                                  match="still works but is deprecated"):
                    await client.login()

        assert "still works but is deprecated" in caplog.text

    @pytest.mark.asyncio
    async def test_password_grant_at_a_migrated_site(
        self, ropc_kwargs, async_client_factory, discovery_url,
        make_discovery_document, default_token_url, token_response,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=make_discovery_document(AUTH0_ISSUER))
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response)

            with pytest.warns(ERClientAuthWarning,
                              match="accepts only Auth0-issued tokens"):
                await client.login()

    @pytest.mark.asyncio
    async def test_opaque_token_at_a_migrating_site(
        self, token_kwargs, async_client_factory, discovery_url,
        discovery_document, caplog,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=discovery_document)

            with caplog.at_level(logging.WARNING):
                with pytest.warns(ERClientAuthWarning, match="looks like a legacy"):
                    await client.auth_headers()

        assert "looks like a legacy" in caplog.text

    @pytest.mark.asyncio
    async def test_opaque_token_at_a_migrated_site(
        self, token_kwargs, async_client_factory, discovery_url,
        make_discovery_document,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=make_discovery_document(AUTH0_ISSUER))

            with pytest.warns(ERClientAuthWarning, match="Requests will be rejected"):
                await client.auth_headers()

    @pytest.mark.asyncio
    async def test_the_same_warning_is_issued_once_per_client(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, default_token_url, token_response, caplog, recwarn,
    ):
        """A retry loop must not turn one deprecation into a wall of noise."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            discovery_route = respx_mock.get(discovery_url).mock(
                return_value=httpx.Response(200, json=discovery_document))
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response)

            with caplog.at_level(logging.WARNING):
                await client.login()
                await client.login()

            assert len(auth_warnings(recwarn.list)) == 1
            assert len([r for r in caplog.records
                        if "Auth0" in r.getMessage()]) == 1
            assert discovery_route.call_count == 2


class TestStaysSilent:
    """Silence is the default: only an external issuer makes credentials legacy."""

    @pytest.mark.asyncio
    async def test_password_grant_at_a_site_that_has_not_migrated(
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

            await client.login()

            assert auth_warnings(recwarn.list) == []

    @pytest.mark.asyncio
    async def test_opaque_token_at_a_site_that_has_not_migrated(
        self, token_kwargs, async_client_factory, discovery_url,
        make_discovery_document, das_issuer, recwarn,
    ):
        client = async_client_factory(**token_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=make_discovery_document(das_issuer))

            await client.auth_headers()

            assert auth_warnings(recwarn.list) == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "issuers", [("das", "auth0"), ("auth0",)], ids=["migrating", "migrated"],
    )
    async def test_a_jwt_is_never_warned_about(
        self, service_root, async_client_factory, discovery_url,
        make_discovery_document, das_issuer, issuers, recwarn,
    ):
        """A modern token is what the warnings are asking callers to move to."""
        lookup = {"das": das_issuer, "auth0": AUTH0_ISSUER}
        client = async_client_factory(
            service_root=service_root, token=JWT_TOKEN)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=make_discovery_document(
                    *(lookup[name] for name in issuers)))

            await client.auth_headers()

            assert auth_warnings(recwarn.list) == []

    @pytest.mark.asyncio
    async def test_a_site_with_no_metadata_says_nothing(
        self, ropc_kwargs, async_client_factory, discovery_url,
        default_token_url, token_response, recwarn,
    ):
        """Unavailable metadata is not evidence of anything."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(404)
            respx_mock.post(default_token_url).return_value = httpx.Response(
                200, json=token_response)

            await client.login()

            assert auth_warnings(recwarn.list) == []


class TestRedirects:
    """Sites redirect .well-known paths; sync follows them, so async must too."""

    @pytest.mark.asyncio
    async def test_a_redirect_is_followed(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, service_root,
    ):
        client = async_client_factory(**ropc_kwargs)
        elsewhere = f"{service_root}/moved/oauth-protected-resource"
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                301, headers={"Location": elsewhere})
            respx_mock.get(elsewhere).return_value = httpx.Response(
                200, json=discovery_document)

            assert await client.discover() is not None

    @pytest.mark.asyncio
    async def test_a_document_reached_on_another_host_is_discarded(
        self, ropc_kwargs, async_client_factory, discovery_url,
    ):
        """RFC 9728 section 3.3: the document must name the resource we asked about."""
        client = async_client_factory(**ropc_kwargs)
        other_site = "https://other-site.erdomain.org"
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                301, headers={"Location": f"{other_site}{DISCOVERY_PATH}"})
            respx_mock.get(f"{other_site}{DISCOVERY_PATH}").return_value = httpx.Response(
                200, json={"resource": other_site, "authorization_servers": []})

            assert await client.discover() is None


class TestTokenTransportErrorsStillPropagate:
    """Discovery swallows its own transport errors; the token endpoint's are
    still the caller's to see.

    Both halves matter. A caller with working credentials and an unreachable
    discovery endpoint must still be able to log in, and a caller whose token
    endpoint is unreachable must still get the real transport error rather
    than a classified login failure.
    """

    @pytest.mark.asyncio
    async def test_a_connection_error_on_the_token_post_is_raised_raw(
        self, ropc_kwargs, async_client_factory, discovery_url, default_token_url,
    ):
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(404)
            respx_mock.post(default_token_url).mock(
                side_effect=httpx.ConnectError("no route to host"))

            with pytest.raises(httpx.ConnectError):
                await client.login()

    @pytest.mark.asyncio
    async def test_the_same_when_discovery_did_serve_a_document(
        self, ropc_kwargs, async_client_factory, discovery_url,
        discovery_document, default_token_url,
    ):
        """Having metadata in hand changes nothing about how the POST fails."""
        client = async_client_factory(**ropc_kwargs)
        async with respx.mock as respx_mock:
            respx_mock.get(discovery_url).return_value = httpx.Response(
                200, json=discovery_document)
            respx_mock.post(default_token_url).mock(
                side_effect=httpx.ConnectError("no route to host"))

            with pytest.warns(ERClientAuthWarning):
                with pytest.raises(httpx.ConnectError):
                    await client.login()
