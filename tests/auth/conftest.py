"""Shared fixtures for the auth characterization tests.

These tests pin down what ``ERClient`` and ``AsyncERClient`` do *today* at
construction time and on their lazy login paths. They are the safety net for
upcoming changes to the auth code, so they deliberately assert current
behavior — warts included.

A test that locks in a wart carries a ``# wart:`` comment, so the change that
fixes it flips the assertion on purpose rather than discovering it as a
surprise failure.
"""
import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
import requests

from erclient.client import AsyncERClient
from erclient.device_code import KNOWN_AUTHORIZATION_SERVERS
from erclient.discovery import DISCOVERY_PATH, normalize_issuer
from erclient.er_errors import ERClientAuthWarning

# The client subtracts a fixed 5-minute safety margin from the token's
# expires_in before recording auth_expires.
EXPIRY_SKEW_SECONDS = 5 * 60

AUTH0_ISSUER = "https://fake-tenant.us.auth0.com"
# A JWT-shaped token: header is real base64url, the rest is plainly fake.
JWT_TOKEN = ("eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCJ9"
             ".DUMMY-PAYLOAD.DUMMY-SIGNATURE")


def jwt_with_issuer(issuer):
    """A JWT-shaped token whose payload really does carry this ``iss``.

    Header and payload are base64url with the padding stripped, as a real JWT
    has them; the signature stays fake, since nothing here verifies it.
    """
    def encode(value):
        return base64.urlsafe_b64encode(
            json.dumps(value).encode()).decode().rstrip("=")

    return ".".join([encode({"alg": "RS256", "typ": "JWT"}),
                     encode({"iss": issuer, "sub": "auth0|1"}),
                     "DUMMY-SIGNATURE"])


# The site's own Auth0 tenant, spelled with the trailing slash DAS puts on the
# issuer claim but not on the discovery document's entry — so the default JWT
# exercises the normalization rather than an exact string match.
JWT_WITH_ISSUER = jwt_with_issuer(f"{AUTH0_ISSUER}/")


def device_code_endpoint(issuer):
    """Where a tenant takes device-authorization requests, as it advertises it."""
    return f"{issuer.rstrip('/')}/oauth/device/code"


def device_token_endpoint(issuer):
    """Where a tenant takes token requests, as it advertises it."""
    return f"{issuer.rstrip('/')}/oauth/token"


# The device-code refusals, spelled out here so a test fails when the text a
# caller reads changes, not only when the exception class does.
DISCOVERY_DISABLED_MESSAGE = (
    "Interactive sign-in needs the site's discovery document to find its "
    "authorization server, but discovery=False was passed. Enable discovery, "
    "or pass device_code_issuer=."
)
INCOMPLETE_OVERRIDE_MESSAGE = (
    "The issuer passed with device_code_issuer= is not an EarthRanger Auth0 "
    "tenant this client knows, so device_code_client_id= and "
    "device_code_audience= are needed too."
)
CODE_EXPIRED_MESSAGE = (
    "The sign-in code expired before it was approved. Call client.login() "
    "again for a new one."
)
SIGN_IN_DECLINED_MESSAGE = (
    "The sign-in was declined at the authorization server. Call "
    "client.login() again to retry."
)


def no_terminal_message(service_root):
    """An implicit first login with nobody to read the prompt."""
    return (
        f"Site {service_root} needs an interactive sign-in and no terminal is "
        "attached. Call client.login() explicitly where you can see the "
        "prompt, or pass an Auth0-issued access token with token=."
    )


def expired_session_message(service_root):
    """The same, once a device-code token has run out."""
    return (
        f"Your EarthRanger session for {service_root} has expired and no "
        "terminal is attached to sign in again. Call client.login() "
        "explicitly, or pass a fresh Auth0-issued access token with token=."
    )


def no_authorization_servers_message(service_root):
    """The site publishes nothing to sign in against."""
    return (
        f"Site {service_root} does not publish its authorization servers, so "
        "the client cannot sign in interactively. Pass an Auth0-issued access "
        "token with token=, or pass device_code_issuer= if you know the site's "
        "Auth0 issuer."
    )


def no_known_tenant_message(service_root, accepted):
    """It publishes servers, but none this release knows."""
    return (
        f"Site {service_root} lists no EarthRanger Auth0 tenant this client "
        f"knows ({accepted}). Pass an Auth0-issued access token with token=, "
        "or pass device_code_issuer=, device_code_client_id= and "
        "device_code_audience= for its tenant."
    )


def metadata_unreadable_message(metadata_url):
    """The authorization server would not describe itself."""
    return (
        "Could not read the authorization server's metadata at "
        f"{metadata_url}. Try again, or pass an Auth0-issued access token "
        "with token=."
    )


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
        "token=, or construct the client with no credentials and call login() "
        "to sign in interactively."
    )


@pytest.fixture
def opaque_token_mismatch_message(service_root):
    """What the client says when a legacy token cannot work at this site."""
    return (
        "The token passed with token= looks like a legacy EarthRanger-issued "
        f"token, but site {service_root} accepts only Auth0-issued tokens. "
        "Use an Auth0-issued access token, or construct the client with no "
        "credentials and call login() to sign in interactively."
    )


@pytest.fixture
def unlisted_issuer_message(service_root):
    """What the client says about a JWT from an issuer the site does not name."""

    def _message(issuer, accepted):
        return (
            f"The token passed with token= was issued by {issuer}, which site "
            f"{service_root} does not accept. Accepted issuers: "
            f"{', '.join(accepted)}."
        )

    return _message


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


