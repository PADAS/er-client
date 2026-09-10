"""Signing a user in with no credentials in hand: RFC 8628 device
authorization, end to end against a fake site and a fake Auth0 tenant."""
import base64
import json
import logging

import pytest
from tests.auth.conftest import Reply

from erclient.device_code import KNOWN_AUTHORIZATION_SERVERS
from erclient.er_errors import (ERClientBadCredentials, ERClientBadRequest,
                                ERClientException, ERClientRateLimitExceeded,
                                ERClientServiceUnreachable)

CLIENT_KINDS = ("sync",)

ISSUER = "https://auth-dev.pamdas.org"
TENANT = KNOWN_AUTHORIZATION_SERVERS[ISSUER]
METADATA_URL = f"{ISSUER}/.well-known/openid-configuration"
DEVICE_ENDPOINT = f"{ISSUER}/oauth/device/code"
TOKEN_ENDPOINT = f"{ISSUER}/oauth/token"
USER_CODE = "WDJB-MJHT"
VERIFICATION_URI = f"{ISSUER}/activate"
VERIFICATION_URI_COMPLETE = f"{VERIFICATION_URI}?user_code={USER_CODE}"


def jwt_for(issuer):
    """A JWT-shaped token whose payload really does carry this iss."""
    def encode(value):
        return base64.urlsafe_b64encode(
            json.dumps(value).encode()).decode().rstrip("=")

    return ".".join([encode({"alg": "RS256", "typ": "JWT"}),
                     encode({"iss": issuer, "sub": "auth0|1"}),
                     "DUMMY-SIGNATURE"])


def without_nones(document):
    return {key: value for key, value in document.items() if value is not None}


def as_metadata(issuer=ISSUER, **overrides):
    return without_nones({
        "issuer": issuer,
        "device_authorization_endpoint": DEVICE_ENDPOINT,
        "token_endpoint": TOKEN_ENDPOINT,
        **overrides})


def device_authorization(**overrides):
    return without_nones({
        "device_code": "device-code-1",
        "user_code": USER_CODE,
        "verification_uri": VERIFICATION_URI,
        "verification_uri_complete": VERIFICATION_URI_COMPLETE,
        "expires_in": 900,
        "interval": 5,
        **overrides})


def token_body(issuer=ISSUER, **overrides):
    return without_nones({
        "access_token": jwt_for(issuer),
        "token_type": "Bearer",
        "expires_in": 172800,
        "scope": "openid profile email",
        **overrides})


def pending(**overrides):
    return Reply(400, json_body={"error": "authorization_pending", **overrides})


@pytest.fixture
def site_document(service_root):
    """What a site backed by the dev tenant publishes."""
    return {"resource": service_root,
            "authorization_servers": [f"{service_root}/oauth2", ISSUER]}


@pytest.fixture
def flow(server, discovery_url, site_document):
    """Stand up the site and its tenant. Every piece is overridable."""

    def _serve(*, discovery=None, metadata=None, authorization=None,
               token_replies=None):
        server.always("GET", discovery_url,
                      discovery or Reply(json_body=site_document))
        server.always("GET", METADATA_URL,
                      metadata or Reply(json_body=as_metadata()))
        server.always("POST", DEVICE_ENDPOINT,
                      authorization or Reply(json_body=device_authorization()))
        server.script("POST", TOKEN_ENDPOINT,
                      *(token_replies or [Reply(json_body=token_body())]))

    return _serve


@pytest.fixture
def clock(monkeypatch):
    """A monotonic clock the poller's own waits advance, so nothing sleeps."""
    now = [1000.0]
    slept = []

    def _sleep(seconds):
        slept.append(seconds)
        now[0] += seconds

    monkeypatch.setattr("erclient.client.time.monotonic", lambda: now[0])
    monkeypatch.setattr("erclient.client.time.sleep", _sleep)
    return slept


