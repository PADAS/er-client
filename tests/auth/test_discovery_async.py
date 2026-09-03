"""AsyncERClient.discover(): fetching the site's protected-resource metadata.

The async mirror of ``test_discovery_sync.py``. Only explicit ``discover()``
calls are covered here — what ``login()`` and ``auth_headers()`` fetch on their
own is a separate concern.

Discovery is advisory. Every failure mode has the same outcome: no metadata,
nothing raised, nothing logged above debug.
"""
import json

import httpx
import pytest
import respx

from erclient.discovery import DISCOVERY_PATH

AUTH0_ISSUER = "https://fake-tenant.us.auth0.com"


@pytest.fixture
def discovery_url(service_root):
    return f"{service_root}{DISCOVERY_PATH}"


@pytest.fixture
def discovery_document(service_root):
    """A document a migrating site would serve: its own issuer plus Auth0."""
    return {
        "resource": service_root,
        "authorization_servers": [f"{service_root}/oauth2", AUTH0_ISSUER],
    }


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
