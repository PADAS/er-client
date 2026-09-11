"""What both clients do today at construction time and on their lazy auth
paths. Assertions describe current behavior, warts included."""
from datetime import datetime, timezone

import httpx
import pytest
import pytz
import requests
from tests.auth.conftest import Reply

from erclient.er_errors import ERClientException
from erclient.version import __version__


class TestConstruction:

    @pytest.mark.parametrize("kwargs_name", ["ropc_kwargs", "token_kwargs"])
    def test_issues_no_request(self, request, client, server, kwargs_name):
        client.make(**request.getfixturevalue(kwargs_name))

        assert server.traffic == []

    def test_unknown_kwargs_are_silently_ignored(self, client, service_root):
        client.make(service_root=service_root, not_a_real_option="whatever")

        assert not hasattr(client._client, "not_a_real_option")

    def test_a_positional_argument_is_rejected(self, client, service_root):
        with pytest.raises(TypeError):
            client.make(service_root)

    def test_credentials_are_stored_as_given(self, client, service_root):
        client.make(service_root=service_root, username="a-user",
                    password="a-password", client_id="a-client-id",
                    provider_key="a-provider-key",
                    realtime_url="https://realtime.erdomain.org")

        assert client.username == "a-user"
        assert client.password == "a-password"
        assert client.client_id == "a-client-id"
        assert client.provider_key == "a-provider-key"
        assert client.realtime_url == "https://realtime.erdomain.org"
        assert client.user_agent == f"das-client/{__version__}"

    def test_omitted_credentials_default_to_none(self, client, service_root):
        client.make(service_root=service_root)

        assert client.username is None
        assert client.password is None
        assert client.client_id is None
        assert client.auth is None


class TestTokenUrl:

    def test_without_a_service_root_it_is_not_a_usable_url(self, client):
        client.make()

        assert client.service_root == ""
        assert client.token_url == "/oauth2/token"  # wart

    @pytest.mark.parametrize("service_root_input", [
        "https://example.com",
        "https://example.com/",
        "https://example.com/api",
        "https://example.com/api/",
        "https://example.com/api/v1.0",
        "https://example.com/api/v2.0",
    ])
    def test_derives_from_the_normalized_service_root(self, client,
                                                      service_root_input):
        client.make(service_root=service_root_input)

        assert client.token_url == "https://example.com/oauth2/token"

    def test_an_explicit_value_is_used_verbatim(self, client, service_root,
                                                custom_token_url):
        client.make(service_root=service_root, token_url=custom_token_url)

        assert client.token_url == custom_token_url


class TestSuppliedToken:
    """token= mode: auth is complete at construction and never refreshed."""

    def test_is_wrapped_as_bearer_auth_that_never_expires(self, client,
                                                          token_kwargs):
        client.make(**token_kwargs)

        assert client.auth == {"token_type": "Bearer",
                               "access_token": token_kwargs["token"]}
        assert client.auth_expires == datetime(2099, 1, 1, tzinfo=pytz.utc)

    def test_repeated_auth_headers_ask_the_token_endpoint_for_nothing(
            self, client, server, token_kwargs):
        client.make(**token_kwargs)

        for _ in range(3):
            headers = client.auth_headers()

        assert headers == {
            "Authorization": f"Bearer {token_kwargs['token']}",
            "Accept-Type": "application/json",
        }
        assert server.traffic == []

    def test_it_wins_over_a_username_and_password(self, client, server,
                                                  ropc_kwargs, token_kwargs):
        client.make(**{**ropc_kwargs, **token_kwargs})

        headers = client.auth_headers()

        assert headers["Authorization"] == f"Bearer {token_kwargs['token']}"
        assert server.traffic == []
        assert client.username == ropc_kwargs["username"]

    def test_an_empty_token_is_no_token_at_all(self, client, service_root):
        client.make(service_root=service_root, token="")

        assert client.auth is None


