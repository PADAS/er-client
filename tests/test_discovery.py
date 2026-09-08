"""Unit tests for the RFC 9728 discovery helpers.

No HTTP here: these are the pure decisions the clients make once a discovery
document is in hand — is it usable, whose authorization servers does it list,
and do the credentials in hand deserve a warning at this site.
"""
import base64
import json

import pytest

from erclient.discovery import (DISCOVERY_PATH, ProtectedResourceMetadata,
                                classify_authorization_servers,
                                credential_site_mismatch, discovery_url,
                                jwt_issuer, legacy_auth_warning,
                                looks_like_jwt, normalize_issuer,
                                parse_absolute_url,
                                parse_protected_resource_metadata)

SERVICE_ROOT = "https://fake-site.erdomain.org"
DAS_ISSUER = "https://fake-site.erdomain.org"
AUTH0_ISSUER = "https://fake-tenant.us.auth0.com"


def make_document(resource=SERVICE_ROOT, authorization_servers=(DAS_ISSUER,), **extra):
    """Serialize a discovery document the way a site would serve it."""
    body = {"resource": resource,
            "authorization_servers": list(authorization_servers)}
    body.update(extra)
    return json.dumps(body)


def b64url(text):
    """Encode a segment the way a JWT does: base64url, padding stripped."""
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def make_jwt(header=None, payload=None):
    """A JWT-shaped string.

    The header is always encoded for real, since that is what
    ``looks_like_jwt`` decodes. The payload is encoded only when one is given;
    otherwise it stays plainly fake, as does the signature, which nothing here
    reads.
    """
    header = {"alg": "RS256", "typ": "JWT"} if header is None else header
    segments = [b64url(json.dumps(header)),
                b64url(json.dumps(payload)) if payload is not None
                else "DUMMY-PAYLOAD",
                "DUMMY-SIGNATURE"]
    return ".".join(segments)


class TestParseAbsoluteUrl:
    """The one place a URL from outside is taken apart, so it must not raise."""

    def test_an_absolute_url(self):
        parsed = parse_absolute_url(
            "https://Fake-Site.erdomain.org:8443/oauth2")

        assert parsed.scheme == "https"
        assert parsed.hostname == "fake-site.erdomain.org"
        assert parsed.port == 8443

    @pytest.mark.parametrize(
        "value",
        ["https://[broken", "https://fake-site.erdomain.org:notaport/oauth2",
         "not a url at all", "fake-site.erdomain.org", "https://", "", None, 42],
        ids=["malformed_ipv6", "non_numeric_port", "prose", "no_scheme",
             "no_host", "empty", "none", "not_a_string"],
    )
    def test_anything_else_is_none(self, value):
        """The first two make urlparse itself raise; none of them may."""
        assert parse_absolute_url(value) is None


class TestDiscoveryUrl:
    """Where the client goes looking for the document."""

    def test_appends_the_well_known_path(self):
        assert discovery_url(
            SERVICE_ROOT) == f"{SERVICE_ROOT}{DISCOVERY_PATH}"

    def test_empty_service_root_has_nowhere_to_go(self):
        """A client built without a service_root skips discovery entirely."""
        assert discovery_url("") is None


