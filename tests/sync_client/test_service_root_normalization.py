"""Tests for service_root normalization in ERClient (strips /api or /api/... to avoid .../api/api/v1.0)."""
import pytest

from erclient.client import ERClient, normalize_service_root


@pytest.mark.parametrize(
    "service_root_input,expected_base,expected_api_root_v1",
    [
        ("https://example.com", "https://example.com",
         "https://example.com/api/v1.0"),
        ("https://example.com/", "https://example.com",
         "https://example.com/api/v1.0"),
        ("https://example.com/api", "https://example.com",
         "https://example.com/api/v1.0"),
        ("https://example.com/api/", "https://example.com",
         "https://example.com/api/v1.0"),
        ("https://example.com/api/v1.0", "https://example.com",
         "https://example.com/api/v1.0"),
        ("https://example.com/api/v2.0", "https://example.com",
         "https://example.com/api/v1.0"),
        ("https://example.com/some/path/api", "https://example.com/some/path",
         "https://example.com/some/path/api/v1.0"),
        ("https://example.com/some/path/api/v1.0", "https://example.com/some/path",
         "https://example.com/some/path/api/v1.0"),
    ],
    ids=[
        "base_no_slash",
        "base_trailing_slash",
        "ends_with_api_no_slash",
        "ends_with_api_trailing_slash",
        "full_v1",
        "full_v2",
        "path_then_api",
        "path_then_api_v1",
    ],
)
def test_service_root_normalization_strips_api_segment(
    service_root_input, expected_base, expected_api_root_v1
):
    """service_root ending with /api or /api/... is normalized so _api_root does not double /api."""
    client = ERClient(service_root=service_root_input, provider_key="test")
    assert client.service_root == expected_base
    assert client._api_root("v1.0") == expected_api_root_v1


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://example.com/api/v1.0", "https://example.com"),
        ("https://example.com/", "https://example.com"),
        ("https://example.com/some/path/api", "https://example.com/some/path"),
        # Callers that pass nothing get an empty root rather than an exception;
        # ERClient has always tolerated a missing service_root at construction.
        ("", ""),
        (None, ""),
    ],
    ids=["full_v1", "trailing_slash", "path_then_api", "empty", "none"],
)
def test_normalize_service_root_is_the_shared_implementation(raw, expected):
    """Both clients and the auth module derive an origin through this one function."""
    assert normalize_service_root(raw) == expected


def test_token_url_derived_from_service_root_when_omitted():
    """When token_url is not passed, it defaults to {service_root}/oauth2/token."""
    client = ERClient(service_root="https://hello.pamdas.org",
                      provider_key="test")
    assert client.token_url == "https://hello.pamdas.org/oauth2/token"


def test_token_url_override_respected():
    """When token_url is passed, it is used instead of the default."""
    client = ERClient(
        service_root="https://hello.pamdas.org",
        token_url="https://auth.other.org/oauth2/token",
        provider_key="test",
    )
    assert client.token_url == "https://auth.other.org/oauth2/token"
