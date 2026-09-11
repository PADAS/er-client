"""Refusing a username/password grant at a site that has finished migrating.
Its token endpoint may still hand out a token; the API would reject every
request made with one."""
import contextlib
from datetime import datetime

import pytest
import pytz
from tests.auth.conftest import Reply, auth_warnings

from erclient.er_errors import ERClientBadCredentials

AUTH0_ISSUER = "https://auth-dev.pamdas.org"


@pytest.fixture
def publishes(server, discovery_url, service_root):
    """Make the site publish the issuers a test names."""

    def _publish(*authorization_servers):
        server.always("GET", discovery_url, Reply(json_body={
            "resource": service_root,
            "authorization_servers": list(authorization_servers)}))

    return _publish


@pytest.fixture
def refusal_message(service_root):
    return (
        f"Site {service_root} accepts only Auth0-issued tokens, so "
        "username/password login against its legacy token endpoint cannot "
        "work: the token endpoint may still issue a token, but every API "
        "request would be rejected. Pass an Auth0-issued access token with "
        "token=, or construct the client with no credentials and call login() "
        "to sign in interactively."
    )


class TestASiteThatOnlyAcceptsAuth0Tokens:

    def test_the_password_is_never_posted(self, client, server, ropc_kwargs,
                                          publishes):
        publishes(AUTH0_ISSUER)
        client.make(**ropc_kwargs)

        with pytest.raises(ERClientBadCredentials):
            client.auth_headers()

        assert server.posts == []

    def test_login_reports_the_refusal_the_way_each_client_reports_failure(
            self, client, ropc_kwargs, publishes, refusal_message):
        publishes(AUTH0_ISSUER)
        client.make(**ropc_kwargs)

        if client.kind == "sync":
            assert client.login() is False
        else:
            with pytest.raises(ERClientBadCredentials) as exc_info:
                client.login()
            assert str(exc_info.value) == refusal_message

    def test_auth_headers_raises_with_the_whole_explanation(
            self, client, ropc_kwargs, publishes, refusal_message):
        publishes(AUTH0_ISSUER)
        client.make(**ropc_kwargs)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert str(exc_info.value) == refusal_message
        assert exc_info.value.status_code is None

    def test_nothing_usable_is_left_behind(self, client, ropc_kwargs,
                                           publishes, token_response,
                                           default_token_url, server):
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(**ropc_kwargs)
        client.login()
        publishes(AUTH0_ISSUER)

        with contextlib.suppress(ERClientBadCredentials):
            client.login()

        assert client.auth is None
        assert client._last_auth_error.error == "credential_site_mismatch"
        assert client._last_auth_error.grant_type == "password"

    def test_a_supplied_token_is_not_refused(self, client, token_kwargs,
                                             publishes):
        publishes(AUTH0_ISSUER)
        client.make(**token_kwargs)

        assert client.auth_headers()["Authorization"].startswith("Bearer ")


class TestASiteThatCanStillHonourIt:

    @pytest.mark.parametrize("published,deprecated", [
        (("https://fake-site.erdomain.org/oauth2",), False),
        (("https://fake-site.erdomain.org/oauth2", AUTH0_ISSUER), True),
        ((), False),
    ])
    def test_the_grant_is_posted_as_before(self, client, server, ropc_kwargs,
                                           publishes, default_token_url,
                                           token_response, recwarn, published,
                                           deprecated):
        publishes(*published)
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(**ropc_kwargs)

        assert client.login() is True
        assert bool(auth_warnings(recwarn.list)) is deprecated

    def test_a_site_serving_no_document_is_no_evidence(self, client, server,
                                                       ropc_kwargs,
                                                       discovery_url,
                                                       default_token_url,
                                                       token_response):
        server.respond("GET", discovery_url, 500, text="")
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(**ropc_kwargs)

        assert client.login() is True


class TestWhenTheSiteIsAsked:

    def test_on_every_login_rather_than_once(self, client, server,
                                             ropc_kwargs, discovery_url,
                                             default_token_url,
                                             token_response):
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(**ropc_kwargs)

        client.login()
        client.login()

        assert server.calls.count(("GET", discovery_url)) == 2

    def test_a_site_that_migrates_mid_process_is_noticed_at_the_next_login(
            self, client, server, ropc_kwargs, default_token_url,
            token_response_factory, publishes):
        server.respond("POST", default_token_url,
                       json_body=token_response_factory(refresh_token=None))
        client.make(**ropc_kwargs)
        assert client.login() is True
        client._client.auth_expires = pytz.utc.localize(datetime.min)

        publishes(AUTH0_ISSUER)

        with pytest.raises(ERClientBadCredentials):
            client.auth_headers()

    def test_discovery_false_keeps_the_client_off_the_network(
            self, client, server, ropc_kwargs, discovery_url,
            default_token_url, token_response, publishes):
        publishes(AUTH0_ISSUER)
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(**ropc_kwargs, discovery=False)

        assert client.login() is True
        assert ("GET", discovery_url) not in server.calls