class TestParseProtectedResourceMetadata:
    """RFC 9728 section 3.3: the document must claim the resource we asked about."""

    def test_parses_a_well_formed_document(self):
        metadata = parse_protected_resource_metadata(
            make_document(authorization_servers=[DAS_ISSUER, AUTH0_ISSUER]),
            SERVICE_ROOT,
        )

        assert metadata.resource == SERVICE_ROOT
        assert metadata.authorization_servers == (DAS_ISSUER, AUTH0_ISSUER)
        assert metadata.raw["resource"] == SERVICE_ROOT

    def test_keeps_unknown_fields_in_raw(self):
        """Later steps read more of the document than this one does."""
        metadata = parse_protected_resource_metadata(
            make_document(scopes_supported=["read"]), SERVICE_ROOT
        )

        assert metadata.raw["scopes_supported"] == ["read"]

    @pytest.mark.parametrize(
        "resource",
        [
            f"{SERVICE_ROOT}/",
            "https://FAKE-SITE.erdomain.org",
            "HTTPS://fake-site.erdomain.org",
        ],
        ids=["trailing_slash", "host_case", "scheme_case"],
    )
    def test_accepts_cosmetic_differences_in_resource(self, resource):
        metadata = parse_protected_resource_metadata(
            make_document(resource=resource), SERVICE_ROOT)

        assert metadata is not None

    def test_a_plain_http_issuer_is_still_metadata(self):
        """A local development site lists its own http issuer; that is not a defect."""
        metadata = parse_protected_resource_metadata(
            make_document(authorization_servers=["http://localhost:8000"]),
            SERVICE_ROOT)

        assert metadata.authorization_servers == ("http://localhost:8000",)

    def test_empty_authorization_servers_is_still_metadata(self):
        """A site that lists no issuers is a valid document, just uninformative."""
        metadata = parse_protected_resource_metadata(
            make_document(authorization_servers=[]), SERVICE_ROOT)

        assert metadata.authorization_servers == ()

    @pytest.mark.parametrize(
        "text",
        [
            make_document(resource="https://other-site.erdomain.org"),
            make_document(resource=f"{SERVICE_ROOT}/some/path"),
            make_document(resource=f"{SERVICE_ROOT}//"),
            make_document(resource=f"{SERVICE_ROOT}?tenant=other"),
            make_document(resource=f"{SERVICE_ROOT}#fragment"),
            json.dumps({"authorization_servers": [DAS_ISSUER]}),
            json.dumps({"resource": SERVICE_ROOT}),
            json.dumps({"resource": 42, "authorization_servers": []}),
            json.dumps({"resource": SERVICE_ROOT,
                        "authorization_servers": DAS_ISSUER}),
            json.dumps({"resource": SERVICE_ROOT,
                        "authorization_servers": [DAS_ISSUER, 7]}),
            make_document(authorization_servers=[DAS_ISSUER, ""]),
            make_document(authorization_servers=["not a URL"]),
            make_document(authorization_servers=["https://[broken"]),
            make_document(authorization_servers=[
                          "javascript://issuer.example"]),
            make_document(authorization_servers=[
                          DAS_ISSUER, "ftp://issuer.example"]),
            make_document(resource="https://[broken"),
            make_document(resource="https://fake-site.erdomain.org:notaport"),
            "<html><body>Not Found</body></html>",
            "",
            json.dumps([{"resource": SERVICE_ROOT}]),
        ],
        ids=[
            "resource_is_another_host",
            "resource_has_extra_path",
            "resource_has_two_trailing_slashes",
            "resource_has_query",
            "resource_has_fragment",
            "resource_missing",
            "authorization_servers_missing",
            "resource_not_a_string",
            "authorization_servers_not_a_list",
            "authorization_servers_entry_not_a_string",
            "authorization_servers_entry_empty",
            "authorization_servers_entry_not_a_url",
            "authorization_servers_entry_malformed",
            "authorization_servers_entry_javascript_scheme",
            "authorization_servers_entry_ftp_scheme",
            "resource_malformed",
            "resource_port_not_a_number",
            "not_json",
            "empty_body",
            "json_but_not_an_object",
        ],
    )
    def test_unusable_documents_yield_none(self, text):
        """Any failure means "no metadata"; discovery never raises.

        The malformed cases matter: ``urlparse`` raises on them, and an
        issuer with no host would otherwise read as an external server.
        """
        assert parse_protected_resource_metadata(text, SERVICE_ROOT) is None


