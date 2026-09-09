"""Unit tests for the device-code module: tables, parsers, and the prompt.

Pure functions only — the clients own the HTTP, as with ``discovery.py``.

Two things here are load-bearing beyond their apparent size. The known-tenant
table keys on the *custom domain* an EarthRanger site advertises, never on the
canonical ``*.auth0.com`` name, because EarthRanger validates a token's ``iss``
against exactly the string discovery serves. And every parser answers an
unusable document with ``None`` rather than an exception, so a caller decides
what a malformed authorization server deserves.
"""
import json

import pytest

from erclient import (KNOWN_AUTHORIZATION_SERVERS, AuthorizationServer,
                      DeviceAuthorization)
from erclient.device_code import (DEFAULT_POLL_INTERVAL_SECONDS, DEFAULT_SCOPE,
                                  DEVICE_CODE_GRANT,
                                  authorization_server_metadata_url,
                                  default_prompt_text, is_https_url,
                                  is_issuer_url,
                                  parse_authorization_server_metadata,
                                  parse_device_authorization,
                                  parse_token_response,
                                  select_authorization_server)
from erclient.discovery import ProtectedResourceMetadata

DEV_ISSUER = "https://auth-dev.pamdas.org"
PROD_ISSUER = "https://auth.pamdas.org"
SERVICE_ROOT = "https://fake-site.erdomain.org"
DAS_ISSUER = f"{SERVICE_ROOT}/oauth2"
OTHER_ISSUER = "https://someone-elses-tenant.us.auth0.com"


def metadata_listing(*issuers):
    """Metadata for a site that lists exactly these authorization servers."""
    return ProtectedResourceMetadata(
        resource=SERVICE_ROOT, authorization_servers=tuple(issuers), raw={})


class TestKnownAuthorizationServers:
    """The registrations, as supplied by the Auth0 tenant's owners."""

    def test_the_dev_tenant(self):
        server = KNOWN_AUTHORIZATION_SERVERS[DEV_ISSUER]

        assert server.issuer == DEV_ISSUER
        assert server.client_id == "tpPAukxw0S8MXwZPcK6hwIEcqM0cAp5l"
        assert server.audience == "https://dev.pamdas.org/api"

    def test_the_prod_tenant(self):
        server = KNOWN_AUTHORIZATION_SERVERS[PROD_ISSUER]

        assert server.issuer == PROD_ISSUER
        assert server.client_id == "JMzSKHVrOVjFYC6KjeONw9ZToPRw56uZ"
        assert server.audience == "https://pamdas.org/api"

    def test_the_table_holds_only_those_two(self):
        assert set(KNOWN_AUTHORIZATION_SERVERS) == {DEV_ISSUER, PROD_ISSUER}

    def test_keys_and_issuers_are_stored_normalized(self):
        """Discovery advertises a trailing slash; lookups normalize, so the table must not."""
        for key, server in KNOWN_AUTHORIZATION_SERVERS.items():
            assert key == server.issuer
            assert not key.endswith("/")

    def test_no_canonical_auth0_hostname_appears(self):
        """A token minted at *.auth0.com carries an iss EarthRanger rejects."""
        for key, server in KNOWN_AUTHORIZATION_SERVERS.items():
            assert "auth0.com" not in key
            assert "auth0.com" not in server.audience

    def test_the_grant_and_scope_constants(self):
        assert DEVICE_CODE_GRANT == "urn:ietf:params:oauth:grant-type:device_code"
        # No offline_access: the registration issues no refresh token.
        assert DEFAULT_SCOPE == "openid profile email"


