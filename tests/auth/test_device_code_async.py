"""AsyncERClient signs a user in interactively when it was given no credentials.

The async counterpart of ``test_device_code_sync.py``. The flow is the same
one, and it has to stay the same: the two clients differ enough already, and a
caller moving between them should not discover that one of them signs in
differently, prompts differently, or refuses for different reasons.

What is genuinely different is what escapes. The async client's ``login()``
raises rather than returning a bool, and everywhere the password grant lets an
``httpx.HTTPStatusError`` out for a wrapper to classify, this path raises the
EarthRanger exception itself — there is no wrapper between a caller and their
own ``login()`` call.
"""
import json
import logging
import webbrowser
from datetime import datetime
from unittest.mock import patch

import httpx
import pytest
import pytz
import respx
from tests.auth.conftest import (CODE_EXPIRED_MESSAGE,
                                 DISCOVERY_DISABLED_MESSAGE,
                                 INCOMPLETE_OVERRIDE_MESSAGE,
                                 OVERRIDE_NOT_HTTPS_MESSAGE,
                                 SIGN_IN_DECLINED_MESSAGE,
                                 device_authorization_unreadable_message,
                                 expired_session_message,
                                 metadata_unreadable_message,
                                 no_authorization_servers_message,
                                 no_known_tenant_message, no_terminal_message)
from tests.auth.respx_helpers import (KNOWN_ISSUER, device_code_endpoint,
                                      device_token_endpoint, flat_timeout,
                                      metadata_endpoint, mock_device_flow,
                                      timeout_of, traffic)

from erclient.client import (DEVICE_CODE_TIMEOUT_SECONDS,
                             DISCOVERY_TIMEOUT_SECONDS)
from erclient.device_code import (DEFAULT_SCOPE, DEVICE_CODE_GRANT,
                                  KNOWN_AUTHORIZATION_SERVERS)
from erclient.er_errors import (INTERACTIVE_SIGN_IN_UNAVAILABLE,
                                ERClientBadCredentials, ERClientBadRequest,
                                ERClientServiceUnreachable)

PROD_ISSUER = "https://auth.pamdas.org/"
OTHER_ISSUER = "https://someone-elses-tenant.us.auth0.com/"
VERIFICATION_URL = (
    "https://auth-dev.pamdas.org/activate?user_code=WDJB-MJHT")

pytestmark = pytest.mark.asyncio


def form(request):
    """The form fields of a recorded request."""
    return dict(httpx.QueryParams(request.content.decode()))


@pytest.fixture
def flow(async_client_factory, service_root, dev_discovery_document,
         as_metadata_document, device_authorization_document,
         device_token_response):
    """A client with no credentials, and the fake tenant it will talk to."""

    def _install(respx_mock, *, issuer=KNOWN_ISSUER, discovery=..., metadata=...,
                 authorization=..., token_responses=..., **client_kwargs):
        if discovery is ...:
            discovery = httpx.Response(200, json=dev_discovery_document)
        if metadata is ...:
            metadata = httpx.Response(200, json=as_metadata_document(issuer))
        if authorization is ...:
            authorization = httpx.Response(
                200, json=device_authorization_document())
        if token_responses is ...:
            token_responses = [httpx.Response(200, json=device_token_response)]
        mock_device_flow(respx_mock, service_root, issuer=issuer,
                         discovery=discovery, metadata=metadata,
                         authorization=authorization,
                         token_responses=token_responses)
        return async_client_factory(service_root=service_root, **client_kwargs)

    return _install


class TestWhichFlowIsSelected:
    """One rule, and it is the sync client's rule."""

    @pytest.mark.parametrize(
        "kwargs, expected",
        [
            ({}, True),
            ({"token": ""}, True),
            ({"token": "a-token"}, False),
            ({"username": "u"}, False),
            ({"client_id": "das_web_client"}, False),
            ({"token": "", "username": "u"}, False),
        ],
        ids=["nothing", "empty_token", "token", "username", "client_id",
             "empty_token_with_username"],
    )
    async def test_the_truth_table(
        self, service_root, async_client_factory, kwargs, expected
    ):
        client = async_client_factory(service_root=service_root, **kwargs)

        assert client._uses_device_code() is expected

    async def test_a_lone_client_id_still_posts_a_password_grant(
        self, service_root, default_token_url, async_client_factory,
        token_response,
    ):
        client = async_client_factory(service_root=service_root,
                                      client_id="das_web_client")

        async with respx.mock as respx_mock:
            respx_mock.get(f"{service_root}/.well-known/"
                           "oauth-protected-resource").mock(
                return_value=httpx.Response(404))
            token_route = respx_mock.post(default_token_url).mock(
                return_value=httpx.Response(200, json=token_response))

            assert await client.login() is True

        assert form(token_route.calls[0].request)["grant_type"] == "password"