class TestWhichFlowIsSelected:

    @pytest.mark.parametrize("kwargs,expected", [
        ({}, True),
        ({"token": "a-token"}, False),
        ({"token": ""}, True),
        ({"username": "u", "password": "p", "client_id": "c"}, False),
        ({"username": "u"}, False),
        ({"client_id": "c"}, False),
        ({"token": "", "username": "u"}, False),
    ])
    def test_only_a_client_with_nothing_at_all_signs_the_user_in(
            self, client, service_root, kwargs, expected):
        client.make(service_root=service_root, **kwargs)

        assert client._uses_device_code() is expected

    def test_a_lone_client_id_still_posts_a_password_grant(
            self, client, server, service_root, default_token_url,
            token_response):
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(service_root=service_root, client_id="das_web_client")

        assert client.login() is True
        assert server.traffic[0].data["grant_type"] == "password"


class TestTheHappyPath:

    def test_returns_true_and_holds_the_token(self, client, service_root, flow,
                                              clock, assert_expiry_matches):
        flow()
        client.make(service_root=service_root)

        assert client.login() is True
        assert client.auth["access_token"] == jwt_for(ISSUER)
        assert client.auth_headers(
        )["Authorization"] == f"Bearer {jwt_for(ISSUER)}"
        assert_expiry_matches(client.auth_expires, 172800)

    def test_a_short_lived_token_keeps_half_its_life(self, client,
                                                     service_root, flow, clock):
        flow(token_replies=[Reply(json_body=token_body(expires_in=300))])
        client.make(service_root=service_root)

        client.login()

        # Not the flat five-minute margin, which would record a 300s token as
        # already expired and start another sign-in on the next request.
        assert client._auth_is_valid() is True

    def test_a_refresh_token_the_tenant_sent_anyway_is_dropped(
            self, client, service_root, flow, clock):
        flow(token_replies=[
            Reply(json_body=token_body(refresh_token="refresh-token-1"))])
        client.make(service_root=service_root)

        client.login()

        assert "refresh_token" not in client.auth

    def test_the_order_of_the_conversation(self, client, server, service_root,
                                           discovery_url, flow, clock):
        flow()
        client.make(service_root=service_root)

        client.login()

        assert server.calls == [
            ("GET", discovery_url),
            ("GET", METADATA_URL),
            ("POST", DEVICE_ENDPOINT),
            ("POST", TOKEN_ENDPOINT),
        ]

    def test_nothing_is_sent_to_the_sites_own_token_endpoint(
            self, client, server, service_root, default_token_url, flow, clock):
        flow()
        client.make(service_root=service_root)

        client.login()

        assert default_token_url not in [url for _, url in server.calls]

    def test_the_flow_runs_on_its_own_deadlines(self, client, server,
                                                service_root, flow, clock):
        flow()
        client.make(service_root=service_root)

        client.login()

        deadlines = {call.url: call.timeout for call in server.traffic}
        assert deadlines[METADATA_URL] == 5
        assert deadlines[DEVICE_ENDPOINT] == 10
        assert deadlines[TOKEN_ENDPOINT] == 10


class TestWhatIsAskedOfTheTenant:

    def test_the_device_authorization_request(self, client, server,
                                              service_root, flow, clock):
        flow()
        client.make(service_root=service_root)

        client.login()

        assert server.traffic[2].data == {
            "client_id": TENANT.client_id,
            "scope": "openid profile email",
            "audience": TENANT.audience,
        }

    def test_the_token_request(self, client, server, service_root, flow, clock):
        flow()
        client.make(service_root=service_root)

        client.login()

        assert server.traffic[3].data == {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": "device-code-1",
            "client_id": TENANT.client_id,
        }

    def test_the_metadata_request_identifies_the_client(
            self, client, server, service_root, flow, clock):
        flow()
        client.make(service_root=service_root)

        client.login()

        assert server.traffic[1].headers["User-Agent"] == client.user_agent

    def test_the_prod_tenant_gets_its_own_registration(
            self, client, server, service_root, discovery_url, flow, clock):
        prod = KNOWN_AUTHORIZATION_SERVERS["https://auth.pamdas.org"]
        server.always("GET", discovery_url, Reply(json_body={
            "resource": service_root,
            "authorization_servers": [prod.issuer]}))
        server.always("GET", f"{prod.issuer}/.well-known/openid-configuration",
                      Reply(json_body={
                          "issuer": prod.issuer,
                          "device_authorization_endpoint":
                              f"{prod.issuer}/oauth/device/code",
                          "token_endpoint": f"{prod.issuer}/oauth/token"}))
        server.always("POST", f"{prod.issuer}/oauth/device/code",
                      Reply(json_body=device_authorization(
                          verification_uri=f"{prod.issuer}/activate",
                          verification_uri_complete=None)))
        server.script("POST", f"{prod.issuer}/oauth/token",
                      Reply(json_body=token_body(issuer=prod.issuer)))
        client.make(service_root=service_root)

        client.login()

        assert server.traffic[2].data["client_id"] == prod.client_id
        assert server.traffic[2].data["audience"] == prod.audience