class TestSelectFromDiscovery:
    """Without an override, the site's own list picks the tenant."""

    def test_the_dev_tenant_among_others(self):
        """A migrating site lists its own issuer first; the Auth0 one is what we want."""
        server = select_authorization_server(
            metadata_listing(DAS_ISSUER, f"{DEV_ISSUER}/"))

        assert server == KNOWN_AUTHORIZATION_SERVERS[DEV_ISSUER]

    def test_a_trailing_slash_still_matches(self):
        """Discovery serves the slash form, and that is the only form it serves."""
        server = select_authorization_server(
            metadata_listing(f"{DEV_ISSUER}/"))

        assert server.client_id == "tpPAukxw0S8MXwZPcK6hwIEcqM0cAp5l"

    def test_host_case_still_matches(self):
        server = select_authorization_server(
            metadata_listing("https://AUTH-DEV.PAMDAS.ORG/"))

        assert server == KNOWN_AUTHORIZATION_SERVERS[DEV_ISSUER]

    def test_the_prod_tenant(self):
        server = select_authorization_server(
            metadata_listing(DAS_ISSUER, f"{PROD_ISSUER}/"))

        assert server == KNOWN_AUTHORIZATION_SERVERS[PROD_ISSUER]

    def test_the_first_known_issuer_wins(self):
        """Nothing sensible orders two known tenants; take the site's own order."""
        server = select_authorization_server(
            metadata_listing(f"{PROD_ISSUER}/", f"{DEV_ISSUER}/"))

        assert server == KNOWN_AUTHORIZATION_SERVERS[PROD_ISSUER]

    def test_a_site_listing_only_its_own_issuer(self):
        assert select_authorization_server(
            metadata_listing(DAS_ISSUER)) is None

    def test_a_tenant_we_do_not_know(self):
        """Someone else's Auth0 tenant needs the overrides, not a guess."""
        assert select_authorization_server(
            metadata_listing(OTHER_ISSUER)) is None

    def test_no_metadata_at_all(self):
        assert select_authorization_server(None) is None

    def test_a_site_listing_nothing(self):
        assert select_authorization_server(metadata_listing()) is None

    def test_an_override_applies_to_the_discovered_tenant(self):
        """A caller testing against the dev tenant with their own registration."""
        server = select_authorization_server(
            metadata_listing(f"{DEV_ISSUER}/"), client_id="other-client")

        assert server.issuer == DEV_ISSUER
        assert server.client_id == "other-client"
        assert server.audience == "https://dev.pamdas.org/api"


class TestSelectFromAnIssuerOverride:
    """An explicit issuer settles it, whatever discovery said."""

    def test_a_known_issuer_beats_the_metadata(self):
        server = select_authorization_server(
            metadata_listing(f"{PROD_ISSUER}/"), issuer=f"{DEV_ISSUER}/")

        assert server == KNOWN_AUTHORIZATION_SERVERS[DEV_ISSUER]

    def test_a_known_issuer_without_any_metadata(self):
        server = select_authorization_server(None, issuer=DEV_ISSUER)

        assert server == KNOWN_AUTHORIZATION_SERVERS[DEV_ISSUER]

    def test_a_new_tenant_needs_a_client_id_and_an_audience(self):
        server = select_authorization_server(
            None, issuer=f"{OTHER_ISSUER}/", client_id="new-client",
            audience="https://new.example.org/api")

        assert server == AuthorizationServer(
            issuer=OTHER_ISSUER, client_id="new-client",
            audience="https://new.example.org/api")

    @pytest.mark.parametrize(
        "overrides",
        [{}, {"client_id": "new-client"},
         {"audience": "https://new.example.org/api"}],
        ids=["neither", "client_id_only", "audience_only"],
    )
    def test_an_unknown_tenant_missing_either_one(self, overrides):
        """Half a registration cannot start a flow, so say so rather than guess."""
        assert select_authorization_server(
            None, issuer=OTHER_ISSUER, **overrides) is None

    def test_overrides_apply_to_a_known_issuer_too(self):
        server = select_authorization_server(
            None, issuer=DEV_ISSUER, client_id="other-client",
            audience="https://other.example.org/api")

        assert server == AuthorizationServer(
            issuer=DEV_ISSUER, client_id="other-client",
            audience="https://other.example.org/api")

    @pytest.mark.parametrize(
        "issuer",
        ["http://auth-dev.pamdas.org", "http://someone-elses-tenant.us.auth0.com",
         "someone-elses-tenant.us.auth0.com", "https://[broken",
         f"{DEV_ISSUER}?tenant=x", f"{OTHER_ISSUER}?tenant=x",
         f"{OTHER_ISSUER}#fragment"],
        ids=["known_tenant_over_http", "new_tenant_over_http", "no_scheme",
             "malformed", "known_tenant_with_query", "new_tenant_with_query",
             "new_tenant_with_fragment"],
    )
    def test_an_issuer_that_is_not_an_issuer_url_selects_nothing(self, issuer):
        """The metadata document names where credentials go, so it is fetched
        over https from a URL the well-known path can be appended to, or not at
        all — even for a tenant the table knows, and even with the full
        registration supplied."""
        assert select_authorization_server(
            None, issuer=issuer, client_id="new-client",
            audience="https://new.example.org/api") is None


