"""Tests for routing a site to the right authentication method.

authenticate_for_site asks the site what it accepts and then acts on the answer.
While the device flow is still being built, the rule is deliberately narrow:
take the password grant wherever the site still offers it, and refuse clearly
where it does not.
"""
import httpx
import pytest
import respx

from erclient.auth import authenticate_for_site
from erclient.er_errors import (ERClientAuthMethodUnavailable,
                                ERClientDiscoveryError)

from .conftest import AUTH0_ISSUER, DAS_ISSUER, DISCOVERY_URL, SITE

TOKEN_URL = DAS_ISSUER + "/token"

CREDENTIALS = dict(username="hank", password="hunter2",
                   client_id="das_web_client")

TOKEN_RESPONSE = {
    "access_token": "an-access-token",
    "token_type": "Bearer",
    "expires_in": 172800,
}


def _mock_discovery(discovery_document, authorization_servers):
    return respx.get(DISCOVERY_URL).mock(
        return_value=httpx.Response(
            200, json=discovery_document(authorization_servers))
    )


def _mock_token():
    return respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=TOKEN_RESPONSE))


@respx.mock
def test_site_offering_only_the_password_grant_uses_it(discovery_document):
    discovery = _mock_discovery(discovery_document, [DAS_ISSUER])
    token = _mock_token()

    assert authenticate_for_site(
        SITE, **CREDENTIALS).access_token == "an-access-token"
    assert discovery.called
    assert token.called


@respx.mock
def test_credentials_reach_the_token_request(discovery_document):
    _mock_discovery(discovery_document, [DAS_ISSUER])
    token = _mock_token()

    authenticate_for_site(SITE, **CREDENTIALS)

    sent = dict(httpx.QueryParams(token.calls.last.request.content.decode()))
    assert sent == {
        "grant_type": "password",
        "username": "hank",
        "password": "hunter2",
        "client_id": "das_web_client",
    }


@respx.mock
def test_site_offering_both_still_takes_the_password_grant(discovery_document):
    """During migration a site advertises the external issuer first; we take the
    familiar path anyway, because that is the one this version can complete."""
    _mock_discovery(discovery_document, [AUTH0_ISSUER, DAS_ISSUER])
    token = _mock_token()

    with pytest.warns(UserWarning) as recorded:
        result = authenticate_for_site(SITE, **CREDENTIALS)

    assert result.access_token == "an-access-token"
    assert token.called
    # The warning has to name the issuer being passed over, or nobody can tell
    # which site is mid-migration.
    assert AUTH0_ISSUER in str(recorded[0].message)


@respx.mock
def test_no_warning_when_the_password_grant_is_all_that_is_offered(
        discovery_document, recwarn):
    """A site that has not started migrating is unremarkable; do not nag about it."""
    _mock_discovery(discovery_document, [DAS_ISSUER])
    _mock_token()

    authenticate_for_site(SITE, **CREDENTIALS)

    assert [str(warning.message) for warning in recwarn] == []


@respx.mock
@pytest.mark.parametrize(
    "credentials",
    [
        {},
        {"username": "hank"},
        {"password": "hunter2"},
        {"client_id": "das_web_client"},
    ],
    ids=["nothing", "username_only", "password_only", "client_id_only"],
)
def test_password_grant_without_a_full_credential_pair_is_refused(
        credentials, discovery_document):
    _mock_discovery(discovery_document, [DAS_ISSUER])

    with pytest.raises(ERClientAuthMethodUnavailable) as exc_info:
        authenticate_for_site(SITE, **credentials)

    assert "username" in str(exc_info.value)


@respx.mock
@pytest.mark.parametrize(
    "credentials", [CREDENTIALS, {}], ids=["with_credentials", "without_credentials"])
def test_site_offering_no_password_grant_is_refused(credentials, discovery_document):
    """The end state, once a site stops accepting the password grant entirely.

    A username and password cannot help here, so say so rather than sending
    them somewhere that will reject them.
    """
    _mock_discovery(discovery_document, [AUTH0_ISSUER])

    with pytest.raises(ERClientAuthMethodUnavailable) as exc_info:
        authenticate_for_site(SITE, **credentials)

    assert AUTH0_ISSUER in str(exc_info.value)


@respx.mock
def test_no_token_request_is_made_when_the_site_offers_no_password_grant(
        discovery_document):
    """Credentials must not be sent anywhere the site did not point us."""
    _mock_discovery(discovery_document, [AUTH0_ISSUER])
    token = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=TOKEN_RESPONSE))

    with pytest.raises(ERClientAuthMethodUnavailable):
        authenticate_for_site(SITE, **CREDENTIALS)

    assert not token.called


@respx.mock
def test_a_full_api_root_routes_the_same_as_an_origin(discovery_document):
    """Callers pass whatever they hand ERClient, up to and including /api/v1.0."""
    _mock_discovery(discovery_document, [DAS_ISSUER])
    token = _mock_token()

    authenticate_for_site(SITE + "/api/v1.0", **CREDENTIALS)

    assert token.called


@respx.mock
def test_discovery_failure_is_not_reinterpreted_as_an_auth_problem():
    """A site that cannot be asked is a discovery error, not a credential one."""
    respx.get(DISCOVERY_URL).mock(return_value=httpx.Response(404, json={}))

    with pytest.raises(ERClientDiscoveryError):
        authenticate_for_site(SITE, **CREDENTIALS)