class TestClassifyAuthorizationServers:
    """An issuer on the site's own host is the site's legacy token endpoint."""

    def _metadata(self, *issuers):
        return ProtectedResourceMetadata(
            resource=SERVICE_ROOT, authorization_servers=tuple(issuers), raw={})

    def test_das_only(self):
        assert classify_authorization_servers(
            self._metadata(DAS_ISSUER), SERVICE_ROOT) == (True, False)

    def test_external_only(self):
        assert classify_authorization_servers(
            self._metadata(AUTH0_ISSUER), SERVICE_ROOT) == (False, True)

    def test_both(self):
        assert classify_authorization_servers(
            self._metadata(DAS_ISSUER, AUTH0_ISSUER), SERVICE_ROOT) == (True, True)

    def test_no_issuers_at_all(self):
        assert classify_authorization_servers(
            self._metadata(), SERVICE_ROOT) == (False, False)

    def test_host_comparison_ignores_case(self):
        assert classify_authorization_servers(
            self._metadata("https://FAKE-SITE.ERDOMAIN.ORG"), SERVICE_ROOT
        ) == (True, False)

    def test_das_issuer_may_carry_a_path(self):
        """The site's issuer is often {site}/oauth2, not the bare host."""
        assert classify_authorization_servers(
            self._metadata(f"{SERVICE_ROOT}/oauth2"), SERVICE_ROOT
        ) == (True, False)

    def test_an_issuer_urlparse_chokes_on_is_not_the_site(self):
        """Parsing never rejects; an issuer with no readable host is external."""
        assert classify_authorization_servers(
            self._metadata(DAS_ISSUER, "https://[broken"), SERVICE_ROOT
        ) == (True, True)


class TestLooksLikeJwt:
    """A shape check, not a validation: enough to tell modern from legacy."""

    def test_a_jwt_shaped_token(self):
        assert looks_like_jwt(make_jwt()) is True

    def test_header_without_alg_is_not_a_jwt(self):
        assert looks_like_jwt(make_jwt(header={"typ": "JWT"})) is False

    def test_header_that_is_not_a_json_object(self):
        assert looks_like_jwt(make_jwt(header=["RS256"])) is False

    @pytest.mark.parametrize(
        "token",
        [
            "NOT-BASE64.DUMMY-PAYLOAD.DUMMY-SIGNATURE",
            "DUMMY-HEADER.DUMMY-PAYLOAD",
            "dummy-opaque-das-token-000000001",
            "DUMMY-HEADER..DUMMY-SIGNATURE",
            "DUMMY-HEADER.DUMMY-PAYLOAD.DUMMY-SIGNATURE.DUMMY-EXTRA",
            "",
            None,
            42,
            b"a.b.c",
        ],
        ids=[
            "two_dots_but_garbage_header",
            "one_dot",
            "opaque_das_token",
            "empty_segment",
            "too_many_segments",
            "empty_string",
            "none",
            "not_a_string",
            "bytes",
        ],
    )
    def test_non_jwts(self, token):
        assert looks_like_jwt(token) is False


class TestLegacyAuthWarning:
    """The warning table: what each credential mode deserves at each site."""

    def test_password_grant_at_a_migrating_site(self):
        assert legacy_auth_warning(
            service_root=SERVICE_ROOT, has_das=True, has_external=True,
            mode="password",
        ) == (
            f"Site {SERVICE_ROOT} supports EarthRanger's Auth0 sign-in. "
            "Username/password login through the site's legacy token endpoint "
            "still works but is deprecated and will stop working when the site "
            "completes its migration. Pass an Auth0-issued access token with "
            "token=, or construct the client with no credentials and call "
            "login() to sign in interactively."
        )

    def test_password_grant_at_a_migrated_site_is_not_a_warning(self):
        """It cannot work at all, so credential_site_mismatch raises instead."""
        assert legacy_auth_warning(
            service_root=SERVICE_ROOT, has_das=False, has_external=True,
            mode="password",
        ) is None

    def test_opaque_token_at_a_migrating_site(self):
        assert legacy_auth_warning(
            service_root=SERVICE_ROOT, has_das=True, has_external=True,
            mode="opaque_token",
        ) == (
            "The token passed with token= looks like a legacy "
            f"EarthRanger-issued token. Site {SERVICE_ROOT} supports Auth0 "
            "sign-in, and legacy tokens will stop working when the site "
            "completes its migration. Use an Auth0-issued access token, or "
            "construct the client with no credentials and call login() to "
            "sign in interactively."
        )

    def test_opaque_token_at_a_migrated_site_is_not_a_warning(self):
        """It cannot work at all, so credential_site_mismatch raises instead."""
        assert legacy_auth_warning(
            service_root=SERVICE_ROOT, has_das=False, has_external=True,
            mode="opaque_token",
        ) is None

    @pytest.mark.parametrize("mode", ["password", "opaque_token", "jwt_token"])
    @pytest.mark.parametrize(
        "has_das, has_external",
        [(False, False), (True, False)],
        ids=["no_issuers_listed", "das_only"],
    )
    def test_a_site_that_has_not_migrated_is_silent(self, mode, has_das, has_external):
        assert legacy_auth_warning(
            service_root=SERVICE_ROOT, has_das=has_das,
            has_external=has_external, mode=mode,
        ) is None

    @pytest.mark.parametrize(
        "has_das, has_external",
        [(True, True), (False, True)],
        ids=["migrating", "migrated"],
    )
    def test_a_jwt_is_never_warned_about(self, has_das, has_external):
        """A modern token is what we are asking callers to move to."""
        assert legacy_auth_warning(
            service_root=SERVICE_ROOT, has_das=has_das,
            has_external=has_external, mode="jwt_token",
        ) is None