class TestIsIssuerUrl:
    """RFC 8414 section 2: https, and nothing after the path."""

    @pytest.mark.parametrize(
        "value", [DEV_ISSUER, f"{DEV_ISSUER}/", "HTTPS://AUTH-DEV.PAMDAS.ORG",
                  f"{DEV_ISSUER}:8443/tenant"],
        ids=["bare", "trailing_slash", "upper_case", "with_port_and_path"],
    )
    def test_issuer_identifiers(self, value):
        assert is_issuer_url(value) is True

    @pytest.mark.parametrize(
        "value",
        ["http://auth-dev.pamdas.org", f"{DEV_ISSUER}?tenant=x",
         f"{DEV_ISSUER}?", f"{DEV_ISSUER}#fragment", f"{DEV_ISSUER}/#",
         "auth-dev.pamdas.org", "", None, "https://[broken"],
        ids=["plain_http", "query", "empty_query_marker", "fragment",
             "empty_fragment_marker", "no_scheme", "empty", "none",
             "malformed"],
    )
    def test_everything_else(self, value):
        assert is_issuer_url(value) is False


class TestIsHttpsUrl:
    """The bar for every URL the flow touches."""

    @pytest.mark.parametrize(
        "value", [DEV_ISSUER, f"{DEV_ISSUER}/", "HTTPS://AUTH-DEV.PAMDAS.ORG",
                  f"{DEV_ISSUER}:8443/oauth/token"],
        ids=["bare", "trailing_slash", "upper_case", "with_port_and_path"],
    )
    def test_absolute_https_urls(self, value):
        assert is_https_url(value) is True

    @pytest.mark.parametrize(
        "value",
        ["http://auth-dev.pamdas.org", "auth-dev.pamdas.org", "/oauth/token",
         "https://", "", None, "https://[broken",
         "https://auth-dev.pamdas.org:notaport"],
        ids=["plain_http", "no_scheme", "path_only", "no_host", "empty",
             "none", "malformed_ipv6", "non_numeric_port"],
    )
    def test_everything_else(self, value):
        """The last two make urlparse raise; this must not."""
        assert is_https_url(value) is False


class TestAuthorizationServerMetadataUrl:
    """Where the authorization server describes itself."""

    @pytest.mark.parametrize("issuer", [DEV_ISSUER, f"{DEV_ISSUER}/"])
    def test_one_slash_either_way(self, issuer):
        assert authorization_server_metadata_url(issuer) == (
            "https://auth-dev.pamdas.org/.well-known/openid-configuration")


def as_metadata(issuer=f"{DEV_ISSUER}/", **overrides):
    """An OIDC discovery document as Auth0 serves it, pared to what we read."""
    document = {
        "issuer": issuer,
        "device_authorization_endpoint": f"{DEV_ISSUER}/oauth/device/code",
        "token_endpoint": f"{DEV_ISSUER}/oauth/token",
        "jwks_uri": f"{DEV_ISSUER}/.well-known/jwks.json",
    }
    document.update(overrides)
    return json.dumps({k: v for k, v in document.items() if v is not None})


