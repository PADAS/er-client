"""respx helpers shared by the async auth tests."""
import httpx

from erclient.discovery import DISCOVERY_PATH


def mock_discovery(respx_mock, service_root, status_code=404, json_body=None):
    """Register the discovery endpoint on a test's own respx router.

    The async counterpart of the sync ``discovery_not_served`` fixture: these
    tests open their router inside the test body, so a fixture cannot reach
    it. Every async test that logs in or builds auth headers needs this, and
    respx makes a missed one fail loudly rather than letting the request
    escape to the network.

    Defaults to a site that serves no document, which is what these tests
    assumed before discovery existed.
    """
    route = respx_mock.get(f"{service_root}{DISCOVERY_PATH}")
    route.return_value = httpx.Response(status_code, json=json_body)
    return route
