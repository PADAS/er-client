"""Tests for the password-grant leg.

This is the token request the client has always sent for sites that issue their
own tokens. It is reproduced here so authenticate_for_site can reach it without
constructing an ERClient, and it has to stay byte-for-byte what ERClient.login()
sends -- the pinning test below is what holds that.
"""
import httpx
import pytest
import respx

from erclient.auth import AccessToken, authenticate_with_password
from erclient.client import ERClient
from erclient.er_errors import (ERClientBadCredentials, ERClientException,
                                ERClientServiceUnreachable)

from .conftest import DAS_ISSUER, SITE

TOKEN_URL = DAS_ISSUER + "/token"

CREDENTIALS = dict(username="hank", password="hunter2",
                   client_id="das_web_client")


def _token_response(**overrides):
    payload = {
        "access_token": "an-access-token",
        "token_type": "Bearer",
        "expires_in": 172800,
        "scope": "read write",
    }
    payload.update(overrides)
    return payload


@respx.mock
def test_returns_the_issued_token():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_response()))

    token = authenticate_with_password(DAS_ISSUER, **CREDENTIALS)

    assert isinstance(token, AccessToken)
    assert token.access_token == "an-access-token"
    assert token.token_type == "Bearer"
    assert token.expires_in == 172800
    assert token.scope == "read write"
    assert token.refresh_token is None


@respx.mock
def test_refresh_token_is_carried_when_the_server_issues_one():
    """The library does nothing with it, but it must not silently drop it either."""
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json=_token_response(refresh_token="a-refresh-token"))
    )

    assert authenticate_with_password(
        DAS_ISSUER, **CREDENTIALS).refresh_token == "a-refresh-token"


def test_repr_shows_neither_token():
    """A logged or printed AccessToken must not hand out live credentials."""
    token = AccessToken(access_token="an-access-token",
                        refresh_token="a-refresh-token")

    assert "an-access-token" not in repr(token)
    assert "a-refresh-token" not in repr(token)


@respx.mock
def test_request_body_matches_what_erclient_login_sends():
    """Pinning test: this leg must stay identical to the client's existing login."""
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_response()))

    authenticate_with_password(DAS_ISSUER, **CREDENTIALS)

    sent = dict(httpx.QueryParams(route.calls.last.request.content.decode()))
    assert sent == {
        "grant_type": "password",
        "username": "hank",
        "password": "hunter2",
        "client_id": "das_web_client",
    }
    assert route.calls.last.request.headers["content-type"] == "application/x-www-form-urlencoded"


@respx.mock
def test_omitted_client_id_is_left_out_of_the_body():
    """requests drops a None form value; httpx would send client_id= instead.

    ERClient.login() has always built its body with requests, so an omitted
    client_id has always meant an absent key -- not an empty one.
    """
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_response()))

    authenticate_with_password(DAS_ISSUER, username="hank", password="hunter2")

    assert "client_id" not in route.calls.last.request.content.decode()


def test_token_url_matches_the_clients_default():
    """The issuer plus /token is the same endpoint ERClient derives on its own."""
    client = ERClient(service_root=SITE, provider_key="test")

    assert client.token_url == TOKEN_URL


@respx.mock
@pytest.mark.parametrize("status_code", [400, 401])
@pytest.mark.parametrize("error", ["invalid_grant", "invalid_client"])
def test_rejected_credentials_raise_bad_credentials(status_code, error):
    """A wrong password comes back as invalid_grant; a wrong client_id as invalid_client."""
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            status_code, json={"error": error})
    )

    with pytest.raises(ERClientBadCredentials) as exc_info:
        authenticate_with_password(DAS_ISSUER, **CREDENTIALS)

    assert exc_info.value.status_code == status_code
    assert error in exc_info.value.response_body


@respx.mock
@pytest.mark.parametrize("error", ["invalid_request", "unsupported_grant_type"])
def test_a_400_that_blames_the_request_is_not_bad_credentials(error):
    """RFC 6749 uses the same 400 for a broken request; re-typing a password fixes nothing."""
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(400, json={"error": error}))

    with pytest.raises(ERClientException) as exc_info:
        authenticate_with_password(DAS_ISSUER, **CREDENTIALS)

    assert not isinstance(exc_info.value, ERClientBadCredentials)
    assert exc_info.value.status_code == 400


@respx.mock
def test_a_rejection_without_a_readable_error_code_is_not_bad_credentials():
    """A 401 from a proxy or gateway carries no OAuth error code; do not blame the password."""
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(401, text="<html>denied</html>"))

    with pytest.raises(ERClientException) as exc_info:
        authenticate_with_password(DAS_ISSUER, **CREDENTIALS)

    assert not isinstance(exc_info.value, ERClientBadCredentials)


@respx.mock
@pytest.mark.parametrize("status_code", [403, 500, 503])
def test_other_failures_are_not_reported_as_bad_credentials(status_code):
    """Telling someone their password is wrong when the server is down wastes their time."""
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(status_code, json={}))

    with pytest.raises(ERClientException) as exc_info:
        authenticate_with_password(DAS_ISSUER, **CREDENTIALS)

    assert not isinstance(exc_info.value, ERClientBadCredentials)
    assert exc_info.value.status_code == status_code


@respx.mock
def test_unreachable_token_endpoint_is_service_unreachable():
    respx.post(TOKEN_URL).mock(
        side_effect=httpx.ConnectError("no route to host"))

    with pytest.raises(ERClientServiceUnreachable):
        authenticate_with_password(DAS_ISSUER, **CREDENTIALS)


@respx.mock
def test_success_without_an_access_token_is_an_error():
    """A 200 carrying no token is a broken server, not a login we can use."""
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"token_type": "Bearer"}))

    with pytest.raises(ERClientException):
        authenticate_with_password(DAS_ISSUER, **CREDENTIALS)


@respx.mock
def test_non_json_success_is_an_error():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, text="<html>gateway</html>"))

    with pytest.raises(ERClientException):
        authenticate_with_password(DAS_ISSUER, **CREDENTIALS)