class TestTheHappyPath:
    """An explicit login() against a site that names a tenant we know."""

    async def test_returns_true_and_holds_the_token(
        self, flow, no_async_sleep, captured_prompt, device_token_response,
        assert_expiry_matches,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append)

            assert await client.login() is True

        assert client.auth == device_token_response
        assert_expiry_matches(client.auth_expires,
                              device_token_response["expires_in"])
        assert client.last_auth_error is None

    async def test_the_order_of_the_conversation(
        self, flow, no_async_sleep, captured_prompt, discovery_url,
        device_token_response,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(
                                  400,
                                  json={"error": "authorization_pending"}),
                              httpx.Response(200, json=device_token_response),
                          ])

            await client.login()

            assert traffic(respx_mock) == [
                ("GET", discovery_url),
                ("GET", metadata_endpoint(KNOWN_ISSUER)),
                ("POST", device_code_endpoint(KNOWN_ISSUER)),
                ("POST", device_token_endpoint(KNOWN_ISSUER)),
                ("POST", device_token_endpoint(KNOWN_ISSUER)),
            ]

    async def test_everything_goes_to_the_custom_domain(
        self, flow, no_async_sleep, captured_prompt, service_root,
    ):
        """A token minted at a canonical auth0.com name is one EarthRanger rejects."""
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append)

            await client.login()

            tenant_urls = [url for _, url in traffic(respx_mock)
                           if not url.startswith(service_root)]

        assert tenant_urls
        assert all(url.startswith("https://auth-dev.pamdas.org/")
                   for url in tenant_urls)

    async def test_the_user_is_told_where_to_go_and_what_to_confirm(
        self, flow, no_async_sleep, captured_prompt, service_root,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append)

            await client.login()

        assert captured_prompt == [
            "You are about to authorize the EarthRanger Python Client to "
            f"access {service_root} as your user.\n"
            "Open https://auth-dev.pamdas.org/activate?user_code=WDJB-MJHT in "
            "a browser and confirm that it shows the code WDJB-MJHT.\n"
            "Waiting for approval..."
        ]

    async def test_the_two_requests_field_by_field(
        self, flow, no_async_sleep, captured_prompt, known_server,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append)

            await client.login()

            device_request, token_request = [
                call.request for call in respx_mock.calls
                if call.request.method == "POST"]

        assert form(device_request) == {
            "client_id": known_server.client_id,
            "scope": DEFAULT_SCOPE,
            "audience": known_server.audience,
        }
        assert form(token_request) == {
            "grant_type": DEVICE_CODE_GRANT,
            "device_code": "device-code-1",
            "client_id": known_server.client_id,
        }
        assert "Authorization" not in device_request.headers
        assert "Authorization" not in token_request.headers

    async def test_the_prod_tenant_gets_its_own_registration(
        self, flow, no_async_sleep, captured_prompt, make_discovery_document,
        das_issuer, as_metadata_document,
    ):
        async with respx.mock as respx_mock:
            client = flow(
                respx_mock, issuer=PROD_ISSUER,
                device_code_prompt=captured_prompt.append,
                discovery=httpx.Response(
                    200,
                    json=make_discovery_document(das_issuer, PROD_ISSUER)),
                metadata=httpx.Response(
                    200, json=as_metadata_document(PROD_ISSUER)))

            await client.login()

            device_request = next(
                call.request for call in respx_mock.calls
                if call.request.method == "POST")

        prod = KNOWN_AUTHORIZATION_SERVERS["https://auth.pamdas.org"]
        assert form(device_request) == {
            "client_id": prod.client_id,
            "scope": DEFAULT_SCOPE,
            "audience": prod.audience,
        }


