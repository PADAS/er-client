"""Fixtures for the auth tests: one client adapter and one fake server, both
covering the sync and the async client so a behavior is asserted once."""
import asyncio
import json
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qsl

import httpx
import pytest
import requests
import respx

from erclient.client import AsyncERClient, ERClient
from erclient.discovery import DISCOVERY_PATH

# Both clients, unless a module names fewer in its own CLIENT_KINDS.
CLIENT_KINDS = ("sync", "async")

# The margin both clients subtract from a token's expires_in.
EXPIRY_SKEW_SECONDS = 5 * 60


def pytest_generate_tests(metafunc):
    """Run every test that asks for a client against the kinds its module names."""
    if "client" in metafunc.fixturenames:
        kinds = getattr(metafunc.module, "CLIENT_KINDS", CLIENT_KINDS)
        metafunc.parametrize("client", kinds, indirect=True)


class Reply:
    """A canned response, in whichever HTTP library's shape the client reads."""

    def __init__(self, status_code=200, json_body=None, text=None, headers=None):
        self.status_code = status_code
        self.headers = dict(headers or {})
        self.json_body = json_body
        self.text = json.dumps(
            json_body) if json_body is not None else (text or "")

    def as_requests(self):
        response = MagicMock(spec=requests.Response)
        response.status_code = self.status_code
        response.ok = 200 <= self.status_code < 300
        response.headers = dict(self.headers)
        response.text = self.text
        response.json.return_value = self.json_body
        return response

    def as_httpx(self):
        return httpx.Response(self.status_code, content=self.text.encode(),
                              headers=self.headers)


Call = namedtuple("Call", "method url data headers timeout")


def _form(data):
    """A form payload as the wire carries it: requests drops None-valued fields."""
    if not data:
        return None
    return {key: value for key, value in data.items() if value is not None}


class _Route:
    def __init__(self, replies, repeating):
        self._replies = list(replies)
        self._repeating = repeating

    def next(self):
        if self._repeating:
            return self._replies[0]
        if not self._replies:
            raise AssertionError("the client asked more often than scripted")
        return self._replies.pop(0)


class FakeServer:
    """The site and its authorization server, answering by method and URL.

    Routing by URL rather than by call order means an assertion about what was
    requested cannot pass by accident when the client asks in the wrong order:
    ``traffic`` records that separately.
    """

    def __init__(self):
        self._routes = {}
        self.traffic = []

    def respond(self, method, url, status_code=200, json_body=None, text=None,
                headers=None):
        """Answer every such request with this response."""
        self.always(method, url, Reply(status_code, json_body, text, headers))

    def always(self, method, url, reply):
        """Answer every such request with a reply the caller prepared."""
        self._routes[(method, url)] = _Route([reply], repeating=True)

    def script(self, method, url, *replies):
        """Answer such requests with these responses in turn, then fail."""
        self._routes[(method, url)] = _Route(replies, repeating=False)

    def fail(self, method, url, error):
        """Answer every such request by raising, as an unreachable host does."""
        self._routes[(method, url)] = _Route([error], repeating=True)

    @property
    def calls(self):
        return [(call.method, call.url) for call in self.traffic]

    @property
    def posts(self):
        """Every POST, in order: the auth traffic without the discovery GETs."""
        return [call for call in self.traffic if call.method == "POST"]

    def reply_to(self, method, url, data=None, headers=None, timeout=None):
        # Lowercased, since httpx hands header names back that way and
        # requests hands back what the client passed.
        recorded = {key.lower(): value for key,
                    value in (headers or {}).items()}
        self.traffic.append(Call(method, url, data, recorded, timeout))
        route = self._routes.get((method, url))
        if route is None:
            raise AssertionError(f"unscripted {method} {url}")
        return route.next()


class _SyncBackend:
    """Serve the sync client, whose auth requests go through module-level requests."""

    def __init__(self, server):
        self._server = server
        self._patches = []

    def start(self):
        for method in ("get", "post"):
            patcher = patch(f"erclient.client.requests.{method}",
                            side_effect=self._handler(method.upper()))
            patcher.start()
            self._patches.append(patcher)

    def stop(self):
        for patcher in self._patches:
            patcher.stop()

    def _handler(self, method):
        def _request(url, **kwargs):
            reply = self._server.reply_to(
                method, url, _form(kwargs.get("data")),
                kwargs.get("headers"), kwargs.get("timeout"))
            if isinstance(reply, Exception):
                raise reply
            return reply.as_requests()

        return _request