class TestParseAuthorizationServerMetadata:
    """RFC 8414 section 3.3: the document must say who it speaks for."""

    def test_the_two_endpoints_we_need(self):
        assert parse_authorization_server_metadata(
            as_metadata(), expected_issuer=DEV_ISSUER) == (
            f"{DEV_ISSUER}/oauth/device/code", f"{DEV_ISSUER}/oauth/token")

    def test_the_issuer_is_compared_normalized(self):
        """The slash we asked with and the slash it answers with need not match."""
        assert parse_authorization_server_metadata(
            as_metadata(issuer=DEV_ISSUER),
            expected_issuer=f"{DEV_ISSUER}/") is not None

    def test_a_document_for_another_issuer_is_refused(self):
        """The canonical Auth0 name would mint tokens EarthRanger then rejects."""
        assert parse_authorization_server_metadata(
            as_metadata(issuer="https://earthranger-dev.us.auth0.com/"),
            expected_issuer=DEV_ISSUER) is None

    @pytest.mark.parametrize(
        "overrides",
        [
            {"issuer": None},
            {"device_authorization_endpoint": None},
            {"token_endpoint": None},
            {"issuer": 7},
            {"device_authorization_endpoint": ""},
            {"token_endpoint": ["not", "a", "string"]},
        ],
        ids=["no_issuer", "no_device_endpoint", "no_token_endpoint",
             "issuer_not_a_string", "empty_device_endpoint",
             "token_endpoint_not_a_string"],
    )
    def test_a_document_missing_what_we_need(self, overrides):
        assert parse_authorization_server_metadata(
            as_metadata(**overrides), expected_issuer=DEV_ISSUER) is None

    @pytest.mark.parametrize(
        "endpoint",
        ["http://auth-dev.pamdas.org/oauth/token",
         "/oauth/token",
         "auth-dev.pamdas.org/oauth/token",
         "https://[broken",
         "https://auth-dev.pamdas.org:notaport/oauth/token",
         "https://auth-dev.pamdas.org/oauth/token#alternate",
         "https://auth-dev.pamdas.org/oauth/token#",
         "https://auth-dev.pamdas.org/oauth/token ",
         "https://auth-dev.pamdas.org/oauth/to\nken"],
        ids=["plain_http", "path_only", "no_scheme", "malformed_ipv6",
             "non_numeric_port", "fragment", "empty_fragment_marker",
             "trailing_space", "embedded_newline"],
    )
    def test_an_endpoint_we_would_not_post_credentials_to(self, endpoint):
        """Malformed ones make urlparse raise; the parser answers None instead.

        A fragment is rejected because the HTTP libraries strip it, so the
        client would post to a different URI than the document names.
        """
        assert parse_authorization_server_metadata(
            as_metadata(token_endpoint=endpoint),
            expected_issuer=DEV_ISSUER) is None
        assert parse_authorization_server_metadata(
            as_metadata(device_authorization_endpoint=endpoint),
            expected_issuer=DEV_ISSUER) is None

    def test_an_endpoint_may_carry_a_query(self):
        """RFC 6749 section 3.2 allows one; only the fragment is ruled out."""
        endpoints = parse_authorization_server_metadata(
            as_metadata(token_endpoint=f"{DEV_ISSUER}/oauth/token?tenant=x"),
            expected_issuer=DEV_ISSUER)

        assert endpoints[1] == f"{DEV_ISSUER}/oauth/token?tenant=x"

    @pytest.mark.parametrize(
        "text",
        ["", "not json at all", "[]", '"a bare string"',
         "<html>404 Not Found</html>", None],
        ids=["empty", "plain_text", "json_array", "json_string", "html",
             "nothing"],
    )
    def test_a_body_that_is_not_a_document(self, text):
        assert parse_authorization_server_metadata(
            text, expected_issuer=DEV_ISSUER) is None


def device_authorization(**overrides):
    """A device-authorization response as RFC 8628 section 3.2 defines it."""
    document = {
        "device_code": "device-code-1",
        "user_code": "WDJB-MJHT",
        "verification_uri": f"{DEV_ISSUER}/activate",
        "verification_uri_complete": f"{DEV_ISSUER}/activate?user_code=WDJB-MJHT",
        "expires_in": 900,
        "interval": 5,
    }
    document.update(overrides)
    return json.dumps({k: v for k, v in document.items() if v is not None})