class TestNormalizeIssuer:
    """Issuer strings are compared as identifiers, not as text.

    DAS validates a JWT's ``iss`` against exactly the string discovery
    advertises, so the only differences worth forgiving are the ones RFC 3986
    calls insignificant.
    """

    def test_strips_one_trailing_slash(self):
        assert normalize_issuer(f"{AUTH0_ISSUER}/") == AUTH0_ISSUER

    def test_strips_only_one_trailing_slash(self):
        """Two slashes are a different path, not a cosmetic difference."""
        assert normalize_issuer(f"{AUTH0_ISSUER}//") == f"{AUTH0_ISSUER}/"

    def test_lowercases_scheme_and_host(self):
        assert normalize_issuer(
            "HTTPS://FAKE-TENANT.US.AUTH0.COM") == AUTH0_ISSUER

    def test_preserves_path_case(self):
        """Only scheme and host are case-insensitive; a path is a path."""
        assert normalize_issuer(
            f"{SERVICE_ROOT}/OAuth2") == f"{SERVICE_ROOT}/OAuth2"

    def test_preserves_the_port(self):
        assert normalize_issuer(
            "https://Fake-Site.erdomain.org:8443/oauth2/"
        ) == "https://fake-site.erdomain.org:8443/oauth2"

    @pytest.mark.parametrize(
        "issuer",
        ["https://user@FAKE-TENANT.us.auth0.com/",
         "https://user:secret@fake-tenant.us.auth0.com",
         "https://@fake-tenant.us.auth0.com"],
        ids=["user", "user_and_password", "empty_userinfo"],
    )
    def test_userinfo_is_left_alone(self, issuer):
        """Rebuilding from the host would drop it and let the issuer pass as
        the accepted one; the server would not agree."""
        assert normalize_issuer(issuer) == issuer

    def test_keeps_the_brackets_around_an_ipv6_literal(self):
        """``hostname`` strips them; without them the port is ambiguous."""
        assert normalize_issuer(
            "https://[2001:DB8::1]:8443/oauth2/"
        ) == "https://[2001:db8::1]:8443/oauth2"

    @pytest.mark.parametrize(
        "issuer",
        ["not a url at all", "fake-tenant.us.auth0.com", "https://", "",
         "https://[broken", "https://fake-tenant.us.auth0.com:notaport"],
        ids=["prose", "no_scheme", "no_host", "empty", "malformed_ipv6",
             "non_numeric_port"],
    )
    def test_something_that_is_not_a_url_comes_back_unchanged(self, issuer):
        """Nothing to normalize means nothing to invent; comparison then fails honestly.

        The last two make ``urlparse`` raise; a token's ``iss`` claim is
        untrusted input, so that must not reach the caller.
        """
        assert normalize_issuer(issuer) == issuer