class _AsyncBackend:
    """Serve the async client, whose auth requests go through its httpx session."""

    def __init__(self, server):
        self._server = server
        self._router = respx.mock(assert_all_called=False)

    def start(self):
        self._router.start()
        self._router.route().mock(side_effect=self._request)

    def stop(self):
        self._router.stop()

    def _request(self, request):
        data = _form(dict(parse_qsl(request.content.decode())))
        reply = self._server.reply_to(
            request.method, str(request.url), data,
            dict(request.headers), _timeout(request))
        if isinstance(reply, Exception):
            raise reply
        return reply.as_httpx()


def _timeout(request):
    """The deadline httpx recorded, as the one number the client asked for."""
    recorded = request.extensions.get("timeout") or {}
    values = set(recorded.values())
    return values.pop() if len(values) == 1 else recorded


class ClientUnderTest:
    """One client, driven the same way whichever of the two it is.

    Anything the adapter does not define is read off the client itself, so a
    test asserts on ``client.auth`` and ``client.token_url`` directly.
    """

    def __init__(self, kind, loop):
        self.kind = kind
        # What this client's HTTP library raises when the host is unreachable.
        self.transport_error = (requests.ConnectionError if kind == "sync"
                                else httpx.ConnectError)
        self._loop = loop
        self._client = None

    def make(self, **kwargs):
        factory = ERClient if self.kind == "sync" else AsyncERClient
        self._client = factory(**kwargs)
        return self

    def call(self, fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return self._loop.run_until_complete(result)
        return result

    def login(self):
        return self.call(self._client.login)

    def auth_headers(self):
        return self.call(self._client.auth_headers)

    def __getattr__(self, name):
        return getattr(self._client, name)


@pytest.fixture
def server():
    return FakeServer()


@pytest.fixture
def client(request, server):
    backend = (_SyncBackend(server) if request.param == "sync"
               else _AsyncBackend(server))
    backend.start()
    loop = asyncio.new_event_loop() if request.param == "async" else None

    adapter = ClientUnderTest(request.param, loop)
    yield adapter

    if loop is not None:
        if adapter._client is not None:
            loop.run_until_complete(adapter._client.close())
        loop.close()
    backend.stop()


@pytest.fixture(autouse=True)
def discovery_not_served(server, discovery_url):
    """Default every test here to a site that serves no discovery document.

    A password grant now discovers before it posts, and a 404 is the answer
    that leaves the grant exactly as it was. A test about discovery registers
    its own route over this one.
    """
    server.respond("GET", discovery_url, 404, text="")


@pytest.fixture
def tty(monkeypatch):
    """Pretend a user is watching, so an implicit login may prompt them."""
    monkeypatch.setattr("erclient.client._stdin_is_tty", lambda: True)


@pytest.fixture
def no_tty(monkeypatch):
    """Pretend nobody is watching: a cron job, a worker, a piped script."""
    monkeypatch.setattr("erclient.client._stdin_is_tty", lambda: False)


@pytest.fixture
def service_root():
    return "https://fake-site.erdomain.org"


@pytest.fixture
def default_token_url(service_root):
    """Where a client posts when token_url is not supplied."""
    return f"{service_root}/oauth2/token"


@pytest.fixture
def custom_token_url():
    return "https://fake-auth.erdomain.org/oauth2/token"


@pytest.fixture
def discovery_url(service_root):
    """Where the site serves its protected-resource metadata."""
    return f"{service_root}{DISCOVERY_PATH}"


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
        return {key: value for key, value in payload.items() if value is not None}

    return _factory


@pytest.fixture
def token_response(token_response_factory):
    return token_response_factory()


@pytest.fixture
def assert_expiry_matches():
    """Assert auth_expires == now + expires_in - the client's skew.

    A tolerance rather than a frozen clock, so the suite needs no freezegun;
    the window is far tighter than the skew being asserted.
    """

    def _assert(auth_expires, expires_in, tolerance_seconds=5):
        expected = datetime.now(timezone.utc) + timedelta(
            seconds=int(expires_in) - EXPIRY_SKEW_SECONDS)
        drift = abs((auth_expires - expected).total_seconds())
        assert drift < tolerance_seconds

    return _assert