class TestParseDeviceAuthorization:
    """The response that carries the code the user is about to type."""

    def test_every_field(self):
        authorization = parse_device_authorization(device_authorization())

        assert authorization == DeviceAuthorization(
            device_code="device-code-1",
            user_code="WDJB-MJHT",
            verification_uri=f"{DEV_ISSUER}/activate",
            verification_uri_complete=(
                f"{DEV_ISSUER}/activate?user_code=WDJB-MJHT"),
            expires_in=900,
            interval=5,
        )

    def test_without_the_complete_uri(self):
        """RFC 8628 makes it optional; the user then types the code themselves."""
        authorization = parse_device_authorization(
            device_authorization(verification_uri_complete=None))

        assert authorization.verification_uri_complete is None
        assert authorization.verification_uri == f"{DEV_ISSUER}/activate"

    def test_without_an_interval(self):
        """RFC 8628 section 3.2: five seconds when the server does not say."""
        authorization = parse_device_authorization(
            device_authorization(interval=None))

        assert authorization.interval == DEFAULT_POLL_INTERVAL_SECONDS == 5

    @pytest.mark.parametrize(
        "overrides",
        [
            {"device_code": None},
            {"user_code": None},
            {"verification_uri": None},
            {"expires_in": None},
            {"expires_in": "900"},
            {"device_code": ""},
            {"user_code": 12345},
        ],
        ids=["no_device_code", "no_user_code", "no_verification_uri",
             "no_expires_in", "expires_in_as_a_string", "empty_device_code",
             "user_code_not_a_string"],
    )
    def test_a_response_we_could_not_poll_on(self, overrides):
        assert parse_device_authorization(
            device_authorization(**overrides)) is None

    @pytest.mark.parametrize(
        "text",
        ["", "not json at all", "[]", "<html>500</html>", None],
        ids=["empty", "plain_text", "json_array", "html", "nothing"],
    )
    def test_a_body_that_is_not_a_response(self, text):
        assert parse_device_authorization(text) is None

    def test_a_malformed_optional_field_falls_back_to_its_default(self):
        """An unusable extra is not worth failing a flow we can otherwise run."""
        authorization = parse_device_authorization(
            device_authorization(interval="soon",
                                 verification_uri_complete=42))

        assert authorization.interval == DEFAULT_POLL_INTERVAL_SECONDS
        assert authorization.verification_uri_complete is None

    @pytest.mark.parametrize("interval", [0, -1, -5])
    def test_an_interval_that_is_not_a_wait_falls_back_too(self, interval):
        """Zero is a tight polling loop and a negative one is not a duration."""
        authorization = parse_device_authorization(
            device_authorization(interval=interval))

        assert authorization.interval == DEFAULT_POLL_INTERVAL_SECONDS

    @pytest.mark.parametrize("expires_in", [0, -1])
    def test_a_lifetime_that_has_already_run_out(self, expires_in):
        """A code whose deadline passed before the first poll cannot be polled on."""
        assert parse_device_authorization(
            device_authorization(expires_in=expires_in)) is None

    @pytest.mark.parametrize(
        "verification_uri",
        ["http://example.com/activate", "javascript:alert(1)", "activate"],
        ids=["plain_http", "javascript_scheme", "no_scheme"],
    )
    def test_a_uri_we_would_not_send_a_user_to(self, verification_uri):
        """This one is opened in a browser, so it gets the endpoint check too."""
        assert parse_device_authorization(
            device_authorization(verification_uri=verification_uri)) is None

    def test_a_verification_uri_may_carry_a_fragment(self):
        """Unlike the endpoints: this one is opened in a browser, where a
        fragment means something and is kept."""
        authorization = parse_device_authorization(device_authorization(
            verification_uri=f"{DEV_ISSUER}/activate#top",
            verification_uri_complete=f"{DEV_ISSUER}/activate?user_code=X#top"))

        assert authorization.verification_uri == f"{DEV_ISSUER}/activate#top"
        assert authorization.verification_uri_complete == (
            f"{DEV_ISSUER}/activate?user_code=X#top")

    def test_an_unusable_complete_uri_is_dropped(self):
        """The optional one is a convenience: without it the user types the code."""
        authorization = parse_device_authorization(device_authorization(
            verification_uri_complete="http://example.com/activate?user_code=X"))

        assert authorization.verification_uri_complete is None
        assert authorization.verification_uri == f"{DEV_ISSUER}/activate"