class TestTheFlowHasItsOwnDeadlines:
    """A user is watching, so these requests keep off the caller's timeouts."""

    async def test_each_request_carries_its_own(
        self, flow, no_async_sleep, captured_prompt, device_token_response,
        discovery_url,
    ):
        """The sync client spells these out; routing them through the session
        would silently hand them the caller's API timeouts instead."""
        async with respx.mock as respx_mock:
            client = flow(respx_mock, data_timeout=97,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(
                                  400,
                                  json={"error": "authorization_pending"}),
                              httpx.Response(200, json=device_token_response),
                          ])

            await client.login()

            discovery = flat_timeout(DISCOVERY_TIMEOUT_SECONDS)
            device_code = flat_timeout(DEVICE_CODE_TIMEOUT_SECONDS)
            assert timeout_of(respx_mock, discovery_url, "GET") == discovery
            assert timeout_of(
                respx_mock, metadata_endpoint(KNOWN_ISSUER), "GET") == discovery
            assert timeout_of(
                respx_mock, device_code_endpoint(KNOWN_ISSUER),
                "POST") == device_code
            assert timeout_of(
                respx_mock, device_token_endpoint(KNOWN_ISSUER),
                "POST") == device_code


class TestPolling:
    """RFC 8628 section 3.5, on asyncio.sleep instead of time.sleep."""

    async def test_pending_answers_are_not_failures(
        self, flow, no_async_sleep, captured_prompt, device_token_response,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(
                                  400,
                                  json={"error": "authorization_pending"}),
                              httpx.Response(
                                  400,
                                  json={"error": "authorization_pending"}),
                              httpx.Response(200, json=device_token_response),
                          ])

            assert await client.login() is True

        assert client.last_auth_error is None
        assert no_async_sleep == [1, 1, 1]

    async def test_slow_down_adds_five_seconds_for_good(
        self, flow, no_async_sleep, captured_prompt, device_token_response,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(
                                  400,
                                  json={"error": "authorization_pending"}),
                              httpx.Response(400, json={"error": "slow_down"}),
                              httpx.Response(
                                  400,
                                  json={"error": "authorization_pending"}),
                              httpx.Response(200, json=device_token_response),
                          ])

            await client.login()

        assert no_async_sleep == [1, 1, 6, 6]

    async def test_a_retry_after_on_a_slow_down_wins_when_it_is_longer(
        self, flow, no_async_sleep, captured_prompt, device_token_response,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(400, json={"error": "slow_down"},
                                             headers={"Retry-After": "30"}),
                              httpx.Response(200, json=device_token_response),
                          ])

            await client.login()

        assert no_async_sleep == [1, 30]

    async def test_an_interval_the_poller_could_not_wait_for(
        self, flow, no_async_sleep, captured_prompt,
        device_authorization_document, device_token_response,
    ):
        """A negative interval is a wait that never was; poll on the default."""
        async with respx.mock as respx_mock:
            client = flow(
                respx_mock, device_code_prompt=captured_prompt.append,
                authorization=httpx.Response(
                    200, json=device_authorization_document(interval=-1)),
                token_responses=[
                    httpx.Response(400,
                                   json={"error": "authorization_pending"}),
                    httpx.Response(200, json=device_token_response),
                ])

            assert await client.login() is True

        assert no_async_sleep and all(
            seconds > 0 for seconds in no_async_sleep)

    async def test_the_code_expiring_at_the_server(
        self, flow, no_async_sleep, captured_prompt,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(
                                  400, json={"error": "expired_token"})])

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.login()

        assert str(exc_info.value) == CODE_EXPIRED_MESSAGE
        assert client.last_auth_error.error == "expired_token"
        assert client.auth is None

    async def test_the_code_expiring_on_our_own_clock(
        self, flow, no_async_sleep, captured_prompt,
        device_authorization_document, monkeypatch,
    ):
        """A server that never says expired_token must not be polled forever."""
        async with respx.mock as respx_mock:
            client = flow(
                respx_mock, device_code_prompt=captured_prompt.append,
                authorization=httpx.Response(
                    200, json=device_authorization_document(expires_in=1)),
                token_responses=[
                    httpx.Response(400,
                                   json={"error": "authorization_pending"})])

            def polls():
                return len([url for _, url in traffic(respx_mock)
                            if url == device_token_endpoint(KNOWN_ISSUER)])

            # Keyed off the poll count rather than a fixed sequence: patching
            # time.monotonic patches it for httpx and asyncio too, and they
            # would consume a scripted one.
            monkeypatch.setattr("erclient.client.time.monotonic",
                                lambda: 0 if not polls() else 100)

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.login()

            polled = polls()

        assert str(exc_info.value) == CODE_EXPIRED_MESSAGE
        assert polled == 1

    async def test_the_user_saying_no(
        self, flow, no_async_sleep, captured_prompt,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(
                                  400, json={"error": "access_denied"})])

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.login()

        assert str(exc_info.value) == SIGN_IN_DECLINED_MESSAGE
        assert client.last_auth_error.error == "access_denied"

    async def test_any_other_refusal_is_classified_as_a_login_failure(
        self, flow, no_async_sleep, captured_prompt,
    ):
        """Never an httpx error: a caller's own login() call raises ours."""
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(
                                  400, json={"error": "invalid_scope"})])

            with pytest.raises(ERClientBadRequest) as exc_info:
                await client.login()

        assert str(exc_info.value).startswith("Login failed.")
        assert exc_info.value.status_code == 400
        assert client.last_auth_error.url == device_token_endpoint(
            KNOWN_ISSUER)
        assert client.last_auth_error.grant_type == DEVICE_CODE_GRANT


