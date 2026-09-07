"""ERClient signs a user in interactively when it was given no credentials.

``ERClient(service_root=...)`` and nothing else used to be a client that could
only fail: the first request posted a password grant of ``None``s. It now runs
RFC 8628 device authorization against the EarthRanger Auth0 tenant the site
names, shows the user a URL and a code, and polls until they approve.

Two rules shape most of what is asserted here. The flow runs against the custom
domain the site advertises and nowhere else, because EarthRanger validates a
token's ``iss`` against exactly that string. And a token from this flow carries
no refresh token, so expiry means signing in again — which needs a terminal,
and says so when there isn't one.
"""
import json
import logging
from datetime import datetime
from unittest.mock import patch

import pytest
import pytz
import requests
from tests.auth.conftest import (CODE_EXPIRED_MESSAGE,
                                 DISCOVERY_DISABLED_MESSAGE,
                                 INCOMPLETE_OVERRIDE_MESSAGE,
                                 SIGN_IN_DECLINED_MESSAGE,
                                 device_authorization_unreadable_message,
                                 device_code_endpoint, device_token_endpoint,
                                 expired_session_message,
                                 metadata_unreadable_message,
                                 no_authorization_servers_message,
                                 no_known_tenant_message, no_terminal_message)

from erclient.client import ERClient
from erclient.device_code import (DEFAULT_SCOPE, DEVICE_CODE_GRANT,
                                  KNOWN_AUTHORIZATION_SERVERS)
from erclient.er_errors import (INTERACTIVE_SIGN_IN_UNAVAILABLE,
                                ERClientBadCredentials, ERClientBadRequest,
                                ERClientServiceUnreachable)

PROD_ISSUER = "https://auth.pamdas.org/"
OTHER_ISSUER = "https://someone-elses-tenant.us.auth0.com/"


def urls(traffic, method=None):
    """The URLs from a fake server's traffic log, optionally by method."""
    return [url for verb, url in traffic if method in (None, verb)]


class TestWhichFlowIsSelected:
    """One rule: no credentials of any kind means sign the user in."""

    @pytest.mark.parametrize(
        "kwargs, expected",
        [
            ({}, True),
            ({"token": ""}, True),
            ({"token": None}, True),
            ({"token": "a-token"}, False),
            ({"username": "u"}, False),
            ({"password": "p"}, False),
            ({"client_id": "das_web_client"}, False),
            ({"username": "u", "password": "p",
              "client_id": "das_web_client"}, False),
            ({"token": "", "username": "u"}, False),
        ],
        ids=["nothing", "empty_token", "explicit_none", "token", "username",
             "password", "client_id", "full_ropc", "empty_token_with_username"],
    )
    def test_the_truth_table(self, service_root, kwargs, expected):
        """Any legacy kwarg at all keeps the password grant, even incomplete."""
        client = ERClient(service_root=service_root, **kwargs)

        assert client._uses_device_code() is expected

    def test_a_lone_client_id_still_posts_a_password_grant(
        self, service_root, default_token_url, patched_post,
        make_requests_response, token_response,
    ):
        """The legacy path is unchanged, however little of it was filled in."""
        client = ERClient(service_root=service_root,
                          client_id="das_web_client")
        patched_post.return_value = make_requests_response(
            200, json_data=token_response)

        assert client.login() is True
        assert patched_post.call_args.args[0] == default_token_url
        assert patched_post.call_args.kwargs["data"]["grant_type"] == "password"