class FakeDeviceServer:
    """A site and an Auth0 tenant, answering the sync client by URL.

    The client reaches four endpoints on the device-code path, and a test that
    cares about one of them still has to get past the other three. Routing by
    URL rather than by call order also means the assertions about *what* was
    requested cannot pass by accident when the client asks in the wrong order:
    ``traffic`` records that separately.
    """

    def __init__(self, issuer, responses):
        self.issuer = issuer
        self._responses = responses
        self.token_responses = []
        self.traffic = []

    @property
    def device_endpoint(self):
        return device_code_endpoint(self.issuer)

    @property
    def token_endpoint(self):
        return device_token_endpoint(self.issuer)

    def get(self, url, **kwargs):
        self.traffic.append(("GET", url))
        if url.endswith(DISCOVERY_PATH):
            return self._responses["discovery"]
        if url.endswith("/.well-known/openid-configuration"):
            return self._responses["metadata"]
        raise AssertionError(f"unexpected GET {url}")

    def post(self, url, **kwargs):
        self.traffic.append(("POST", url))
        if url == self.device_endpoint:
            return self._responses["authorization"]
        if url == self.token_endpoint:
            assert self.token_responses, "the client polled more than scripted"
            return self.token_responses.pop(0)
        raise AssertionError(f"unexpected POST {url}")


@pytest.fixture
def fake_device_server(
    patched_get, patched_post, make_requests_response, known_issuer,
    dev_discovery_document, as_metadata_document, device_authorization_document,
    device_token_response,
):
    """Stand up a fake tenant behind the sync client's requests.get/post.

    Every piece is overridable, so a test that wants a broken metadata
    document or a scripted poll says only that much.
    """

    def _serve(*, discovery=None, metadata=None, authorization=None,
               token_responses=None, issuer=None):
        issuer = issuer or known_issuer
        server = FakeDeviceServer(issuer, {
            "discovery": discovery if discovery is not None
            else make_requests_response(200, json_data=dev_discovery_document),
            "metadata": metadata if metadata is not None
            else make_requests_response(
                200, json_data=as_metadata_document(issuer)),
            "authorization": authorization if authorization is not None
            else make_requests_response(
                200, json_data=device_authorization_document()),
        })
        server.token_responses = list(token_responses) if token_responses else [
            make_requests_response(200, json_data=device_token_response)]
        patched_get.side_effect = server.get
        patched_post.side_effect = server.post
        return server

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
def known_issuer():
    """An EarthRanger Auth0 tenant this client knows, spelled as discovery serves it."""
    return "https://auth-dev.pamdas.org/"


@pytest.fixture
def known_server(known_issuer):
    """The registration that goes with it."""
    return KNOWN_AUTHORIZATION_SERVERS[normalize_issuer(known_issuer)]


@pytest.fixture
def dev_discovery_document(make_discovery_document, das_issuer, known_issuer):
    """What a migrating site backed by that tenant serves."""
    return make_discovery_document(das_issuer, known_issuer)


@pytest.fixture
def as_metadata_document():
    """An OIDC discovery document for an authorization server."""

    def _factory(issuer, **overrides):
        document = {
            "issuer": issuer,
            "device_authorization_endpoint": device_code_endpoint(issuer),
            "token_endpoint": device_token_endpoint(issuer),
            "jwks_uri": f"{issuer.rstrip('/')}/.well-known/jwks.json",
        }
        document.update(overrides)
        return {k: v for k, v in document.items() if v is not None}

    return _factory


@pytest.fixture
def device_authorization_document():
    """A device-authorization response, with a fast interval for the tests."""

    def _factory(**overrides):
        document = {
            "device_code": "device-code-1",
            "user_code": "WDJB-MJHT",
            "verification_uri": "https://auth-dev.pamdas.org/activate",
            "verification_uri_complete": (
                "https://auth-dev.pamdas.org/activate?user_code=WDJB-MJHT"),
            "expires_in": 60,
            "interval": 1,
        }
        document.update(overrides)
        return {k: v for k, v in document.items() if v is not None}

    return _factory


@pytest.fixture
def device_token_response():
    """What the token endpoint returns once the user approves.

    No ``refresh_token``: the registration does not ask for ``offline_access``,
    so expiry sends the client back through the whole flow.
    """
    return {
        "access_token": JWT_WITH_ISSUER,
        "token_type": "Bearer",
        "expires_in": 172800,
        "scope": "openid profile email",
    }


@pytest.fixture
def tty(monkeypatch):
    """Pretend a user is watching, so an implicit login may prompt them."""
    monkeypatch.setattr("erclient.client._stdin_is_tty", lambda: True)


@pytest.fixture
def no_tty(monkeypatch):
    """Pretend nobody is watching: a cron job, a worker, a piped script."""
    monkeypatch.setattr("erclient.client._stdin_is_tty", lambda: False)


@pytest.fixture
def no_sleep(monkeypatch):
    """Record what the poller would have waited for, without waiting."""
    slept = []
    monkeypatch.setattr("erclient.client.time.sleep", slept.append)
    return slept


@pytest.fixture
def no_async_sleep(monkeypatch):
    """The async poller's waits, recorded rather than served."""
    slept = []

    async def _sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr("erclient.client.asyncio.sleep", _sleep)
    return slept


@pytest.fixture
def captured_prompt():
    """A device_code_prompt callable that keeps what it was told to show."""
    return []


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

    def _factory(status_code, json_data=None, text=None, headers=None):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status_code
        resp.ok = 200 <= status_code < 300
        # A real dict, not a mock: the client reads Retry-After off it.
        resp.headers = dict(headers or {})
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