class TestJwtIssuer:
    """The ``iss`` claim, read without trusting it.

    No signature check: an attacker-supplied ``iss`` can only make the client
    refuse to send a token it was given, which is not an attack.
    """

    def test_reads_the_issuer_claim(self):
        token = make_jwt(payload={"iss": AUTH0_ISSUER, "sub": "auth0|1"})

        assert jwt_issuer(token) == AUTH0_ISSUER

    def test_decodes_a_payload_whose_base64_needs_padding(self):
        """Real JWTs carry no ``=`` padding; we put it back before decoding."""
        token = make_jwt(payload={"iss": f"{AUTH0_ISSUER}/"})
        _, payload, _ = token.split(".")

        assert len(payload) % 4 != 0
        assert jwt_issuer(token) == f"{AUTH0_ISSUER}/"

    @pytest.mark.parametrize(
        "payload",
        [
            {"sub": "auth0|1"},
            {"iss": ""},
            {"iss": 42},
            {"iss": None},
            [AUTH0_ISSUER],
        ],
        ids=["no_iss", "iss_empty", "iss_not_a_string", "iss_null",
             "payload_not_an_object"],
    )
    def test_no_usable_issuer_claim(self, payload):
        assert jwt_issuer(make_jwt(payload=payload)) is None

    def test_payload_that_is_not_json(self):
        """The placeholder payload is not even base64; this never raises."""
        assert jwt_issuer(make_jwt()) is None

    @pytest.mark.parametrize(
        "token",
        ["dummy-opaque-das-token-000000001", "", None, 42, b"a.b.c"],
        ids=["opaque_das_token", "empty_string", "none", "not_a_string",
             "bytes"],
    )
    def test_a_token_that_is_not_a_jwt_has_no_issuer(self, token):
        assert jwt_issuer(token) is None


def metadata_listing(*issuers, resource=SERVICE_ROOT):
    """Metadata for a site that lists exactly these authorization servers."""
    return ProtectedResourceMetadata(
        resource=resource, authorization_servers=tuple(issuers), raw={})


EXTERNAL_ONLY = metadata_listing(AUTH0_ISSUER)
BOTH_LISTED = metadata_listing(DAS_ISSUER, AUTH0_ISSUER)
DAS_ONLY = metadata_listing(DAS_ISSUER)

PASSWORD_MISMATCH = (
    f"Site {SERVICE_ROOT} accepts only Auth0-issued tokens, so "
    "username/password login against its legacy token endpoint cannot work: "
    "the token endpoint may still issue a token, but every API request would "
    "be rejected. Pass an Auth0-issued access token with token=, or construct "
    "the client with no credentials and call login() to sign in interactively."
)
OPAQUE_TOKEN_MISMATCH = (
    "The token passed with token= looks like a legacy EarthRanger-issued "
    f"token, but site {SERVICE_ROOT} accepts only Auth0-issued tokens. Use an "
    "Auth0-issued access token, or construct the client with no credentials "
    "and call login() to sign in interactively."
)


def mismatch(metadata, mode, token_issuer=None):
    return credential_site_mismatch(metadata=metadata,
                                    service_root=SERVICE_ROOT, mode=mode,
                                    token_issuer=token_issuer)


class TestCredentialSiteMismatchWithoutMetadata:
    """No document, or an uninformative one, means no opinion."""

    @pytest.mark.parametrize("mode", ["password", "opaque_token", "jwt_token"])
    def test_no_metadata_at_all(self, mode):
        assert mismatch(None, mode, token_issuer=AUTH0_ISSUER) is None

    @pytest.mark.parametrize("mode", ["password", "opaque_token", "jwt_token"])
    def test_a_site_that_lists_no_issuers(self, mode):
        assert mismatch(metadata_listing(), mode,
                        token_issuer=AUTH0_ISSUER) is None


