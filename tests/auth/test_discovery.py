"""Tests for RFC 9728 protected-resource discovery.

The client asks a site which authorization server(s) it accepts before it holds
a token, by fetching /.well-known/oauth-protected-resource. Everything here is
about getting a trustworthy list out of that endpoint -- what we then do with
the list is the routing tests' problem.
"""
import httpx
import pytest
import respx

from erclient.auth import discover_authorization_servers
from erclient.er_errors import ERClientDiscoveryError

from .conftest import AUTH0_ISSUER, DAS_ISSUER, DISCOVERY_URL, SITE


@respx.mock
def test_returns_the_advertised_authorization_servers(discovery_document):
    route = respx.get(DISCOVERY_URL).mock(
        return_value=httpx.Response(
            200, json=discovery_document([AUTH0_ISSUER, DAS_ISSUER]))
    )

    assert discover_authorization_servers(SITE) == [AUTH0_ISSUER, DAS_ISSUER]
    assert route.called


@respx.mock
@pytest.mark.parametrize(
    "site",
    [
        SITE,
        SITE + "/",
        SITE + "/api",
        SITE + "/api/v1.0",
    ],
    ids=["origin", "trailing_slash", "api", "api_v1"],
)
def test_discovery_url_is_built_from_the_site_origin(site, discovery_document):
    """Callers pass whatever they pass to ERClient, including a full API root."""
    route = respx.get(DISCOVERY_URL).mock(
        return_value=httpx.Response(200, json=discovery_document([DAS_ISSUER]))
    )

    assert discover_authorization_servers(site) == [DAS_ISSUER]
    assert route.called


@respx.mock
def test_resource_mismatch_is_rejected(discovery_document):
    """RFC 9728 s3.3: discard a document whose resource is not the origin we fetched."""
    respx.get(DISCOVERY_URL).mock(
        return_value=httpx.Response(
            200,
            json=discovery_document(
                [DAS_ISSUER], resource="https://impostor.erdomain.org"),
        )
    )

    with pytest.raises(ERClientDiscoveryError) as exc_info:
        discover_authorization_servers(SITE)

    # The message has to name both sides, or the failure is undiagnosable.
    assert "impostor.erdomain.org" in str(exc_info.value)
    assert SITE in str(exc_info.value)


@respx.mock
def test_trailing_slash_on_resource_is_not_a_match(discovery_document):
    """Issuer and resource comparisons are string-exact, per spec."""
    respx.get(DISCOVERY_URL).mock(
        return_value=httpx.Response(200, json=discovery_document(
            [DAS_ISSUER], resource=SITE + "/"))
    )

    with pytest.raises(ERClientDiscoveryError):
        discover_authorization_servers(SITE)


@respx.mock
@pytest.mark.parametrize("status_code", [400, 401, 404, 500, 503])
def test_non_2xx_discovery_is_an_error(status_code):
    """A site too old to serve the endpoint 404s; that is a discovery failure, not a route."""
    respx.get(DISCOVERY_URL).mock(
        return_value=httpx.Response(status_code, json={}))

    with pytest.raises(ERClientDiscoveryError) as exc_info:
        discover_authorization_servers(SITE)

    assert exc_info.value.status_code == status_code


@respx.mock
def test_malformed_json_is_an_error():
    respx.get(DISCOVERY_URL).mock(
        return_value=httpx.Response(200, text="<html>not json</html>")
    )

    with pytest.raises(ERClientDiscoveryError):
        discover_authorization_servers(SITE)


@respx.mock
@pytest.mark.parametrize(
    "document",
    [
        {"resource": SITE},
        {"resource": SITE, "authorization_servers": []},
        {"resource": SITE, "authorization_servers": "not-a-list"},
        {"authorization_servers": [DAS_ISSUER]},
        [DAS_ISSUER],
    ],
    ids=["missing_key", "empty_list", "not_a_list",
         "missing_resource", "not_an_object"],
)
def test_unusable_document_shapes_are_errors(document):
    respx.get(DISCOVERY_URL).mock(
        return_value=httpx.Response(200, json=document))

    with pytest.raises(ERClientDiscoveryError):
        discover_authorization_servers(SITE)


@respx.mock
def test_unreachable_site_is_a_discovery_error():
    respx.get(DISCOVERY_URL).mock(
        side_effect=httpx.ConnectError("no route to host"))

    with pytest.raises(ERClientDiscoveryError) as exc_info:
        discover_authorization_servers(SITE)

    assert SITE in str(exc_info.value)