class TestTheHappyPath:
    """An explicit login() against a site that names a tenant we know."""

    def test_returns_true_and_holds_the_token(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        device_token_response, assert_expiry_matches,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        assert client.login() is True
        assert client.auth == device_token_response
        assert_expiry_matches(client.auth_expires,
                              device_token_response["expires_in"])
        assert client.last_auth_error is None

    def test_the_order_of_the_conversation(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        known_issuer, discovery_url, device_token_response,
        make_requests_response,
    ):
        """Ask the site, ask the tenant, start the flow, then poll."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server(token_responses=[
            make_requests_response(
                400, json_data={"error": "authorization_pending"}),
            make_requests_response(200, json_data=device_token_response),
        ])

        client.login()

        assert server.traffic == [
            ("GET", discovery_url),
            ("GET", "https://auth-dev.pamdas.org/.well-known/openid-configuration"),
            ("POST", device_code_endpoint(known_issuer)),
            ("POST", device_token_endpoint(known_issuer)),
            ("POST", device_token_endpoint(known_issuer)),
        ]

    def test_nothing_is_sent_to_the_sites_own_token_endpoint(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        default_token_url,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server()

        client.login()

        assert default_token_url not in urls(server.traffic)

    def test_everything_goes_to_the_custom_domain(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
    ):
        """A token minted at a canonical auth0.com name is one EarthRanger rejects."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server()

        client.login()

        tenant_urls = [url for url in urls(server.traffic)
                       if not url.startswith(service_root)]
        assert tenant_urls
        assert all(url.startswith("https://auth-dev.pamdas.org/")
                   for url in tenant_urls)

    def test_the_user_is_told_where_to_go_and_what_to_confirm(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        client.login()

        assert captured_prompt == [
            "You are about to authorize the EarthRanger Python Client to "
            f"access {service_root} as your user.\n"
            "Open https://auth-dev.pamdas.org/activate?user_code=WDJB-MJHT in "
            "a browser and confirm that it shows the code WDJB-MJHT.\n"
            "Waiting for approval..."
        ]

    def test_the_prompt_comes_before_the_first_poll(
        self, service_root, fake_device_server, no_sleep, known_issuer,
    ):
        """Nobody can approve a code they have not been shown."""
        server = fake_device_server()
        traffic_when_prompted = []
        client = ERClient(
            service_root=service_root,
            device_code_prompt=lambda text: traffic_when_prompted.extend(
                urls(server.traffic, "POST")))

        client.login()

        assert traffic_when_prompted == [device_code_endpoint(known_issuer)]

    def test_it_waits_the_interval_the_server_asked_for(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        device_authorization_document, make_requests_response,
        device_token_response,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(
            authorization=make_requests_response(
                200, json_data=device_authorization_document(interval=3)),
            token_responses=[
                make_requests_response(
                    400, json_data={"error": "authorization_pending"}),
                make_requests_response(200, json_data=device_token_response),
            ])

        client.login()

        assert no_sleep == [3, 3]


class TestWhatIsAskedOfTheTenant:
    """The two POSTs, field by field."""

    def test_the_device_authorization_request(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        patched_post, known_server,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        client.login()

        device_call = patched_post.call_args_list[0]
        assert device_call.kwargs["data"] == {
            "client_id": known_server.client_id,
            "scope": DEFAULT_SCOPE,
            "audience": known_server.audience,
        }

    def test_the_token_request(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        patched_post, known_server,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        client.login()

        token_call = patched_post.call_args_list[-1]
        assert token_call.kwargs["data"] == {
            "grant_type": DEVICE_CODE_GRANT,
            "device_code": "device-code-1",
            "client_id": known_server.client_id,
        }

    def test_no_credentials_are_sent_to_the_tenant(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        patched_post,
    ):
        """There is nothing to authenticate with yet; that is the whole point."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        client.login()

        for call in patched_post.call_args_list:
            assert "Authorization" not in (call.kwargs.get("headers") or {})

    def test_the_metadata_request_identifies_the_client(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        patched_get,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        client.login()

        metadata_call = patched_get.call_args_list[-1]
        assert metadata_call.kwargs["headers"] == {
            "User-Agent": client.user_agent,
            "Accept": "application/json",
        }

    def test_the_prod_tenant_gets_its_own_registration(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        patched_post, make_discovery_document, das_issuer,
        make_requests_response, as_metadata_document,
    ):
        """Which tenant a site names decides the client id and the audience."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        prod = KNOWN_AUTHORIZATION_SERVERS["https://auth.pamdas.org"]
        fake_device_server(
            issuer=PROD_ISSUER,
            discovery=make_requests_response(
                200,
                json_data=make_discovery_document(das_issuer, PROD_ISSUER)),
            metadata=make_requests_response(
                200, json_data=as_metadata_document(PROD_ISSUER)))

        client.login()

        assert patched_post.call_args_list[0].kwargs["data"] == {
            "client_id": prod.client_id,
            "scope": DEFAULT_SCOPE,
            "audience": prod.audience,
        }


class TestPolling:
    """RFC 8628 section 3.5: wait, ask again, and back off when told to."""

    def test_pending_answers_are_not_failures(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response, device_token_response,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(token_responses=[
            make_requests_response(
                400, json_data={"error": "authorization_pending"}),
            make_requests_response(
                400, json_data={"error": "authorization_pending"}),
            make_requests_response(200, json_data=device_token_response),
        ])

        assert client.login() is True
        assert client.last_auth_error is None

    def test_slow_down_adds_five_seconds_for_good(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response, device_token_response,
    ):
        """The increment is to the interval itself, not to one wait."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(token_responses=[
            make_requests_response(
                400, json_data={"error": "authorization_pending"}),
            make_requests_response(400, json_data={"error": "slow_down"}),
            make_requests_response(
                400, json_data={"error": "authorization_pending"}),
            make_requests_response(200, json_data=device_token_response),
        ])

        client.login()

        assert no_sleep == [1, 1, 6, 6]

    def test_a_retry_after_on_a_slow_down_wins_when_it_is_longer(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response, device_token_response,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(token_responses=[
            make_requests_response(400, json_data={"error": "slow_down"},
                                   headers={"Retry-After": "30"}),
            make_requests_response(200, json_data=device_token_response),
        ])

        client.login()

        assert no_sleep == [1, 30]

    def test_an_interval_the_poller_could_not_wait_for(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response, device_authorization_document,
        device_token_response,
    ):
        """A negative interval is time.sleep()'s ValueError; poll on the default."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(
            authorization=make_requests_response(
                200, json_data=device_authorization_document(interval=-1)),
            token_responses=[
                make_requests_response(
                    400, json_data={"error": "authorization_pending"}),
                make_requests_response(200, json_data=device_token_response),
            ])

        assert client.login() is True
        assert no_sleep and all(seconds > 0 for seconds in no_sleep)

    def test_the_code_expiring_at_the_server(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(token_responses=[
            make_requests_response(400, json_data={"error": "expired_token"}),
        ])

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert str(exc_info.value) == CODE_EXPIRED_MESSAGE
        assert client.last_auth_error.error == "expired_token"
        assert client.auth is None

    def test_the_code_expiring_on_our_own_clock(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response, device_authorization_document, known_issuer,
    ):
        """A server that never says expired_token must not be polled forever."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server(
            authorization=make_requests_response(
                200, json_data=device_authorization_document(expires_in=1)),
            token_responses=[
                make_requests_response(
                    400, json_data={"error": "authorization_pending"}),
            ])

        def polls():
            return urls(server.traffic, "POST").count(
                device_token_endpoint(known_issuer))

        # Keyed off the poll count rather than a fixed sequence: patching
        # time.monotonic patches it for the HTTP libraries too, and a
        # scripted one would run out on whoever else reads the clock.
        with patch("erclient.client.time.monotonic",
                   side_effect=lambda: 0 if not polls() else 100):
            with pytest.raises(ERClientBadCredentials) as exc_info:
                client.login()

        assert str(exc_info.value) == CODE_EXPIRED_MESSAGE
        assert polls() == 1

    def test_the_user_saying_no(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(token_responses=[
            make_requests_response(400, json_data={"error": "access_denied"}),
        ])

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert str(exc_info.value) == SIGN_IN_DECLINED_MESSAGE
        assert client.last_auth_error.error == "access_denied"

    def test_any_other_refusal_is_classified_as_a_login_failure(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response, known_issuer,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(token_responses=[
            make_requests_response(400, json_data={"error": "invalid_scope"}),
        ])

        with pytest.raises(ERClientBadRequest) as exc_info:
            client.login()

        assert str(exc_info.value).startswith("Login failed.")
        assert exc_info.value.status_code == 400
        assert client.last_auth_error.url == device_token_endpoint(
            known_issuer)
        assert client.last_auth_error.grant_type == DEVICE_CODE_GRANT


class TestTheTenantRefusesToStart:
    """A device-authorization request that does not come back with a code."""

    def test_a_refusal_is_classified_like_any_token_refusal(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response, known_issuer,
    ):
        body = {"error": "invalid_client",
                "error_description": "no such client"}
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(
            authorization=make_requests_response(401, json_data=body))

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert str(exc_info.value).startswith("Login failed.")
        assert exc_info.value.status_code == 401
        assert json.loads(exc_info.value.response_body) == body
        assert client.last_auth_error.url == device_code_endpoint(known_issuer)
        assert client.last_auth_error.grant_type == DEVICE_CODE_GRANT
        assert captured_prompt == []

    def test_a_response_we_cannot_poll_on(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response, device_authorization_document, known_issuer,
    ):
        """200 with half a response is as unusable as a refusal."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server(
            authorization=make_requests_response(
                200, json_data=device_authorization_document(user_code=None)))

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert str(exc_info.value).startswith(
            device_authorization_unreadable_message(
                device_code_endpoint(known_issuer)))
        assert device_token_endpoint(known_issuer) not in urls(server.traffic)

    def test_the_message_names_the_endpoint_that_actually_failed(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        make_requests_response, known_issuer,
    ):
        """The metadata document parsed; it is this response that did not."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(
            authorization=make_requests_response(
                200, json_data={"unexpected": True}))

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert device_code_endpoint(known_issuer) in str(exc_info.value)
        assert "metadata" not in str(exc_info.value)


class TestTheAuthorizationServerWillNotDescribeItself:
    """Unlike site discovery, this fetch is required, so its failure is loud."""

    @pytest.fixture
    def metadata_url(self):
        return "https://auth-dev.pamdas.org/.well-known/openid-configuration"

    def test_a_transport_error(
        self, service_root, fake_device_server, patched_get, captured_prompt,
        metadata_url, make_requests_response, dev_discovery_document,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server()
        discovery = make_requests_response(
            200, json_data=dev_discovery_document)

        def get(url, **kwargs):
            if url.endswith("openid-configuration"):
                raise requests.ConnectionError("no route to host")
            return discovery

        patched_get.side_effect = get

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert str(exc_info.value) == metadata_unreadable_message(metadata_url)
        assert exc_info.value.status_code is None
        assert server.token_responses  # nothing was polled

    @pytest.mark.parametrize(
        "metadata_kwargs",
        [
            {"status_code": 500, "text": "<html>Internal Server Error</html>"},
            {"status_code": 404, "text": ""},
        ],
        ids=["server_error", "not_found"],
    )
    def test_an_unhappy_status(
        self, service_root, fake_device_server, captured_prompt, metadata_url,
        make_requests_response, metadata_kwargs, known_issuer,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server(
            metadata=make_requests_response(**metadata_kwargs))

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert str(exc_info.value).startswith(
            metadata_unreadable_message(metadata_url))
        assert exc_info.value.status_code == metadata_kwargs["status_code"]
        assert device_code_endpoint(known_issuer) not in urls(server.traffic)

    def test_a_document_naming_another_issuer(
        self, service_root, fake_device_server, captured_prompt, metadata_url,
        make_requests_response, as_metadata_document, known_issuer,
    ):
        """The canonical Auth0 domain would work, and then EarthRanger would 401."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server(
            metadata=make_requests_response(
                200,
                json_data={**as_metadata_document(known_issuer),
                           "issuer": "https://earthranger-dev.us.auth0.com/"}))

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            client.login()

        assert str(exc_info.value).startswith(
            metadata_unreadable_message(metadata_url))
        assert device_code_endpoint(known_issuer) not in urls(server.traffic)

    def test_a_document_missing_an_endpoint(
        self, service_root, fake_device_server, captured_prompt, metadata_url,
        make_requests_response, as_metadata_document, known_issuer,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server(
            metadata=make_requests_response(
                200,
                json_data=as_metadata_document(
                    known_issuer, device_authorization_endpoint=None)))

        with pytest.raises(ERClientServiceUnreachable):
            client.login()

        assert device_code_endpoint(known_issuer) not in urls(server.traffic)


class TestThereIsNoTenantToSignInAgainst:
    """Refusals decided before anything is asked of an authorization server."""

    def assert_refused(self, client, message, server=None):
        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.login()

        assert str(exc_info.value) == message
        assert exc_info.value.status_code is None
        assert client.auth is None
        auth_error = client.last_auth_error
        # Not credential_site_mismatch: the site's document did not say these
        # credentials cannot work, it said nothing we could sign in against.
        assert auth_error.error == INTERACTIVE_SIGN_IN_UNAVAILABLE
        assert auth_error.status_code is None
        assert auth_error.error_description == message
        assert auth_error.grant_type == DEVICE_CODE_GRANT
        if server is not None:
            assert urls(server.traffic, "POST") == []
            assert not [url for url in urls(server.traffic, "GET")
                        if "openid-configuration" in url]

    def test_discovery_turned_off_and_no_issuer_given(
        self, service_root, patched_get, patched_post,
    ):
        """Without discovery there is nothing left to ask; say which knob fixes it."""
        client = ERClient(service_root=service_root, discovery=False)

        self.assert_refused(client, DISCOVERY_DISABLED_MESSAGE)
        assert not patched_get.called
        assert not patched_post.called

    def test_a_site_that_publishes_no_document(
        self, service_root, fake_device_server, make_requests_response,
    ):
        server = fake_device_server(
            discovery=make_requests_response(404, text=""))

        self.assert_refused(ERClient(service_root=service_root),
                            no_authorization_servers_message(service_root),
                            server)

    def test_a_site_that_names_only_its_own_issuer(
        self, service_root, fake_device_server, make_requests_response,
        make_discovery_document, das_issuer,
    ):
        """A site that has not migrated cannot be signed into interactively."""
        server = fake_device_server(
            discovery=make_requests_response(
                200, json_data=make_discovery_document(das_issuer)))

        self.assert_refused(
            ERClient(service_root=service_root),
            no_known_tenant_message(service_root, das_issuer), server)

    def test_a_site_backed_by_a_tenant_we_do_not_know(
        self, service_root, fake_device_server, make_requests_response,
        make_discovery_document, das_issuer,
    ):
        """Someone else's Auth0 tenant needs a registration we were not given."""
        server = fake_device_server(
            discovery=make_requests_response(
                200,
                json_data=make_discovery_document(das_issuer, OTHER_ISSUER)))

        self.assert_refused(
            ERClient(service_root=service_root),
            no_known_tenant_message(
                service_root,
                f"{das_issuer}, {OTHER_ISSUER.rstrip('/')}"),
            server)

    def test_an_issuer_override_without_the_rest_of_the_registration(
        self, service_root, patched_get, patched_post,
    ):
        """A client id cannot be guessed, so half an override is refused."""
        client = ERClient(service_root=service_root,
                          device_code_issuer=OTHER_ISSUER)

        self.assert_refused(client, INCOMPLETE_OVERRIDE_MESSAGE)
        assert not patched_get.called


class TestOverrides:
    """The known-tenant table is a default, not a limit."""

    def test_a_tenant_this_release_never_heard_of(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        patched_get, patched_post, make_requests_response,
        as_metadata_document,
    ):
        """Issuer, client id and audience together replace discovery entirely."""
        client = ERClient(
            service_root=service_root, discovery=False,
            device_code_issuer=OTHER_ISSUER,
            device_code_client_id="new-client",
            device_code_audience="https://new.example.org/api",
            device_code_prompt=captured_prompt.append)
        server = fake_device_server(
            issuer=OTHER_ISSUER,
            metadata=make_requests_response(
                200, json_data=as_metadata_document(OTHER_ISSUER)))

        assert client.login() is True
        assert urls(server.traffic, "GET") == [
            f"{OTHER_ISSUER.rstrip('/')}/.well-known/openid-configuration"]
        assert patched_post.call_args_list[0].kwargs["data"] == {
            "client_id": "new-client",
            "scope": DEFAULT_SCOPE,
            "audience": "https://new.example.org/api",
        }

    def test_a_client_id_for_a_tenant_we_do_know(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        patched_post, known_server,
    ):
        """A caller with their own registration at the same tenant."""
        client = ERClient(service_root=service_root,
                          device_code_client_id="other-client",
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        client.login()

        assert patched_post.call_args_list[0].kwargs["data"] == {
            "client_id": "other-client",
            "scope": DEFAULT_SCOPE,
            "audience": known_server.audience,
        }

    def test_a_narrower_scope(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        patched_post,
    ):
        client = ERClient(service_root=service_root,
                          device_code_scope="openid",
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        client.login()

        assert patched_post.call_args_list[0].kwargs["data"]["scope"] == "openid"


class TestPromptRouting:
    """Where the code is shown, and who else gets told."""

    def test_the_default_writes_to_stderr_and_the_log(
        self, service_root, fake_device_server, no_sleep, capsys, caplog,
    ):
        """stdout stays clean for a script whose output is being piped."""
        client = ERClient(service_root=service_root)
        fake_device_server()

        with caplog.at_level(logging.INFO, logger="ERClient"):
            client.login()

        captured = capsys.readouterr()
        assert "WDJB-MJHT" in captured.err
        assert captured.err.endswith("\n")
        assert captured.out == ""
        assert "WDJB-MJHT" in caplog.text

    def test_a_callable_takes_over_entirely(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        capsys,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        client.login()

        assert len(captured_prompt) == 1
        assert capsys.readouterr().err == ""

    def test_the_browser_stays_shut_by_default(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        with patch("erclient.client.webbrowser.open") as mock_open:
            client.login()

        assert not mock_open.called

    def test_opening_the_browser_when_asked(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
    ):
        client = ERClient(service_root=service_root, open_browser=True,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        with patch("erclient.client.webbrowser.open") as mock_open:
            client.login()

        mock_open.assert_called_once_with(
            "https://auth-dev.pamdas.org/activate?user_code=WDJB-MJHT")

    def test_a_browser_that_will_not_open_is_not_a_failure(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
    ):
        """The URL was printed either way, so there is nothing to fail about."""
        client = ERClient(service_root=service_root, open_browser=True,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        with patch("erclient.client.webbrowser.open",
                   side_effect=OSError("no display")):
            assert client.login() is True


class TestImplicitLogin:
    """auth_headers() signs the user in, but only where they can see it."""

    def test_with_a_terminal_the_flow_just_runs(
        self, service_root, fake_device_server, no_sleep, captured_prompt, tty,
        device_token_response,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        headers = client.auth_headers()

        assert headers["Authorization"] == (
            f"Bearer {device_token_response['access_token']}")
        assert len(captured_prompt) == 1

    def test_without_a_terminal_nothing_is_attempted(
        self, service_root, patched_get, patched_post, no_tty,
    ):
        """Printing a code where nobody can read it would only hang the caller."""
        client = ERClient(service_root=service_root)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert str(exc_info.value) == no_terminal_message(service_root)
        assert client.last_auth_error.error == INTERACTIVE_SIGN_IN_UNAVAILABLE
        assert client.last_auth_error.status_code is None
        assert client.last_auth_error.grant_type == DEVICE_CODE_GRANT
        assert not patched_get.called
        assert not patched_post.called

    def test_an_explicit_login_proceeds_without_a_terminal(
        self, service_root, fake_device_server, no_sleep, captured_prompt,
        no_tty,
    ):
        """A notebook reports no TTY on stdin, and is exactly who this is for."""
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        assert client.login() is True


class TestExpiry:
    """No refresh token, by design: expiry means signing in again."""

    def test_a_terminal_gets_the_whole_flow_again(
        self, service_root, fake_device_server, no_sleep, captured_prompt, tty,
        discovery_url, known_issuer, device_token_response,
        make_requests_response,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        server = fake_device_server(token_responses=[
            make_requests_response(200, json_data=device_token_response),
            make_requests_response(200, json_data=device_token_response),
        ])

        client.auth_headers()
        client.auth_expires = pytz.utc.localize(datetime.min)
        client.auth_headers()

        assert server.traffic.count(("GET", discovery_url)) == 2
        assert urls(server.traffic, "POST").count(
            device_code_endpoint(known_issuer)) == 2
        assert len(captured_prompt) == 2

    def test_nothing_is_refreshed_and_no_password_is_posted(
        self, service_root, fake_device_server, no_sleep, captured_prompt, tty,
        patched_post, default_token_url, device_token_response,
        make_requests_response,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server(token_responses=[
            make_requests_response(200, json_data=device_token_response),
            make_requests_response(200, json_data=device_token_response),
        ])

        client.auth_headers()
        client.auth_expires = pytz.utc.localize(datetime.min)
        client.auth_headers()

        posted = [call.kwargs.get("data", {})
                  for call in patched_post.call_args_list]
        assert not [data for data in posted
                    if data.get("grant_type") == "refresh_token"]
        assert default_token_url not in [
            call.args[0] for call in patched_post.call_args_list]

    def test_without_a_terminal_the_expired_session_is_reported(
        self, service_root, fake_device_server, no_sleep, captured_prompt, tty,
        monkeypatch, patched_get,
    ):
        client = ERClient(service_root=service_root,
                          device_code_prompt=captured_prompt.append)
        fake_device_server()

        client.auth_headers()
        client.auth_expires = pytz.utc.localize(datetime.min)
        monkeypatch.setattr("erclient.client._stdin_is_tty", lambda: False)
        calls_before = patched_get.call_count

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert str(exc_info.value) == expired_session_message(service_root)
        assert client.last_auth_error.error == INTERACTIVE_SIGN_IN_UNAVAILABLE
        assert client.last_auth_error.status_code is None
        assert patched_get.call_count == calls_before
