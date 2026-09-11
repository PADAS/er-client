"""What the site's discovery document says about the credentials a caller
brought. A password grant it cannot honour is refused before it is posted; a
token it does not list is warned about and sent anyway, for the server to
judge."""
import contextlib
from datetime import datetime

import pytest
import pytz
from tests.auth.conftest import Reply, auth_warnings, jwt_for

from erclient.er_errors import ERClientAuthWarning, ERClientBadCredentials

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
def das_issuer(service_root):
    return f"{service_root}/oauth2"


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


class TestATokenTheSiteDoesNotList:

    def test_a_legacy_token_at_a_site_that_has_finished_migrating(
            self, client, service_root, token_kwargs, publishes):
        publishes(AUTH0_ISSUER)
        client.make(**token_kwargs)

        with pytest.warns(ERClientAuthWarning) as record:
            headers = client.auth_headers()

        assert str(record[0].message) == (
            "The token passed with token= looks like a legacy "
            f"EarthRanger-issued token, but site {service_root} lists only "
            "Auth0 issuers. Use an Auth0-issued access token, or construct "
            "the client with no credentials and call login() to sign in "
            "interactively."
        )
        assert headers["Authorization"].startswith("Bearer ")

    def test_a_jwt_from_an_issuer_the_site_does_not_list(
            self, client, service_root, publishes, das_issuer):
        other = "https://auth.example.com"
        publishes(das_issuer, AUTH0_ISSUER)
        client.make(service_root=service_root, token=jwt_for(other))

        with pytest.warns(ERClientAuthWarning) as record:
            headers = client.auth_headers()

        assert str(record[0].message) == (
            f"The token passed with token= was issued by {other}, which site "
            f"{service_root} does not list among the issuers it accepts: "
            f"{das_issuer}, {AUTH0_ISSUER}."
        )
        assert headers["Authorization"].startswith("Bearer ")

    def test_the_server_is_left_to_judge_its_own_tokens(
            self, client, token_kwargs, publishes):
        publishes(AUTH0_ISSUER)
        client.make(**token_kwargs)

        with pytest.warns(ERClientAuthWarning):
            client.auth_headers()

        # Nothing was refused, so there is no refusal to report.
        assert client._last_auth_error is None

    def test_it_is_said_once_however_many_requests_follow(
            self, client, server, discovery_url, token_kwargs, publishes):
        publishes(AUTH0_ISSUER)
        client.make(**token_kwargs)

        with pytest.warns(ERClientAuthWarning) as record:
            for _ in range(3):
                client.auth_headers()

        assert len(auth_warnings(record.list)) == 1
        assert server.calls.count(("GET", discovery_url)) == 1


class TestATokenTheSiteCanAccept:

    @pytest.mark.parametrize("listed", [
        AUTH0_ISSUER,
        f"{AUTH0_ISSUER}/",
        "https://AUTH-DEV.PAMDAS.ORG",
    ])
    def test_a_jwt_from_a_listed_issuer_is_compared_normalized(
            self, client, service_root, publishes, listed):
        publishes(listed)
        client.make(service_root=service_root, token=jwt_for(AUTH0_ISSUER))

        assert client.auth_headers()["Authorization"] == (
            f"Bearer {jwt_for(AUTH0_ISSUER)}")

    def test_a_jwt_with_no_readable_issuer_is_left_to_the_server(
            self, client, service_root, publishes):
        publishes(AUTH0_ISSUER)
        client.make(service_root=service_root,
                    token="eyJhbGciOiAiUlMyNTYifQ.bm90LWpzb24.SIG")

        assert client.auth_headers()["Authorization"].startswith("Bearer ")

    @pytest.mark.parametrize("published,deprecated", [
        (("https://fake-site.erdomain.org/oauth2",), False),
        (("https://fake-site.erdomain.org/oauth2", AUTH0_ISSUER), True),
        ((), False),
    ])
    def test_a_legacy_token_while_the_site_still_lists_its_own_issuer(
            self, client, token_kwargs, publishes, recwarn, published,
            deprecated):
        publishes(*published)
        client.make(**token_kwargs)

        assert client.auth_headers()["Authorization"].startswith("Bearer ")
        assert bool(auth_warnings(recwarn.list)) is deprecated

    def test_a_site_serving_no_document_is_no_evidence(self, client,
                                                       token_kwargs):
        client.make(**token_kwargs)

        assert client.auth_headers()["Authorization"].startswith("Bearer ")


class TestWhenTokenModeAsksTheSite:

    def test_once_only_however_many_requests_follow(
            self, client, server, discovery_url, token_kwargs, publishes,
            das_issuer):
        publishes(das_issuer)
        client.make(**token_kwargs)

        for _ in range(3):
            client.auth_headers()

        assert server.calls.count(("GET", discovery_url)) == 1

    def test_not_at_construction(self, client, server, token_kwargs,
                                 publishes):
        publishes(AUTH0_ISSUER)

        client.make(**token_kwargs)

        assert server.traffic == []

    def test_not_at_all_when_discovery_is_off(self, client, server,
                                              token_kwargs, publishes):
        publishes(AUTH0_ISSUER)
        client.make(**token_kwargs, discovery=False)

        assert client.auth_headers()["Authorization"].startswith("Bearer ")
        assert server.traffic == []


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
