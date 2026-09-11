"""What a caller sees when the token endpoint refuses, on both clients. The
sync client raises from auth_headers(); the async one raises the same class
from the request wrapper that caught the httpx error."""
import contextlib

import httpx
import pytest
from tests.auth.conftest import Reply

from erclient.client import AsyncERClient, ERClient
from erclient.er_errors import (AuthError, ERClientBadCredentials,
                                ERClientBadRequest, ERClientException,
                                ERClientInternalError,
                                ERClientRateLimitExceeded,
                                ERClientServiceUnreachable)


class TestTheClassAcallerSees:

    @pytest.mark.parametrize("status_code,expected", [
        (400, ERClientBadRequest),
        (401, ERClientBadCredentials),
        (429, ERClientRateLimitExceeded),
        (500, ERClientInternalError),
        (503, ERClientServiceUnreachable),
    ])
    def test_a_body_with_no_oauth_code_is_classified_by_status(
            self, client, server, ropc_kwargs, default_token_url, status_code,
            expected):
        server.respond("POST", default_token_url, status_code, text="nope")
        client.make(**ropc_kwargs)

        with pytest.raises(expected) as exc_info:
            client.call(client.get_me)

        assert type(exc_info.value) is expected
        assert exc_info.value.status_code == status_code
        assert exc_info.value.response_body == "nope"

    def test_the_oauth_code_in_the_body_beats_the_status(
            self, client, server, ropc_kwargs, default_token_url):
        server.respond("POST", default_token_url, 400,
                       json_body={"error": "invalid_client"})
        client.make(**ropc_kwargs)

        with pytest.raises(ERClientBadCredentials):
            client.call(client.get_me)

    def test_a_code_neither_table_knows_stays_the_base_exception(
            self, client, server, ropc_kwargs, default_token_url):
        server.respond("POST", default_token_url, 418,
                       json_body={"error": "teapot_overheated"})
        client.make(**ropc_kwargs)

        with pytest.raises(ERClientException) as exc_info:
            client.call(client.get_me)

        assert type(exc_info.value) is ERClientException

    def test_a_retry_after_from_the_token_endpoint_reaches_the_caller(
            self, client, server, ropc_kwargs, default_token_url):
        server.respond("POST", default_token_url, 429, text="slow down",
                       headers={"Retry-After": "7"})
        client.make(**ropc_kwargs)

        with pytest.raises(ERClientRateLimitExceeded) as exc_info:
            client.call(client.get_me)

        assert exc_info.value.retry_after == 7


class TestWhatIsNotClassified:

    def test_a_transport_error_is_raised_as_it_is(
            self, client, server, ropc_kwargs, default_token_url):
        server.fail("POST", default_token_url,
                    client.transport_error("no route to host"))
        client.make(**ropc_kwargs)

        with pytest.raises(client.transport_error):
            client.login()

    def test_a_success_drops_the_refusal_that_would_misclassify_the_next_one(
            self, client, server, ropc_kwargs, default_token_url,
            token_response):
        server.script("POST", default_token_url,
                      Reply(401, text="nope"),
                      Reply(json_body=token_response))
        client.make(**ropc_kwargs)

        with contextlib.suppress(httpx.HTTPStatusError):
            client.login()
        assert client.last_auth_error is not None

        assert client.login() is True
        assert client.last_auth_error is None


class TestWhereASyncCallerReadsTheReason:
    """Sync login() returns a bare False, so the detail has to live somewhere."""

    def test_nothing_has_been_refused_yet(self, client, ropc_kwargs):
        client.make(**ropc_kwargs)

        assert client.last_auth_error is None

    def test_a_refusal_from_the_token_endpoint(self, client, server,
                                               ropc_kwargs, default_token_url):
        server.respond("POST", default_token_url, 400,
                       json_body={"error": "invalid_grant",
                                  "error_description": "wrong password"},
                       headers={"Retry-After": "5"})
        client.make(**ropc_kwargs)

        with contextlib.suppress(httpx.HTTPStatusError):
            client.login()

        auth_error = client.last_auth_error
        assert auth_error.status_code == 400
        assert auth_error.error == "invalid_grant"
        assert auth_error.error_description == "wrong password"
        assert auth_error.url == default_token_url
        assert auth_error.grant_type == "password"
        assert auth_error.retry_after == 5

    def test_a_refusal_the_client_made_itself(self, client, server,
                                              ropc_kwargs, discovery_url,
                                              service_root):
        server.respond("GET", discovery_url, json_body={
            "resource": service_root,
            "authorization_servers": ["https://auth-dev.pamdas.org"]})
        client.make(**ropc_kwargs)

        with contextlib.suppress(ERClientBadCredentials):
            client.login()

        auth_error = client.last_auth_error
        assert auth_error.error == "credential_site_mismatch"
        # No server was consulted, so there is no status and no body to show.
        assert auth_error.status_code is None
        assert auth_error.response_body is None
        assert "accepts only Auth0-issued tokens" in auth_error.error_description

    def test_it_is_the_same_property_on_both_clients(self):
        assert ERClient.last_auth_error is AsyncERClient.last_auth_error

    def test_its_type_can_be_imported_from_the_package(self):
        import erclient

        assert erclient.AuthError is AuthError
