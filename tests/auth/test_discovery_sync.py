"""ERClient.discover(): fetching the site's protected-resource metadata.

Only explicit ``discover()`` calls are covered here — what ``login()`` and
``auth_headers()`` fetch on their own is a separate concern.

Discovery is advisory. Every failure mode has the same outcome: no metadata,
nothing raised, nothing logged above debug. A caller with working credentials
and an unreachable discovery endpoint must still be able to log in.
"""
import json
from unittest.mock import patch

import pytest
import requests

from erclient.client import ERClient
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


@pytest.fixture
def patched_get():
    """Patch the module-level requests.get the discovery fetch uses."""
    with patch("erclient.client.requests.get") as mock_get:
        yield mock_get


class TestDiscoverySucceeds:
    """The happy path: a site that serves the document."""

    def test_returns_and_stores_the_metadata(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document, service_root,
    ):
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        metadata = client.discover()

        assert metadata.resource == service_root
        assert metadata.authorization_servers == (
            f"{service_root}/oauth2", AUTH0_ISSUER)
        assert client.protected_resource_metadata is metadata

    def test_fetches_the_well_known_url(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document, discovery_url,
    ):
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        client.discover()

        assert patched_get.call_args.args[0] == discovery_url

    def test_sends_no_credentials(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document,
    ):
        """The document is public; sending auth would mean logging in first."""
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        client.discover()

        assert "Authorization" not in patched_get.call_args.kwargs["headers"]

    def test_identifies_the_client_and_asks_for_json(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document,
    ):
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        client.discover()

        assert patched_get.call_args.kwargs["headers"] == {
            "User-Agent": client.user_agent,
            "Accept": "application/json",
        }

    def test_uses_a_short_timeout(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document,
    ):
        """An advisory read must not stall a login behind a slow site."""
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        client.discover()

        assert patched_get.call_args.kwargs["timeout"] == 5


class TestDiscoveryFails:
    """Every failure is the same answer: no metadata, and nothing raised."""

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
    def test_unusable_responses_yield_no_metadata(
        self, ropc_kwargs, patched_get, make_requests_response, status_code, text,
    ):
        patched_get.return_value = make_requests_response(
            status_code, text=text)
        client = ERClient(**ropc_kwargs)

        assert client.discover() is None
        assert client.protected_resource_metadata is None

    @pytest.mark.parametrize(
        "exception",
        [
            requests.ConnectionError("no route to host"),
            requests.Timeout("timed out"),
        ],
        ids=["connection_error", "timeout"],
    )
    def test_transport_errors_are_swallowed(
        self, ropc_kwargs, patched_get, exception,
    ):
        """A site we cannot reach for discovery is not a reason to refuse a login."""
        patched_get.side_effect = exception
        client = ERClient(**ropc_kwargs)

        assert client.discover() is None
        assert client.protected_resource_metadata is None

    def test_a_later_failure_clears_earlier_metadata(
        self, ropc_kwargs, patched_get, make_requests_response, discovery_document,
    ):
        """The property reports the most recent fetch, not the best one."""
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)
        client.discover()

        patched_get.return_value = make_requests_response(404, text="")
        client.discover()

        assert client.protected_resource_metadata is None


class TestDiscoveryIsSkipped:
    """Cases where there is nothing to ask, or nobody to ask."""

    def test_no_metadata_before_the_first_fetch(self, ropc_kwargs, patched_get):
        client = ERClient(**ropc_kwargs)

        assert client.protected_resource_metadata is None
        assert not patched_get.called

    def test_a_client_without_a_service_root_asks_nobody(self, patched_get):
        client = ERClient(username="test-user", password="test-password")

        assert client.discover() is None
        assert client.protected_resource_metadata is None
        assert not patched_get.called

    def test_opting_out_does_not_disable_an_explicit_discover(
        self, ropc_kwargs, patched_get, make_requests_response, discovery_document,
    ):
        """discovery=False turns off the automatic fetches, not the method."""
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs, discovery=False)

        assert client.discover() is not None
        assert patched_get.called
