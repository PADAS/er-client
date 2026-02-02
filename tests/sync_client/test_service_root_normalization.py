"""Tests for service_root normalization in ERClient (strips /api or /api/... to avoid .../api/api/v1.0)."""
import pytest

from erclient.client import ERClient


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