class TestPasswordGrant:
    """ROPC mode: nothing happens until the first request needs headers."""

    def test_construction_acquires_nothing(self, client, ropc_kwargs):
        client.make(**ropc_kwargs)

        assert client.auth is None
        assert client.auth_expires == pytz.utc.localize(datetime.min)

    def test_posts_exactly_the_password_payload(self, client, server,
                                                ropc_kwargs, default_token_url,
                                                token_response):
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(**ropc_kwargs)

        client.auth_headers()

        assert server.calls == [("POST", default_token_url)]
        assert server.traffic[0].data == {
            "grant_type": "password",
            "username": ropc_kwargs["username"],
            "password": ropc_kwargs["password"],
            "client_id": ropc_kwargs["client_id"],
        }

    def test_a_custom_token_url_receives_it_instead(self, client, server,
                                                    ropc_kwargs,
                                                    custom_token_url,
                                                    token_response):
        server.respond("POST", custom_token_url, json_body=token_response)
        client.make(**ropc_kwargs, token_url=custom_token_url)

        client.auth_headers()

        assert server.calls == [("POST", custom_token_url)]

    @pytest.mark.parametrize("expires_in", [3600, "3600"])
    def test_the_whole_response_is_stored_with_a_derived_expiry(
            self, client, server, ropc_kwargs, default_token_url,
            token_response_factory, assert_expiry_matches, expires_in):
        body = token_response_factory(expires_in=expires_in)
        server.respond("POST", default_token_url, json_body=body)
        client.make(**ropc_kwargs)

        client.auth_headers()

        assert client.auth == body
        assert_expiry_matches(client.auth_expires, expires_in)

    def test_the_authorization_header_uses_the_response_token_type(
            self, client, server, ropc_kwargs, default_token_url,
            token_response_factory):
        body = token_response_factory(token_type="MAC", access_token="abc123")
        server.respond("POST", default_token_url, json_body=body)
        client.make(**ropc_kwargs)

        assert client.auth_headers()["Authorization"] == "MAC abc123"

    def test_login_reports_success(self, client, server, ropc_kwargs,
                                   default_token_url, token_response):
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(**ropc_kwargs)

        assert client.login() is True
        assert client.auth == token_response

    def test_a_live_token_is_reused(self, client, server, ropc_kwargs,
                                    default_token_url, token_response):
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(**ropc_kwargs)

        client.auth_headers()
        client.auth_headers()

        assert len(server.traffic) == 1

    def test_an_expired_token_is_refreshed_without_a_password_grant(
            self, client, server, ropc_kwargs, default_token_url,
            token_response_factory):
        server.script(
            "POST", default_token_url,
            Reply(json_body=token_response_factory()),
            Reply(json_body=token_response_factory(
                access_token="access-token-2")))
        client.make(**ropc_kwargs)

        client.auth_headers()
        client._client.auth_expires = pytz.utc.localize(datetime.min)
        headers = client.auth_headers()

        assert server.traffic[1].data == {
            "grant_type": "refresh_token",
            "refresh_token": "refresh-token-1",
            "client_id": ropc_kwargs["client_id"],
        }
        assert headers["Authorization"] == "Bearer access-token-2"

    def test_a_refused_refresh_is_where_the_two_clients_part_company(
            self, client, server, ropc_kwargs, default_token_url,
            token_response_factory):
        server.script(
            "POST", default_token_url,
            Reply(json_body=token_response_factory()),
            Reply(401, json_body={"error": "invalid_grant"}),
            Reply(json_body=token_response_factory(
                access_token="access-token-3")))
        client.make(**ropc_kwargs)

        client.auth_headers()
        client._client.auth_expires = pytz.utc.localize(datetime.min)

        if client.kind == "sync":
            headers = client.auth_headers()

            assert [call.data["grant_type"] for call in server.traffic] == [
                "password", "refresh_token", "password"]
            assert headers["Authorization"] == "Bearer access-token-3"
        else:
            # wart: the async client raises instead of trying the password
            # grant, so a session that outlives its refresh token cannot
            # recover the way the sync one does.
            with pytest.raises(httpx.HTTPStatusError):
                client.auth_headers()

    def test_a_token_without_a_refresh_token_expires_into_a_password_grant(
            self, client, server, ropc_kwargs, default_token_url,
            token_response_factory):
        server.script(
            "POST", default_token_url,
            Reply(json_body=token_response_factory(refresh_token=None)),
            Reply(json_body=token_response_factory(
                access_token="access-token-2", refresh_token=None)))
        client.make(**ropc_kwargs)

        client.auth_headers()
        client._client.auth_expires = pytz.utc.localize(datetime.min)
        headers = client.auth_headers()

        assert [call.data["grant_type"] for call in server.traffic] == [
            "password", "password"]
        assert headers["Authorization"] == "Bearer access-token-2"

    def test_refresh_token_with_none_to_send_reports_that_and_asks_nothing(
            self, client, server, ropc_kwargs, default_token_url,
            token_response_factory):
        body = token_response_factory(refresh_token=None)
        server.respond("POST", default_token_url, json_body=body)
        client.make(**ropc_kwargs)
        client.login()

        assert client.call(client.refresh_token) is False
        assert len(server.traffic) == 1
        assert client.auth == body

    def test_auth_is_valid_tracks_the_recorded_expiry(self, client,
                                                      token_kwargs):
        client.make(**token_kwargs)

        assert client._auth_is_valid() is True

        client._client.auth_expires = datetime.now(tz=timezone.utc)
        assert client._auth_is_valid() is False


class TestARefusedLogin:

    def test_clears_whatever_was_in_hand(self, client, server, ropc_kwargs,
                                         default_token_url):
        server.respond("POST", default_token_url, 401, text="nope")
        client.make(**ropc_kwargs)

        with pytest.raises((ERClientException, httpx.HTTPStatusError)):
            client.auth_headers()

        assert client.auth is None
        assert client.auth_expires == pytz.utc.localize(datetime.min)

    def test_is_reported_as_a_bool_or_an_httpx_error(self, client, server,
                                                     ropc_kwargs,
                                                     default_token_url):
        server.respond("POST", default_token_url, 401, text="nope")
        client.make(**ropc_kwargs)

        if client.kind == "sync":
            assert client.login() is False
        else:
            # wart: a caller of the async login() sees the httpx error raw.
            with pytest.raises(httpx.HTTPStatusError):
                client.login()


class TestNoCredentials:
    """Nothing was supplied, so a password grant of nothing is posted."""

    def test_posts_a_password_grant_with_no_credentials_in_it(
            self, client, server, service_root, default_token_url):
        server.respond("POST", default_token_url, 401, text="nope")
        client.make(service_root=service_root)

        with pytest.raises((ERClientException, httpx.HTTPStatusError)):
            client.auth_headers()

        # wart: nothing to authenticate with, and the site is asked anyway.
        assert server.traffic[0].data == {"grant_type": "password"}

    def test_requests_drops_the_none_valued_fields_the_payload_above_relies_on(
            self, default_token_url):
        prepared = requests.Request(
            "POST", default_token_url,
            data={"grant_type": "password", "username": None,
                  "password": None, "client_id": None}).prepare()

        assert prepared.body == "grant_type=password"