class TestPolling:

    def test_pending_answers_are_not_failures(self, client, service_root, flow,
                                              clock):
        flow(token_replies=[pending(), pending(),
                            Reply(json_body=token_body())])
        client.make(service_root=service_root)

        assert client.login() is True
        assert clock == [5, 5, 5]

    def test_slow_down_adds_five_seconds_for_good(self, client, service_root,
                                                  flow, clock):
        flow(token_replies=[Reply(400, json_body={"error": "slow_down"}),
                            pending(),
                            Reply(json_body=token_body())])
        client.make(service_root=service_root)

        client.login()

        assert clock == [5, 10, 10]

    def test_a_retry_after_on_a_slow_down_wins_when_it_is_longer(
            self, client, service_root, flow, clock):
        flow(token_replies=[
            Reply(400, json_body={"error": "slow_down"},
                  headers={"Retry-After": "30"}),
            Reply(json_body=token_body())])
        client.make(service_root=service_root)

        client.login()

        assert clock == [5, 30]

    def test_the_code_expiring_at_the_server(self, client, service_root, flow,
                                             clock):
        flow(token_replies=[Reply(400, json_body={"error": "expired_token"})])
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert "expired" in str(exc_info.value)
        assert client.auth is None

    def test_the_code_expiring_on_our_own_clock(self, client, service_root,
                                                flow, clock):
        flow(authorization=Reply(json_body=device_authorization(expires_in=12)),
             token_replies=[pending(), pending(), pending()])
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert "expired" in str(exc_info.value)

    def test_no_wait_outlasts_the_code(self, client, service_root, flow, clock):
        flow(authorization=Reply(json_body=device_authorization(
            expires_in=7, interval=60)),
            token_replies=[pending()])
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials):
            client.login()

        assert clock == [7]

    def test_the_user_saying_no(self, client, service_root, flow, clock):
        flow(token_replies=[Reply(403, json_body={"error": "access_denied"})])
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert "declined" in str(exc_info.value)
        assert client.auth is None

    def test_any_other_refusal_is_classified_like_a_token_refusal(
            self, client, service_root, flow, clock):
        flow(token_replies=[Reply(429, text="slow down please",
                                  headers={"Retry-After": "9"})])
        client.make(service_root=service_root)

        with pytest.raises(ERClientRateLimitExceeded) as exc_info:
            client.login()

        assert exc_info.value.retry_after == 9


class TestTheTenantWillNotStartTheFlow:

    def test_a_refusal_is_classified_like_any_token_refusal(
            self, client, service_root, flow, clock):
        flow(authorization=Reply(400, json_body={"error": "invalid_request"}))
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadRequest):
            client.login()

    def test_a_response_we_cannot_poll_on(self, client, service_root, flow,
                                          clock):
        flow(authorization=Reply(json_body=device_authorization(
            user_code=None)))
        client.make(service_root=service_root)

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert DEVICE_ENDPOINT in str(exc_info.value)
        # The body may still hold a usable device_code, and this is printed.
        assert exc_info.value.response_body is None


