import json
from unittest.mock import MagicMock, patch

import pytest

from erclient.client import ERClient


def test_service_root_base_url_assembles_api_path(er_server_info, get_events_types_response_v1):
    """When service_root is a base URL (no /api/), client assembles .../api/v1.0 or .../api/v2.0."""
    base_only = {**er_server_info,
                 "service_root": "https://something.pamdas.org"}
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = get_events_types_response_v1
        mock_response.text = json.dumps(get_events_types_response_v1)
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**base_only)
        er_client.get_event_types()
        call_url = mock_session_instance.get.call_args[0][0]
        assert call_url.startswith("https://something.pamdas.org/api/v1.0/")
        assert "activity/events/eventtypes" in call_url

        mock_session_instance.get.reset_mock()
        er_client.get_event_types(version="v2.0")
        call_url_v2 = mock_session_instance.get.call_args[0][0]
        assert "/api/v2.0/" in call_url_v2
        assert "activity/eventtypes" in call_url_v2


@pytest.mark.parametrize(
    "version,events_types_response",
    [
        pytest.param("v1.0", "v1.0", id="v1.0"),
        pytest.param("v2.0", "v2.0", id="v2.0"),
    ],
    indirect=["events_types_response"],
)
def test_get_event_types_different_versions(er_server_info, version, events_types_response):
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = events_types_response
        mock_response.text = json.dumps(events_types_response)
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        event_types = er_client.get_event_types(version=version)

        mock_session_instance.get.assert_called()
        assert event_types == events_types_response["data"]
        call_url = mock_session_instance.get.call_args[0][0]
        assert f"/api/{version}" in call_url


def test_get_event_types_without_version_treated_like_v1(er_server_info, get_events_types_response_v1):
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = get_events_types_response_v1
        mock_response.text = json.dumps(get_events_types_response_v1)
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        event_types = er_client.get_event_types()

        mock_session_instance.get.assert_called()
        assert event_types == get_events_types_response_v1["data"]


@pytest.mark.parametrize("version", ["v1.0", "v2.0"])
def test_post_event_type_different_versions(er_server_info, post_event_type_payload, post_event_type_response, version):
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = post_event_type_response
        mock_response.text = json.dumps(post_event_type_response)
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.post_event_type(
            post_event_type_payload, version=version)

        mock_session_instance.post.assert_called()
        assert result == post_event_type_response["data"]


def test_post_event_type_without_version_treated_like_v1(er_server_info, post_event_type_payload, post_event_type_response):
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = post_event_type_response
        mock_response.text = json.dumps(post_event_type_response)
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.post_event_type(post_event_type_payload)

        mock_session_instance.post.assert_called()
        assert result == post_event_type_response["data"]


@pytest.mark.parametrize("version", ["v1.0", "v2.0"])
def test_patch_event_type_different_versions(er_server_info, patch_event_type_payload, patch_event_type_response, version):
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = patch_event_type_response
        mock_response.text = json.dumps(patch_event_type_response)
        mock_session_instance = MagicMock()
        mock_session_instance.patch.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.patch_event_type(
            patch_event_type_payload, version=version)

        mock_session_instance.patch.assert_called()
        assert result == patch_event_type_response["data"]


def test_patch_event_type_without_version_treated_like_v1(er_server_info, patch_event_type_payload, patch_event_type_response):
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = patch_event_type_response
        mock_response.text = json.dumps(patch_event_type_response)
        mock_session_instance = MagicMock()
        mock_session_instance.patch.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.patch_event_type(patch_event_type_payload)

        mock_session_instance.patch.assert_called()
        assert result == patch_event_type_response["data"]


@pytest.mark.parametrize("version", ["v1.0", "v2.0"])
def test_get_event_type_different_versions(er_server_info, version):
    """get_event_type(name, version) uses the correct path and API root for each version."""
    event_type_slug = "test_event_type"
    get_response = {"data": {"id": "et-uuid",
                             "value": event_type_slug, "display": "Test"}}
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = get_response
        mock_response.text = json.dumps(get_response)
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.get_event_type(event_type_slug, version=version)

        mock_session_instance.get.assert_called_once()
        call_url = mock_session_instance.get.call_args[0][0]
        assert f"/api/{version}/" in call_url
        if version == "v2.0":
            assert "activity/eventtypes/" in call_url
            assert event_type_slug in call_url
        else:
            assert "activity/events/schema/eventtype/" in call_url
            assert event_type_slug in call_url
        assert result == get_response["data"]


def test_get_event_type_version_alias_v2_uses_v2_api_root(er_server_info):
    """get_event_type(version="v2") alias is normalized; request goes to .../api/v2.0/activity/eventtypes/."""
    event_type_slug = "test_event_type"
    get_response = {"data": {"id": "et-uuid",
                             "value": event_type_slug, "display": "Test"}}
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = get_response
        mock_response.text = json.dumps(get_response)
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.get_event_type(event_type_slug, version="v2")

        mock_session_instance.get.assert_called_once()
        call_url = mock_session_instance.get.call_args[0][0]
        assert "/api/v2.0/" in call_url
        assert "activity/eventtypes/" in call_url
        assert event_type_slug in call_url
        assert result == get_response["data"]
