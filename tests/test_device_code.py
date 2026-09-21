"""The device-code tables and parsers. Everything here is a pure function that
must never raise, whatever an authorization server sends."""
import json

import pytest

from erclient.device_code import (DEFAULT_POLL_INTERVAL_SECONDS,
                                  KNOWN_AUTHORIZATION_SERVERS,
                                  authorization_server_metadata_url,
                                  default_prompt_text, is_https_url,
                                  parse_authorization_server_metadata,
                                  parse_device_authorization,
                                  parse_token_response,
                                  select_authorization_server)
from erclient.discovery import parse_protected_resource_metadata

SITE = "https://fake-site.erdomain.org"
DAS_ISSUER = f"{SITE}/oauth2"
KNOWN_ISSUER = "https://auth-dev.pamdas.org"
OTHER_ISSUER = "https://auth.example.com"


def metadata(*authorization_servers):
    return parse_protected_resource_metadata(
        json.dumps({"resource": SITE,
                    "authorization_servers": list(authorization_servers)}),
        SITE)


def as_document(issuer=KNOWN_ISSUER, **overrides):
    document = {
        "issuer": issuer,
        "device_authorization_endpoint": f"{issuer}/oauth/device/code",
        "token_endpoint": f"{issuer}/oauth/token",
    }
    document.update(overrides)
    return json.dumps({k: v for k, v in document.items() if v is not None})


def authorization_document(**overrides):
    document = {
        "device_code": "device-code-1",
        "user_code": "WDJB-MJHT",
        "verification_uri": f"{KNOWN_ISSUER}/activate",
        "verification_uri_complete": f"{KNOWN_ISSUER}/activate?user_code=WDJB-MJHT",
        "expires_in": 900,
        "interval": 5,
    }
    document.update(overrides)
    return json.dumps({k: v for k, v in document.items() if v is not None})


def token_document(**overrides):
    document = {
        "access_token": "access-token-1",
        "token_type": "Bearer",
        "expires_in": 172800,
        "scope": "openid profile email",
    }
    document.update(overrides)
    return json.dumps({k: v for k, v in document.items() if v is not None})


class TestSelectAuthorizationServer:

    @pytest.mark.parametrize("listed", [
        KNOWN_ISSUER,
        f"{KNOWN_ISSUER}/",
        "https://AUTH-DEV.PAMDAS.ORG",
    ])
    def test_finds_the_registration_for_a_tenant_we_know(self, listed):
        server = select_authorization_server(metadata(DAS_ISSUER, listed))

        assert server is KNOWN_AUTHORIZATION_SERVERS[KNOWN_ISSUER]

    def test_takes_the_first_one_the_site_lists(self):
        server = select_authorization_server(
            metadata("https://auth.pamdas.org", KNOWN_ISSUER))

        assert server.issuer == "https://auth.pamdas.org"

    @pytest.mark.parametrize("listed", [(), (DAS_ISSUER,),
                                        (DAS_ISSUER, OTHER_ISSUER)])
    def test_a_site_naming_no_tenant_we_know_selects_nothing(self, listed):
        assert select_authorization_server(metadata(*listed)) is None

    def test_no_metadata_selects_nothing(self):
        assert select_authorization_server(None) is None

    def test_every_registration_is_keyed_by_its_own_issuer(self):
        for key, server in KNOWN_AUTHORIZATION_SERVERS.items():
            assert server.issuer == key
            assert is_https_url(key)
            assert server.client_id and server.audience


class TestAuthorizationServerMetadataUrl:

    @pytest.mark.parametrize("issuer", [KNOWN_ISSUER, f"{KNOWN_ISSUER}/"])
    def test_appends_the_well_known_path_to_the_normalized_issuer(self, issuer):
        assert authorization_server_metadata_url(issuer) == (
            f"{KNOWN_ISSUER}/.well-known/openid-configuration")


class TestIsHttpsUrl:

    def test_accepts_an_absolute_https_url(self):
        assert is_https_url("https://auth-dev.pamdas.org/oauth/token") is True

    @pytest.mark.parametrize("value", [
        "http://auth-dev.pamdas.org/oauth/token",
        "auth-dev.pamdas.org",
        "/oauth/token",
        "https://",
        "",
        None,
        42,
    ])
    def test_rejects_anything_else(self, value):
        assert is_https_url(value) is False