class TestTheTenantRefusesToStart:
    """A device-authorization request that does not come back with a code."""

    async def test_a_refusal_is_classified_like_any_token_refusal(
        self, flow, no_async_sleep, captured_prompt,
    ):
        body = {"error": "invalid_client",
                "error_description": "no such client"}

        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          authorization=httpx.Response(401, json=body),
                          token_responses=None)

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.login()

        assert str(exc_info.value).startswith("Login failed.")
        assert exc_info.value.status_code == 401
        assert json.loads(exc_info.value.response_body) == body
        assert client.last_auth_error.url == device_code_endpoint(KNOWN_ISSUER)
        assert client.last_auth_error.grant_type == DEVICE_CODE_GRANT
        assert captured_prompt == []

    async def test_a_response_we_cannot_poll_on(
        self, flow, no_async_sleep, captured_prompt,
        device_authorization_document,
    ):
        async with respx.mock as respx_mock:
            client = flow(
                respx_mock, device_code_prompt=captured_prompt.append,
                authorization=httpx.Response(
                    200, json=device_authorization_document(user_code=None)),
                token_responses=None)

            with pytest.raises(ERClientServiceUnreachable) as exc_info:
                await client.login()

        assert str(exc_info.value).startswith(
            device_authorization_unreadable_message(
                device_code_endpoint(KNOWN_ISSUER)))

    async def test_the_message_names_the_endpoint_that_actually_failed(
        self, flow, no_async_sleep, captured_prompt,
    ):
        """The metadata document parsed; it is this response that did not."""
        async with respx.mock as respx_mock:
            client = flow(
                respx_mock, device_code_prompt=captured_prompt.append,
                authorization=httpx.Response(200, json={"unexpected": True}),
                token_responses=None)

            with pytest.raises(ERClientServiceUnreachable) as exc_info:
                await client.login()

        assert device_code_endpoint(KNOWN_ISSUER) in str(exc_info.value)
        assert "metadata" not in str(exc_info.value)