def token_response(**overrides):
    """What the token endpoint returns once the user approves."""
    document = {
        "access_token": "access-token-1",
        "token_type": "Bearer",
        "expires_in": 172800,
        "scope": "openid profile email",
    }
    document.update(overrides)
    return json.dumps({k: v for k, v in document.items() if v is not None})


class TestParseTokenResponse:
    """A 2xx is the flow succeeding; the body still has to be a token."""

    def test_a_usable_response_comes_back_whole(self):
        assert parse_token_response(token_response()) == {
            "access_token": "access-token-1",
            "token_type": "Bearer",
            "expires_in": 172800,
            "scope": "openid profile email",
        }

    def test_a_refresh_token_is_dropped(self):
        """This flow does not refresh; a tenant granting offline_access anyway
        must not leave a credential for the legacy refresh path to post."""
        parsed = parse_token_response(
            token_response(refresh_token="refresh-1"))

        assert "refresh_token" not in parsed
        assert parsed["access_token"] == "access-token-1"

    @pytest.mark.parametrize(
        "overrides",
        [{"access_token": None}, {"access_token": ""},
         {"token_type": None}, {"token_type": ""},
         {"expires_in": None}, {"expires_in": "3600"},
         {"expires_in": 0}, {"expires_in": -1}, {"expires_in": True}],
        ids=["no_token", "empty_token", "no_type", "empty_type",
             "no_lifetime", "lifetime_as_string", "zero_lifetime",
             "negative_lifetime", "boolean_lifetime"],
    )
    def test_a_response_missing_what_the_client_reads(self, overrides):
        """Each of these would have raised, or scheduled nonsense, later."""
        assert parse_token_response(token_response(**overrides)) is None

    @pytest.mark.parametrize(
        "text",
        ["", "not json at all", "[]", '"a bare string"',
         "<html>Approved</html>", None],
        ids=["empty", "plain_text", "json_array", "json_string", "html",
             "nothing"],
    )
    def test_a_body_that_is_not_a_token(self, text):
        """A 204, or a 200 that is a web page, is not a sign-in."""
        assert parse_token_response(text) is None


class TestDefaultPromptText:
    """What the user reads before they go and approve the code."""

    def test_the_three_lines(self):
        text = default_prompt_text(
            service_root=SERVICE_ROOT,
            authorization=parse_device_authorization(device_authorization()))

        assert text == (
            "You are about to authorize the EarthRanger Python Client to "
            f"access {SERVICE_ROOT} as your user.\n"
            f"Open {DEV_ISSUER}/activate?user_code=WDJB-MJHT in a browser and "
            "confirm that it shows the code WDJB-MJHT.\n"
            "Waiting for approval..."
        )

    def test_falls_back_to_the_bare_verification_uri(self):
        """Without the complete URI there is a page to visit and a code to type."""
        text = default_prompt_text(
            service_root=SERVICE_ROOT,
            authorization=parse_device_authorization(
                device_authorization(verification_uri_complete=None)))

        assert f"Open {DEV_ISSUER}/activate in a browser" in text
        assert "WDJB-MJHT" in text


class TestPublicSurface:
    """What a caller can reach without importing a private module."""

    @pytest.mark.parametrize(
        "name",
        ["DEVICE_CODE_GRANT", "KNOWN_AUTHORIZATION_SERVERS",
         "AuthorizationServer", "DeviceAuthorization"],
    )
    def test_is_exported_from_the_package(self, name):
        import erclient

        assert name in erclient.__all__
        assert hasattr(erclient, name)