class TestCredentialSiteMismatchForLegacyCredentials:
    """Password grant and opaque tokens: the site's own issuer must be listed."""

    def test_password_grant_where_only_auth0_is_accepted(self):
        assert mismatch(EXTERNAL_ONLY, "password") == PASSWORD_MISMATCH

    def test_opaque_token_where_only_auth0_is_accepted(self):
        assert mismatch(EXTERNAL_ONLY, "opaque_token") == OPAQUE_TOKEN_MISMATCH

    @pytest.mark.parametrize("mode", ["password", "opaque_token"])
    @pytest.mark.parametrize(
        "metadata", [BOTH_LISTED, DAS_ONLY], ids=["migrating", "not_migrated"]
    )
    def test_legacy_credentials_a_site_still_accepts(self, metadata, mode):
        """While the site lists its own issuer, legacy credentials can work."""
        assert mismatch(metadata, mode) is None

    @pytest.mark.parametrize("mode", ["password", "opaque_token"])
    def test_the_site_issuer_may_carry_a_path(self, mode):
        """DAS advertises {site}/oauth2, which is still the site itself."""
        assert mismatch(
            metadata_listing(f"{SERVICE_ROOT}/oauth2", AUTH0_ISSUER), mode
        ) is None


class TestCredentialSiteMismatchForJwts:
    """A JWT is refused only when its issuer is not one the site named."""

    def test_an_unlisted_issuer_names_what_the_site_accepts(self):
        assert mismatch(
            BOTH_LISTED, "jwt_token", token_issuer="https://other.us.auth0.com"
        ) == (
            "The token passed with token= was issued by "
            f"https://other.us.auth0.com, which site {SERVICE_ROOT} does not "
            f"accept. Accepted issuers: {DAS_ISSUER}, {AUTH0_ISSUER}."
        )

    @pytest.mark.parametrize(
        "metadata", [DAS_ONLY, EXTERNAL_ONLY, BOTH_LISTED],
        ids=["not_migrated", "migrated", "migrating"],
    )
    def test_an_unlisted_issuer_is_refused_at_every_kind_of_site(self, metadata):
        message = mismatch(metadata, "jwt_token",
                           token_issuer="https://other.us.auth0.com")

        assert message is not None
        assert "does not accept" in message

    def test_the_accepted_list_is_normalized(self):
        """The caller is shown issuers in the form we compared against."""
        message = mismatch(
            metadata_listing("HTTPS://FAKE-TENANT.US.AUTH0.COM/"),
            "jwt_token", token_issuer="https://other.us.auth0.com",
        )

        assert message.endswith(f"Accepted issuers: {AUTH0_ISSUER}.")

    @pytest.mark.parametrize(
        "token_issuer",
        [AUTH0_ISSUER, f"{AUTH0_ISSUER}/", "https://FAKE-TENANT.us.auth0.com"],
        ids=["exact", "trailing_slash", "host_case"],
    )
    def test_a_listed_issuer_is_accepted_however_it_is_spelled(self, token_issuer):
        assert mismatch(BOTH_LISTED, "jwt_token",
                        token_issuer=token_issuer) is None

    def test_a_jwt_with_no_issuer_claim_is_not_second_guessed(self):
        """Unreadable is not the same as wrong; the server can still judge it."""
        assert mismatch(EXTERNAL_ONLY, "jwt_token", token_issuer=None) is None

    @pytest.mark.parametrize(
        "token_issuer",
        ["https://[broken", "https://other.us.auth0.com:notaport",
         f"https://user@{AUTH0_ISSUER[len('https://'):]}"],
        ids=["malformed_ipv6", "non_numeric_port",
             "accepted_host_with_userinfo"],
    )
    def test_an_issuer_claim_urlparse_chokes_on_is_a_mismatch(self, token_issuer):
        """A forged or garbled iss is refused like any unlisted one, not raised.

        The last case is the accepted issuer with userinfo in front of the
        host: DAS compares the string exactly, so it is not the accepted issuer.
        """
        assert mismatch(BOTH_LISTED, "jwt_token", token_issuer=token_issuer) == (
            f"The token passed with token= was issued by {token_issuer}, which "
            f"site {SERVICE_ROOT} does not accept. Accepted issuers: "
            f"{DAS_ISSUER}, {AUTH0_ISSUER}."
        )