class TestTheAuthorizationServerWillNotDescribeItself:
    """Unlike site discovery, this fetch is required, so its failure is loud."""

    async def test_a_transport_error(
        self, flow, captured_prompt, service_root, dev_discovery_document,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          metadata=None, authorization=None,
                          token_responses=None)
            respx_mock.get(metadata_endpoint(KNOWN_ISSUER)).mock(
                side_effect=httpx.ConnectError("no route to host"))

            with pytest.raises(ERClientServiceUnreachable) as exc_info:
                await client.login()

        assert str(exc_info.value) == metadata_unreadable_message(
            metadata_endpoint(KNOWN_ISSUER))
        assert exc_info.value.status_code is None

    @pytest.mark.parametrize("status_code", [500, 404])
    async def test_an_unhappy_status(
        self, flow, captured_prompt, status_code,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          metadata=httpx.Response(status_code, text=""),
                          authorization=None, token_responses=None)

            with pytest.raises(ERClientServiceUnreachable) as exc_info:
                await client.login()

        assert str(exc_info.value).startswith(metadata_unreadable_message(
            metadata_endpoint(KNOWN_ISSUER)))
        assert exc_info.value.status_code == status_code

    async def test_a_document_naming_another_issuer(
        self, flow, captured_prompt, as_metadata_document,
    ):
        """The canonical Auth0 domain would work, and then EarthRanger would 401."""
        async with respx.mock as respx_mock:
            client = flow(
                respx_mock, device_code_prompt=captured_prompt.append,
                metadata=httpx.Response(
                    200,
                    json={**as_metadata_document(KNOWN_ISSUER),
                          "issuer": "https://earthranger-dev.us.auth0.com/"}),
                authorization=None, token_responses=None)

            with pytest.raises(ERClientServiceUnreachable):
                await client.login()

    async def test_a_document_missing_an_endpoint(
        self, flow, captured_prompt, as_metadata_document,
    ):
        async with respx.mock as respx_mock:
            client = flow(
                respx_mock, device_code_prompt=captured_prompt.append,
                metadata=httpx.Response(
                    200,
                    json=as_metadata_document(
                        KNOWN_ISSUER, device_authorization_endpoint=None)),
                authorization=None, token_responses=None)

            with pytest.raises(ERClientServiceUnreachable):
                await client.login()


class TestThereIsNoTenantToSignInAgainst:
    """Refusals decided before anything is asked of an authorization server."""

    async def assert_refused(self, client, message):
        with pytest.raises(ERClientBadCredentials) as exc_info:
            await client.login()

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

    async def test_discovery_turned_off_and_no_issuer_given(
        self, service_root, async_client_factory,
    ):
        client = async_client_factory(service_root=service_root,
                                      discovery=False)

        async with respx.mock:
            # respx refuses any request at all here, so a fetch would fail
            # this test rather than escape it.
            await self.assert_refused(client, DISCOVERY_DISABLED_MESSAGE)

    async def test_a_site_that_publishes_no_document(
        self, flow, service_root,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock, discovery=httpx.Response(404),
                          metadata=None, authorization=None,
                          token_responses=None)

            await self.assert_refused(
                client, no_authorization_servers_message(service_root))

    async def test_a_site_that_names_only_its_own_issuer(
        self, flow, service_root, make_discovery_document, das_issuer,
    ):
        async with respx.mock as respx_mock:
            client = flow(
                respx_mock,
                discovery=httpx.Response(
                    200, json=make_discovery_document(das_issuer)),
                metadata=None, authorization=None, token_responses=None)

            await self.assert_refused(
                client, no_known_tenant_message(service_root, das_issuer))

    async def test_a_site_backed_by_a_tenant_we_do_not_know(
        self, flow, service_root, make_discovery_document, das_issuer,
    ):
        async with respx.mock as respx_mock:
            client = flow(
                respx_mock,
                discovery=httpx.Response(
                    200,
                    json=make_discovery_document(das_issuer, OTHER_ISSUER)),
                metadata=None, authorization=None, token_responses=None)

            await self.assert_refused(
                client,
                no_known_tenant_message(
                    service_root, f"{das_issuer}, {OTHER_ISSUER.rstrip('/')}"))

    async def test_an_issuer_override_without_the_rest_of_the_registration(
        self, service_root, async_client_factory,
    ):
        client = async_client_factory(service_root=service_root,
                                      device_code_issuer=OTHER_ISSUER)

        async with respx.mock:
            await self.assert_refused(client, INCOMPLETE_OVERRIDE_MESSAGE)

    async def test_an_issuer_override_that_is_not_https(
        self, service_root, async_client_factory,
    ):
        """Its metadata names where credentials go, so it is never fetched in
        the clear — not even with the whole registration supplied."""
        client = async_client_factory(
            service_root=service_root,
            device_code_issuer="http://someone-elses-tenant.us.auth0.com",
            device_code_client_id="new-client",
            device_code_audience="https://new.example.org/api")

        async with respx.mock as respx_mock:
            await self.assert_refused(client, OVERRIDE_NOT_HTTPS_MESSAGE)
            assert not respx_mock.calls


