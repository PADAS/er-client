"""The protected-resource metadata parser and the comparisons built on it.
Everything here is a pure function that must never raise, whatever a site
serves."""
import json

import pytest

from erclient.discovery import (DISCOVERY_PATH, ProtectedResourceMetadata,
                                classify_authorization_servers, discovery_url,
                                normalize_issuer, parse_absolute_url,
                                parse_protected_resource_metadata)

SITE = "https://fake-site.erdomain.org"
DAS_ISSUER = f"{SITE}/oauth2"
AUTH0_ISSUER = "https://auth-dev.pamdas.org"


def document(resource=SITE, authorization_servers=(DAS_ISSUER, AUTH0_ISSUER),
             **extra):
    body = {"resource": resource,
            "authorization_servers": list(authorization_servers)}
    body.update(extra)
    return json.dumps(body)


def parse(text, expected_resource=SITE):
    return parse_protected_resource_metadata(text, expected_resource)


class TestDiscoveryUrl:

    def test_appends_the_well_known_path(self):
        assert discovery_url(SITE) == f"{SITE}{DISCOVERY_PATH}"

    def test_does_not_double_the_separator(self):
        assert discovery_url(f"{SITE}/") == f"{SITE}{DISCOVERY_PATH}"

    @pytest.mark.parametrize("service_root", ["", None])
    def test_no_site_means_nothing_to_ask(self, service_root):
        assert discovery_url(service_root) is None


class TestParseAbsoluteUrl:

    @pytest.mark.parametrize("value", [
        "https://example.com",
        "http://example.com:8000/path",
        "https://example.com/a?b=c#d",
    ])
    def test_accepts_an_absolute_url(self, value):
        assert parse_absolute_url(value) is not None

    @pytest.mark.parametrize("value", [
        "not a url",
        "/just/a/path",
        "example.com",
        "https://",
        "https://example.com:notaport",
        "http://[oops",
        None,
        42,
    ])
    def test_anything_else_is_none_rather_than_a_raise(self, value):
        assert parse_absolute_url(value) is None


class TestParseProtectedResourceMetadata:

    def test_reads_the_resource_and_the_issuer_list(self):
        metadata = parse(document())

        assert isinstance(metadata, ProtectedResourceMetadata)
        assert metadata.resource == SITE
        assert metadata.authorization_servers == (DAS_ISSUER, AUTH0_ISSUER)

    def test_keeps_the_whole_document(self):
        metadata = parse(document(scopes_supported=["read"]))

        assert metadata.raw["scopes_supported"] == ["read"]

    def test_an_empty_issuer_list_is_still_a_document(self):
        assert parse(document(authorization_servers=())
                     ).authorization_servers == ()

    @pytest.mark.parametrize("resource", [
        f"{SITE}/",
        "HTTPS://FAKE-SITE.ERDOMAIN.ORG",
    ])
    def test_cosmetic_differences_in_the_resource_are_forgiven(self, resource):
        assert parse(document(resource=resource)) is not None

    @pytest.mark.parametrize("resource", [
        "https://other-site.erdomain.org",
        f"{SITE}/somewhere-else",
        f"{SITE}//",
        "not a url",
    ])
    def test_a_document_for_something_else_is_no_document(self, resource):
        assert parse(document(resource=resource)) is None

    @pytest.mark.parametrize("text", [
        "",
        "not json at all",
        "<html><body>404</body></html>",
        "[]",
        '"a bare string"',
        "null",
        None,
    ])
    def test_a_body_that_is_not_a_json_object_is_no_document(self, text):
        assert parse(text) is None

    @pytest.mark.parametrize("body", [
        {"authorization_servers": [AUTH0_ISSUER]},
        {"resource": SITE},
        {"resource": SITE, "authorization_servers": AUTH0_ISSUER},
        {"resource": 42, "authorization_servers": []},
    ])
    def test_a_document_missing_what_we_read_is_no_document(self, body):
        assert parse(json.dumps(body)) is None

    @pytest.mark.parametrize("issuer", [
        "auth-dev.pamdas.org",
        "/oauth2",
        "javascript://issuer.example",
        "https://",
        42,
        None,
    ])
    def test_one_entry_that_is_not_an_issuer_discards_the_list(self, issuer):
        assert parse(
            document(authorization_servers=(DAS_ISSUER, issuer))) is None

    def test_a_plain_http_issuer_is_allowed_for_a_development_site(self):
        assert parse(document(resource="http://localhost:8000",
                              authorization_servers=("http://localhost:8000/oauth2",)),
                     "http://localhost:8000") is not None


class TestClassifyAuthorizationServers:

    @pytest.mark.parametrize("issuers,expected", [
        ((DAS_ISSUER,), (True, False)),
        ((AUTH0_ISSUER,), (False, True)),
        ((DAS_ISSUER, AUTH0_ISSUER), (True, True)),
        ((), (False, False)),
    ])
    def test_an_issuer_on_the_sites_own_host_is_the_site(self, issuers,
                                                         expected):
        metadata = parse(document(authorization_servers=issuers))

        assert classify_authorization_servers(metadata, SITE) == expected

    def test_the_host_decides_whatever_path_the_issuer_carries(self):
        metadata = parse(document(authorization_servers=(f"{SITE}/anywhere",)))

        assert classify_authorization_servers(metadata, SITE) == (True, False)

    def test_the_comparison_ignores_host_case(self):
        metadata = parse(document(
            authorization_servers=("https://FAKE-SITE.erdomain.org/oauth2",)))

        assert classify_authorization_servers(metadata, SITE) == (True, False)


class TestNormalizeIssuer:

    @pytest.mark.parametrize("issuer", [
        "https://auth-dev.pamdas.org",
        "https://auth-dev.pamdas.org/",
        "HTTPS://AUTH-DEV.PAMDAS.ORG",
    ])
    def test_forgives_the_differences_rfc_3986_calls_insignificant(self, issuer):
        assert normalize_issuer(issuer) == AUTH0_ISSUER

    def test_keeps_a_port(self):
        assert normalize_issuer(
            "http://localhost:8000/") == "http://localhost:8000"

    def test_keeps_a_path_that_is_not_just_a_slash(self):
        assert normalize_issuer(f"{SITE}/oauth2/") == DAS_ISSUER

    def test_leaves_only_one_trailing_slash_forgiven(self):
        assert normalize_issuer(f"{SITE}/oauth2//") == f"{SITE}/oauth2/"

    @pytest.mark.parametrize("issuer", ["not a url", "", None])
    def test_what_it_cannot_parse_comes_back_untouched(self, issuer):
        assert normalize_issuer(issuer) == issuer
