"""Unit tests for the RFC 9728 discovery helpers.

No HTTP here: these are the pure decisions the clients make once a discovery
document is in hand — is it usable, whose authorization servers does it list,
and do the credentials in hand deserve a warning at this site.
"""
import base64
import json

import pytest

from erclient.discovery import (DISCOVERY_PATH, ProtectedResourceMetadata,
                                classify_authorization_servers, discovery_url,
                                legacy_auth_warning, looks_like_jwt,
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


def make_jwt(header=None):
    """A JWT-shaped string.

    Only the header is encoded for real, since that is the only segment
    ``looks_like_jwt`` decodes; the other two stay plainly fake.
    """
    header = {"alg": "RS256", "typ": "JWT"} if header is None else header
    encoded = base64.urlsafe_b64encode(
        json.dumps(header).encode()).decode().rstrip("=")
    return f"{encoded}.DUMMY-PAYLOAD.DUMMY-SIGNATURE"


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
            json.dumps({"authorization_servers": [DAS_ISSUER]}),
            json.dumps({"resource": SERVICE_ROOT}),
            json.dumps({"resource": 42, "authorization_servers": []}),
            json.dumps({"resource": SERVICE_ROOT,
                        "authorization_servers": DAS_ISSUER}),
            json.dumps({"resource": SERVICE_ROOT,
                        "authorization_servers": [DAS_ISSUER, 7]}),
            "<html><body>Not Found</body></html>",
            "",
            json.dumps([{"resource": SERVICE_ROOT}]),
        ],
        ids=[
            "resource_is_another_host",
            "resource_has_extra_path",
            "resource_missing",
            "authorization_servers_missing",
            "resource_not_a_string",
            "authorization_servers_not_a_list",
            "authorization_servers_entry_not_a_string",
            "not_json",
            "empty_body",
            "json_but_not_an_object",
        ],
    )
    def test_unusable_documents_yield_none(self, text):
        """Any failure means "no metadata"; discovery never raises."""
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
        ],
        ids=[
            "two_dots_but_garbage_header",
            "one_dot",
            "opaque_das_token",
            "empty_segment",
            "too_many_segments",
            "empty_string",
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
            "token= instead."
        )

    def test_password_grant_at_a_migrated_site(self):
        assert legacy_auth_warning(
            service_root=SERVICE_ROOT, has_das=False, has_external=True,
            mode="password",
        ) == (
            f"Site {SERVICE_ROOT} accepts only Auth0-issued tokens. "
            "Username/password login against its legacy token endpoint will "
            "fail. Pass an Auth0-issued access token with token= instead."
        )

    def test_opaque_token_at_a_migrating_site(self):
        assert legacy_auth_warning(
            service_root=SERVICE_ROOT, has_das=True, has_external=True,
            mode="opaque_token",
        ) == (
            "The token passed with token= looks like a legacy "
            f"EarthRanger-issued token. Site {SERVICE_ROOT} supports Auth0 "
            "sign-in, and legacy tokens will stop working when the site "
            "completes its migration. Use an Auth0-issued access token."
        )

    def test_opaque_token_at_a_migrated_site(self):
        assert legacy_auth_warning(
            service_root=SERVICE_ROOT, has_das=False, has_external=True,
            mode="opaque_token",
        ) == (
            "The token passed with token= looks like a legacy "
            f"EarthRanger-issued token, but site {SERVICE_ROOT} accepts only "
            "Auth0-issued tokens. Requests will be rejected. Use an "
            "Auth0-issued access token."
        )

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