class TestOverrides:
    """The known-tenant table is a default, not a limit."""

    async def test_a_tenant_this_release_never_heard_of(
        self, async_client_factory, service_root, no_async_sleep,
        captured_prompt, as_metadata_document, device_authorization_document,
        device_token_response,
    ):
        """Issuer, client id and audience together replace discovery entirely."""
        client = async_client_factory(
            service_root=service_root, discovery=False,
            device_code_issuer=OTHER_ISSUER,
            device_code_client_id="new-client",
            device_code_audience="https://new.example.org/api",
            device_code_prompt=captured_prompt.append)

        async with respx.mock as respx_mock:
            mock_device_flow(
                respx_mock, service_root, issuer=OTHER_ISSUER,
                metadata=httpx.Response(
                    200, json=as_metadata_document(OTHER_ISSUER)),
                authorization=httpx.Response(
                    200, json=device_authorization_document()),
                token_responses=[
                    httpx.Response(200, json=device_token_response)])

            assert await client.login() is True

            assert [url for _, url in traffic(respx_mock)] == [
                metadata_endpoint(OTHER_ISSUER),
                device_code_endpoint(OTHER_ISSUER),
                device_token_endpoint(OTHER_ISSUER),
            ]
            device_request = next(
                call.request for call in respx_mock.calls
                if call.request.method == "POST")

        assert form(device_request) == {
            "client_id": "new-client",
            "scope": DEFAULT_SCOPE,
            "audience": "https://new.example.org/api",
        }

    async def test_a_client_id_for_a_tenant_we_do_know(
        self, flow, no_async_sleep, captured_prompt, known_server,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_client_id="other-client",
                          device_code_prompt=captured_prompt.append)

            await client.login()

            device_request = next(
                call.request for call in respx_mock.calls
                if call.request.method == "POST")

        assert form(device_request) == {
            "client_id": "other-client",
            "scope": DEFAULT_SCOPE,
            "audience": known_server.audience,
        }

    async def test_a_narrower_scope(
        self, flow, no_async_sleep, captured_prompt,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock, device_code_scope="openid",
                          device_code_prompt=captured_prompt.append)

            await client.login()

            device_request = next(
                call.request for call in respx_mock.calls
                if call.request.method == "POST")

        assert form(device_request)["scope"] == "openid"


class TestPromptRouting:
    """Where the code is shown, and who else gets told."""

    async def test_the_default_writes_to_stderr_and_summarizes_to_the_log(
        self, flow, no_async_sleep, capsys, caplog,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock)

            with caplog.at_level(logging.INFO, logger="AsyncERClient"):
                await client.login()

        captured = capsys.readouterr()
        assert "WDJB-MJHT" in captured.err
        assert captured.out == ""
        assert "https://auth-dev.pamdas.org/activate" in caplog.text

    async def test_the_prompt_is_shown_exactly_once(
        self, flow, no_async_sleep, capsys, caplog,
    ):
        """As on the sync client: stderr and a stderr-configured log would
        otherwise show the same code twice."""
        async with respx.mock as respx_mock:
            client = flow(respx_mock)

            with caplog.at_level(logging.INFO, logger="AsyncERClient"):
                await client.login()

        captured = capsys.readouterr()
        # The prompt itself names the code twice on purpose (RFC 8628 section
        # 5.4: the user confirms the page shows the same one), so what must
        # not double is the prompt, and the log must not carry the code at all.
        opening = "You are about to authorize the EarthRanger Python Client"
        appearances = captured.err.count(opening) + sum(
            record.getMessage().count(opening) for record in caplog.records)
        assert appearances == 1
        assert "WDJB-MJHT" not in caplog.text

    async def test_opening_the_browser_when_asked(
        self, flow, no_async_sleep, captured_prompt, monkeypatch,
    ):
        opened = []
        monkeypatch.setattr("erclient.client.webbrowser.open", opened.append)

        async with respx.mock as respx_mock:
            client = flow(respx_mock, open_browser=True,
                          device_code_prompt=captured_prompt.append)

            await client.login()

        assert opened == [
            "https://auth-dev.pamdas.org/activate?user_code=WDJB-MJHT"]

    @pytest.mark.parametrize(
        "patch_kwargs",
        [
            {"return_value": False},
            {"side_effect": OSError("no display")},
            {"side_effect": webbrowser.Error("no runnable browser")},
        ],
        ids=["returns_false", "raises_oserror", "raises_webbrowser_error"],
    )
    async def test_a_browser_that_will_not_open_is_not_a_failure(
        self, flow, no_async_sleep, captured_prompt, caplog, patch_kwargs,
    ):
        """The URL was printed either way, so there is nothing to fail about."""
        with patch("erclient.client.webbrowser.open", **patch_kwargs):
            async with respx.mock as respx_mock:
                client = flow(respx_mock, open_browser=True,
                              device_code_prompt=captured_prompt.append)

                with caplog.at_level(logging.DEBUG, logger="AsyncERClient"):
                    assert await client.login() is True

        assert any(VERIFICATION_URL in record.getMessage()
                   for record in caplog.records
                   if record.levelno == logging.DEBUG)


