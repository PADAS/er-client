"""Shared fixtures for the auth characterization tests.

These tests pin down what ``ERClient`` and ``AsyncERClient`` do *today* at
construction time and on their lazy login paths. They are the safety net for
upcoming changes to the auth code, so they deliberately assert current
behavior — warts included.

A test that locks in a wart carries a ``# wart:`` comment, so the change that
fixes it flips the assertion on purpose rather than discovering it as a
surprise failure.
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
import requests

from erclient.client import AsyncERClient
from erclient.discovery import DISCOVERY_PATH
from erclient.er_errors import ERClientAuthWarning

# The client subtracts a fixed 5-minute safety margin from the token's
# expires_in before recording auth_expires.
EXPIRY_SKEW_SECONDS = 5 * 60

AUTH0_ISSUER = "https://fake-tenant.us.auth0.com"
# A JWT-shaped token: header is real base64url, the rest is plainly fake.
JWT_TOKEN = ("eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9"
             ".DUMMY-PAYLOAD.DUMMY-SIGNATURE")


def auth_warnings(recorded):
    """Only this client's auth warnings, ignoring anything else the run emits."""
    return [w for w in recorded if issubclass(w.category, ERClientAuthWarning)]


@pytest.fixture(autouse=True)
def discovery_not_served():
    """Default every test here to a site that serves no discovery document.

    That is what these tests assumed before discovery existed, so it keeps
    their meaning intact — and it keeps the suite off the network, since the
    sync fetch goes through the module-level ``requests.get``. Tests about
    discovery patch the same target themselves, which takes precedence.
    """
    with patch("erclient.client.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            spec=requests.Response, ok=False, status_code=404, text="")
        yield mock_get


@pytest.fixture
def service_root():
    return "https://fake-site.erdomain.org"


@pytest.fixture
def default_token_url(service_root):
    """Where the client posts when token_url is not supplied."""
    return f"{service_root}/oauth2/token"


@pytest.fixture
def custom_token_url():
    return "https://fake-auth.erdomain.org/oauth2/token"


@pytest.fixture
def ropc_kwargs(service_root):
    """Kwargs that select the resource-owner-password-credentials flow."""
    return {
        "service_root": service_root,
        "username": "test-user",
        "password": "test-password",
        "client_id": "das_web_client",
    }


@pytest.fixture
def token_kwargs(service_root):
    """Kwargs that select the pre-acquired-token flow."""
    return {
        "service_root": service_root,
        "token": "not-a-real-token",
    }


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


@pytest.fixture
def external_only_document(make_discovery_document):
    """A document a fully migrated site would serve: Auth0 and nothing else."""
    return make_discovery_document(AUTH0_ISSUER)


@pytest.fixture
def password_mismatch_message(service_root):
    """What the client says when a password grant cannot work at this site.

    Spelled out in full because the mismatch tests assert the message a caller
    sees verbatim, where the discovery tests only match warnings on a fragment.
    """
    return (
        f"Site {service_root} accepts only Auth0-issued tokens, so "
        "username/password login against its legacy token endpoint cannot "
        "work: the token endpoint may still issue a token, but every API "
        "request would be rejected. Pass an Auth0-issued access token with "
        "token= instead."
    )


@pytest.fixture
def patched_get():
    """Patch the module-level requests.get the discovery fetch uses."""
    with patch("erclient.client.requests.get") as mock_get:
        yield mock_get


@pytest.fixture
def patched_post(token_response, make_requests_response):
    """Patch the token endpoint so logins succeed."""
    with patch("erclient.client.requests.post") as mock_post:
        mock_post.return_value = make_requests_response(
            200, json_data=token_response)
        yield mock_post


@pytest.fixture
def serving(patched_get, make_requests_response):
    """Make the discovery endpoint serve a given document."""

    def _serve(document):
        patched_get.return_value = make_requests_response(
            200, json_data=document)

    return _serve


@pytest.fixture
def token_response_factory():
    """Build a token-endpoint success body, overriding or dropping fields."""

    def _factory(**overrides):
        payload = {
            "access_token": "access-token-1",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh-token-1",
            "scope": "read write",
        }
        payload.update(overrides)
        # Passing a field as None means "omit it from the response".
        return {k: v for k, v in payload.items() if v is not None}

    return _factory


@pytest.fixture
def token_response(token_response_factory):
    return token_response_factory()


@pytest.fixture
def assert_expiry_matches():
    """Assert auth_expires == now + expires_in - the client's 300s skew.

    Uses a tolerance rather than a frozen clock so the suite stays free of a
    freezegun dependency; the window is far tighter than the skew being
    asserted, so an off-by-one in the formula still fails.
    """

    def _assert(auth_expires, expires_in, tolerance_seconds=5):
        expected = datetime.now(timezone.utc) + timedelta(
            seconds=int(expires_in) - EXPIRY_SKEW_SECONDS
        )
        drift = abs((auth_expires - expected).total_seconds())
        assert drift < tolerance_seconds, (
            f"auth_expires drifted {drift}s from the expected "
            f"now + {expires_in} - {EXPIRY_SKEW_SECONDS}"
        )

    return _assert


@pytest.fixture
def make_requests_response():
    """Build a mock ``requests.Response`` shaped like the sync client expects."""

    def _factory(status_code, json_data=None, text=None):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status_code
        resp.ok = 200 <= status_code < 300
        if json_data is not None:
            resp.text = json.dumps(json_data)
            resp.json.return_value = json_data
        else:
            resp.text = text or ""
        return resp

    return _factory


@pytest_asyncio.fixture
async def async_client_factory():
    """Create AsyncERClients and close their sessions at teardown."""
    created = []

    def _factory(**kwargs):
        client = AsyncERClient(**kwargs)
        created.append(client)
        return client

    yield _factory

    for client in created:
        if not client._http_session.is_closed:
            await client.close()