class TestParseAuthorizationServerMetadata:

    def test_reads_the_two_endpoints(self):
        assert parse_authorization_server_metadata(
            as_document(), KNOWN_ISSUER) == (
            f"{KNOWN_ISSUER}/oauth/device/code",
            f"{KNOWN_ISSUER}/oauth/token")

    def test_the_issuer_is_compared_normalized(self):
        assert parse_authorization_server_metadata(
            as_document(issuer=f"{KNOWN_ISSUER}/"), KNOWN_ISSUER) is not None

    def test_a_document_naming_another_issuer_is_refused(self):
        document = as_document(issuer="https://er-dev.us.auth0.com")

        assert parse_authorization_server_metadata(
            document, KNOWN_ISSUER) is None

    @pytest.mark.parametrize("overrides", [
        {"issuer": None},
        {"issuer": 42},
        {"device_authorization_endpoint": None},
        {"token_endpoint": None},
        {"device_authorization_endpoint":
            f"http://{KNOWN_ISSUER[8:]}/oauth/device/code"},
        {"token_endpoint": "/oauth/token"},
        {"token_endpoint": 42},
    ])
    def test_a_document_we_could_not_post_to_is_no_document(self, overrides):
        assert parse_authorization_server_metadata(
            as_document(**overrides), KNOWN_ISSUER) is None

    @pytest.mark.parametrize("text", ["", "not json", "[]", "null", None])
    def test_a_body_that_is_not_a_json_object_is_no_document(self, text):
        assert parse_authorization_server_metadata(text, KNOWN_ISSUER) is None


class TestParseDeviceAuthorization:

    def test_reads_the_whole_response(self):
        authorization = parse_device_authorization(authorization_document())

        assert authorization.device_code == "device-code-1"
        assert authorization.user_code == "WDJB-MJHT"
        assert authorization.verification_uri == f"{KNOWN_ISSUER}/activate"
        assert authorization.verification_uri_complete == (
            f"{KNOWN_ISSUER}/activate?user_code=WDJB-MJHT")
        assert authorization.expires_in == 900
        assert authorization.interval == 5

    @pytest.mark.parametrize("interval", [None, 0, -1, "5", True, 1.5])
    def test_an_interval_it_cannot_wait_for_falls_back_to_the_default(
            self, interval):
        authorization = parse_device_authorization(
            authorization_document(interval=interval))

        assert authorization.interval == DEFAULT_POLL_INTERVAL_SECONDS

    @pytest.mark.parametrize("expires_in", [None, 0, -1, "900", True])
    def test_a_lifetime_it_cannot_poll_within_fails_the_response(self,
                                                                 expires_in):
        assert parse_device_authorization(
            authorization_document(expires_in=expires_in)) is None

    @pytest.mark.parametrize("overrides", [
        {"device_code": None},
        {"device_code": ""},
        {"user_code": None},
        {"verification_uri": None},
        {"verification_uri": f"http://{KNOWN_ISSUER[8:]}/activate"},
        {"verification_uri": "/activate"},
    ])
    def test_a_response_the_user_could_not_act_on_is_no_response(self,
                                                                 overrides):
        assert parse_device_authorization(
            authorization_document(**overrides)) is None

    @pytest.mark.parametrize("complete", [None, "http://insecure/activate", 42])
    def test_an_unusable_complete_uri_is_dropped_not_fatal(self, complete):
        authorization = parse_device_authorization(
            authorization_document(verification_uri_complete=complete))

        assert authorization.verification_uri_complete is None

    @pytest.mark.parametrize("text", ["", "not json", "[]", None])
    def test_a_body_that_is_not_a_json_object_is_no_response(self, text):
        assert parse_device_authorization(text) is None


class TestParseTokenResponse:

    def test_returns_the_body_it_was_given(self):
        token = parse_token_response(token_document())

        assert token["access_token"] == "access-token-1"
        assert token["token_type"] == "Bearer"
        assert token["expires_in"] == 172800
        assert token["scope"] == "openid profile email"

    def test_drops_a_refresh_token_the_tenant_sent_anyway(self):
        token = parse_token_response(
            token_document(refresh_token="refresh-token-1"))

        assert "refresh_token" not in token

    @pytest.mark.parametrize("overrides", [
        {"access_token": None},
        {"access_token": ""},
        {"access_token": 42},
        {"token_type": None},
        {"expires_in": None},
        {"expires_in": 0},
        {"expires_in": "172800"},
        {"expires_in": True},
    ])
    def test_a_body_the_client_could_not_use_is_no_token(self, overrides):
        assert parse_token_response(token_document(**overrides)) is None

    @pytest.mark.parametrize("text", ["", "not json", "[]", None])
    def test_a_body_that_is_not_a_json_object_is_no_token(self, text):
        assert parse_token_response(text) is None


class TestDefaultPromptText:

    def test_names_the_site_the_url_and_the_code(self):
        authorization = parse_device_authorization(authorization_document())

        text = default_prompt_text(service_root=SITE,
                                   authorization=authorization)

        assert SITE in text
        assert authorization.verification_uri_complete in text
        assert "WDJB-MJHT" in text

    def test_falls_back_to_the_bare_verification_uri(self):
        authorization = parse_device_authorization(
            authorization_document(verification_uri_complete=None))

        text = default_prompt_text(service_root=SITE,
                                   authorization=authorization)

        assert f"{KNOWN_ISSUER}/activate" in text