class TestImplicitLogin:
    """A request method signs the user in, but only where they can see it."""

    async def test_with_a_terminal_the_flow_just_runs(
        self, flow, no_async_sleep, captured_prompt, tty, service_root,
        device_token_response,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append)
            api_route = respx_mock.get(
                f"{service_root}/api/v1.0/user/me").mock(
                return_value=httpx.Response(200, json={"data": {"id": "1"}}))

            await client.get_me()

            assert api_route.calls[0].request.headers["Authorization"] == (
                f"Bearer {device_token_response['access_token']}")
        assert len(captured_prompt) == 1

    async def test_without_a_terminal_nothing_is_attempted(
        self, service_root, async_client_factory, no_tty,
    ):
        """Printing a code where nobody can read it would only hang the caller."""
        client = async_client_factory(service_root=service_root)

        async with respx.mock:
            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.get_me()

        assert str(exc_info.value) == no_terminal_message(service_root)
        assert client.last_auth_error.error == INTERACTIVE_SIGN_IN_UNAVAILABLE
        assert client.last_auth_error.status_code is None
        assert client.last_auth_error.grant_type == DEVICE_CODE_GRANT

    async def test_an_explicit_login_proceeds_without_a_terminal(
        self, flow, no_async_sleep, captured_prompt, no_tty,
    ):
        """A notebook reports no TTY on stdin, and is exactly who this is for."""
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append)

            assert await client.login() is True


class TestExpiry:
    """No refresh token, by design: expiry means signing in again."""

    async def test_a_terminal_gets_the_whole_flow_again(
        self, flow, no_async_sleep, captured_prompt, tty, discovery_url,
        device_token_response,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(200, json=device_token_response),
                              httpx.Response(200, json=device_token_response),
                          ])

            await client.auth_headers()
            client.auth_expires = pytz.utc.localize(datetime.min)
            await client.auth_headers()

            requested = traffic(respx_mock)

        assert requested.count(("GET", discovery_url)) == 2
        assert requested.count(
            ("POST", device_code_endpoint(KNOWN_ISSUER))) == 2
        assert len(captured_prompt) == 2

    async def test_nothing_is_refreshed_and_no_password_is_posted(
        self, flow, no_async_sleep, captured_prompt, tty, default_token_url,
        device_token_response,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append,
                          token_responses=[
                              httpx.Response(200, json=device_token_response),
                              httpx.Response(200, json=device_token_response),
                          ])

            await client.auth_headers()
            client.auth_expires = pytz.utc.localize(datetime.min)
            await client.auth_headers()

            requested = [url for _, url in traffic(respx_mock)]

        assert default_token_url not in requested

    async def test_without_a_terminal_the_expired_session_is_reported(
        self, flow, no_async_sleep, captured_prompt, tty, service_root,
        monkeypatch,
    ):
        async with respx.mock as respx_mock:
            client = flow(respx_mock,
                          device_code_prompt=captured_prompt.append)

            await client.auth_headers()
            client.auth_expires = pytz.utc.localize(datetime.min)
            monkeypatch.setattr("erclient.client._stdin_is_tty", lambda: False)
            calls_before = len(respx_mock.calls)

            with pytest.raises(ERClientBadCredentials) as exc_info:
                await client.auth_headers()

            assert len(respx_mock.calls) == calls_before

        assert str(exc_info.value) == expired_session_message(service_root)
        assert client.last_auth_error.error == INTERACTIVE_SIGN_IN_UNAVAILABLE
        assert client.last_auth_error.status_code is None