class TestTheApprovalCannotBeUsed:

    def test_a_token_response_the_client_cannot_read(self, client,
                                                     service_root, flow, clock):
        flow(token_replies=[Reply(json_body=token_body(expires_in=None))])
        client.make(service_root=service_root)

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert TOKEN_ENDPOINT in str(exc_info.value)
        assert client.auth is None

    def test_a_token_minted_for_another_issuer_is_refused(
            self, client, service_root, flow, clock):
        canonical = "https://er-dev.us.auth0.com"
        flow(token_replies=[Reply(json_body=token_body(issuer=canonical))])
        client.make(service_root=service_root)

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert canonical in str(exc_info.value)
        assert ISSUER in str(exc_info.value)
        assert client.auth is None

    def test_an_opaque_token_is_kept_since_it_has_no_issuer_to_read(
            self, client, service_root, flow, clock):
        flow(token_replies=[
            Reply(json_body=token_body(access_token="opaque-token"))])
        client.make(service_root=service_root)

        assert client.login() is True
        assert client.auth["access_token"] == "opaque-token"


class TestTheAuthorizationServerWillNotDescribeItself:

    def test_a_transport_error(self, client, server, service_root, flow, clock):
        flow()
        server.fail("GET", METADATA_URL,
                    client.transport_error("no route to host"))
        client.make(service_root=service_root)

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert METADATA_URL in str(exc_info.value)

    @pytest.mark.parametrize("metadata", [
        Reply(500, text="oops"),
        Reply(302, text="", headers={"Location": "https://elsewhere.example"}),
        Reply(json_body=as_metadata(issuer="https://er-dev.us.auth0.com")),
        Reply(json_body=as_metadata(token_endpoint=None)),
        Reply(text="not json"),
    ])
    def test_a_document_we_could_not_act_on(self, client, service_root, flow,
                                            clock, metadata):
        flow(metadata=metadata)
        client.make(service_root=service_root)

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert METADATA_URL in str(exc_info.value)


class TestThereIsNoTenantToSignInAgainst:

    def test_discovery_turned_off(self, client, server, service_root, flow):
        flow()
        client.make(service_root=service_root, discovery=False)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert "discovery=False" in str(exc_info.value)
        assert server.traffic == []

    @pytest.mark.parametrize("discovery", [
        Reply(404, text=""),
        Reply(text="not json"),
    ])
    def test_a_site_that_publishes_no_document(self, client, service_root,
                                               flow, discovery):
        flow(discovery=discovery)
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert "does not publish its authorization servers" in str(
            exc_info.value)

    def test_a_site_that_publishes_an_empty_list(self, client, service_root,
                                                 flow):
        flow(discovery=Reply(json_body={"resource": service_root,
                                        "authorization_servers": []}))
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert "does not publish its authorization servers" in str(
            exc_info.value)

    @pytest.mark.parametrize("listed", [
        ["https://fake-site.erdomain.org/oauth2"],
        ["https://auth.example.com"],
    ])
    def test_a_site_naming_no_tenant_this_release_knows(
            self, client, service_root, flow, listed):
        flow(discovery=Reply(json_body={"resource": service_root,
                                        "authorization_servers": listed}))
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert "lists no EarthRanger Auth0 tenant this client knows" in str(
            exc_info.value)
        assert listed[0] in str(exc_info.value)

    def test_a_refusal_leaves_nothing_behind(self, client, service_root, flow):
        flow(discovery=Reply(404, text=""))
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials):
            client.login()

        assert client.auth is None
        assert client._last_auth_error.error == "interactive_sign_in_unavailable"


