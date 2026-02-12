"""Tests for service_root normalization in AsyncERClient (strips /api or /api/... to avoid .../api/api/v1.0)."""
import pytest

from erclient.client import AsyncERClient


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
def test_async_service_root_normalization_strips_api_segment(
    service_root_input, expected_base, expected_api_root_v1
):
    """AsyncERClient: service_root ending with /api or /api/... is normalized so _api_root does not double /api."""
    client = AsyncERClient(
        service_root=service_root_input, provider_key="test")
    assert client.service_root == expected_base
    assert client._api_root("v1.0") == expected_api_root_v1


def test_async_token_url_derived_from_service_root_when_omitted():
    """When token_url is not passed, it defaults to {service_root}/oauth2/token."""
    client = AsyncERClient(service_root="https://hello.pamdas.org", provider_key="test")
    assert client.token_url == "https://hello.pamdas.org/oauth2/token"


def test_async_token_url_override_respected():
    """When token_url is passed, it is used instead of the default."""
    client = AsyncERClient(
        service_root="https://hello.pamdas.org",
        token_url="https://auth.other.org/oauth2/token",
        provider_key="test",
    )
    assert client.token_url == "https://auth.other.org/oauth2/token"
