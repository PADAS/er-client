"""respx helpers shared by the async auth tests."""
import httpx

from erclient.discovery import DISCOVERY_PATH

KNOWN_ISSUER = "https://auth-dev.pamdas.org/"


def device_code_endpoint(issuer):
    """Where a tenant takes device-authorization requests."""
    return f"{issuer.rstrip('/')}/oauth/device/code"


def device_token_endpoint(issuer):
    """Where a tenant takes token requests."""
    return f"{issuer.rstrip('/')}/oauth/token"


def metadata_endpoint(issuer):
    """Where a tenant describes itself."""
    return f"{issuer.rstrip('/')}/.well-known/openid-configuration"


def mock_device_flow(respx_mock, service_root, *, issuer=KNOWN_ISSUER,
                     discovery=None, metadata=None, authorization=None,
                     token_responses=None):
    """Stand up a fake site and Auth0 tenant on a test's own respx router.

    The async counterpart of the sync ``fake_device_server`` fixture. Every
    piece is optional so a test that wants one endpoint broken says only that;
    what it does not name is left unregistered, and respx then fails loudly on
    a request the client should not have made.

    Returns the token route, whose ``calls`` are what most polling assertions
    are about.
    """
    if discovery is not None:
        respx_mock.get(f"{service_root}{DISCOVERY_PATH}").mock(
            return_value=discovery)
    if metadata is not None:
        respx_mock.get(metadata_endpoint(issuer)).mock(return_value=metadata)
    if authorization is not None:
        respx_mock.post(device_code_endpoint(issuer)).mock(
            return_value=authorization)
    if token_responses is None:
        return None
    route = respx_mock.post(device_token_endpoint(issuer))
    route.side_effect = list(token_responses)
    return route


def traffic(respx_mock):
    """Every request the client made, in order, as (method, url) pairs."""
    return [(call.request.method, str(call.request.url))
            for call in respx_mock.calls]


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