class TestThePrompt:

    def test_names_the_site_the_url_and_the_code(self, client, service_root,
                                                 flow, clock, capsys):
        flow()
        client.make(service_root=service_root)

        client.login()

        printed = capsys.readouterr().err
        assert service_root in printed
        assert VERIFICATION_URI_COMPLETE in printed
        assert USER_CODE in printed

    def test_is_shown_exactly_once_however_long_the_polling_takes(
            self, client, service_root, flow, clock, capsys):
        flow(token_replies=[pending(), pending(),
                            Reply(json_body=token_body())])
        client.make(service_root=service_root)

        client.login()

        assert capsys.readouterr().err.count("Waiting for approval") == 1

    def test_the_log_gets_a_summary_without_the_code_in_it(
            self, client, service_root, flow, clock, caplog):
        flow()
        client.make(service_root=service_root)

        with caplog.at_level(logging.INFO):
            client.login()

        assert VERIFICATION_URI in caplog.text
        assert USER_CODE not in caplog.text

    def test_the_browser_stays_shut_by_default(self, client, service_root,
                                               flow, clock, monkeypatch):
        opened = []
        monkeypatch.setattr("erclient.client.webbrowser.open", opened.append)
        flow()
        client.make(service_root=service_root)

        client.login()

        assert opened == []

    def test_opening_the_browser_when_asked(self, client, service_root, flow,
                                            clock, monkeypatch):
        opened = []
        monkeypatch.setattr("erclient.client.webbrowser.open", opened.append)
        flow()
        client.make(service_root=service_root, open_browser=True)

        client.login()

        assert opened == [VERIFICATION_URI_COMPLETE]

    def test_a_browser_that_will_not_open_is_not_a_failure(
            self, client, service_root, flow, clock, monkeypatch, capsys):
        def _explode(url):
            raise OSError("no display")

        monkeypatch.setattr("erclient.client.webbrowser.open", _explode)
        flow()
        client.make(service_root=service_root, open_browser=True)

        assert client.login() is True
        assert USER_CODE in capsys.readouterr().err


class TestAnImplicitSignIn:

    def test_with_a_terminal_the_flow_just_runs(self, client, service_root,
                                                flow, clock, tty):
        flow()
        client.make(service_root=service_root)

        headers = client.auth_headers()

        assert headers["Authorization"] == f"Bearer {jwt_for(ISSUER)}"

    def test_without_a_terminal_nothing_is_attempted(self, client, server,
                                                     service_root, flow,
                                                     no_tty):
        flow()
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert "no terminal is attached" in str(exc_info.value)
        assert server.traffic == []

    def test_an_explicit_login_proceeds_without_a_terminal(
            self, client, service_root, flow, clock, no_tty):
        flow()
        client.make(service_root=service_root)

        assert client.login() is True


class TestAnExpiredSession:

    def test_a_terminal_gets_the_whole_flow_again(self, client, server,
                                                  service_root, flow, clock,
                                                  tty):
        flow(token_replies=[Reply(json_body=token_body()),
                            Reply(json_body=token_body(
                                access_token="second-token"))])
        client.make(service_root=service_root)
        client.login()
        client._client.auth_expires = client.auth_expires.replace(year=2000)

        headers = client.auth_headers()

        assert headers["Authorization"] == "Bearer second-token"
        assert server.calls.count(("GET", METADATA_URL)) == 2

    def test_nothing_is_refreshed_and_no_password_is_posted(
            self, client, server, service_root, default_token_url, flow, clock,
            tty):
        flow(token_replies=[Reply(json_body=token_body()),
                            Reply(json_body=token_body())])
        client.make(service_root=service_root)
        client.login()
        client._client.auth_expires = client.auth_expires.replace(year=2000)

        client.auth_headers()

        assert default_token_url not in [url for _, url in server.calls]
        assert all(call.data.get("grant_type") != "refresh_token"
                   for call in server.traffic if call.data)

    def test_without_a_terminal_the_expired_session_is_reported(
            self, client, service_root, flow, clock, tty, no_tty):
        flow()
        client.make(service_root=service_root)
        client._client.auth = {"token_type": "Bearer", "access_token": "old"}
        client._client.auth_expires = client.auth_expires.replace(year=2000)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert "has expired" in str(exc_info.value)


class TestTheRefusalsAreClassified:

    @pytest.mark.parametrize("token_reply,expected", [
        (Reply(400, json_body={"error": "expired_token"}),
         ERClientBadCredentials),
        (Reply(400, json_body={"error": "access_denied"}),
         ERClientBadCredentials),
        (Reply(400, json_body={"error": "invalid_client"}),
         ERClientBadCredentials),
        (Reply(400, json_body={"error": "invalid_request"}),
         ERClientBadRequest),
        (Reply(418, text="teapot"), ERClientException),
    ])
    def test_by_the_oauth_error_in_the_body(self, client, service_root, flow,
                                            clock, token_reply, expected):
        flow(token_replies=[token_reply])
        client.make(service_root=service_root)

        with pytest.raises(expected):
            client.login()
