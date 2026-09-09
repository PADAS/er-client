"""What a caller sees when the token endpoint refuses, on both clients. The
sync client raises from auth_headers(); the async one raises the same class
from the request wrapper that caught the httpx error."""
import contextlib

import httpx
import pytest
from tests.auth.conftest import Reply

from erclient.er_errors import (ERClientBadCredentials, ERClientBadRequest,
                                ERClientException, ERClientInternalError,
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
        assert client._last_auth_error is not None

        assert client.login() is True
        assert client._last_auth_error is None
