import pytest
import json

from unittest.mock import patch, MagicMock
from erclient.client import ERClient


@pytest.mark.parametrize(
    "version,events_types_response",
    [
        pytest.param("v1", "v1", id="v1"),
        pytest.param("v2", "v2", id="v2"),
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


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_post_event_type_different_versions(er_server_info, post_event_type_payload, post_event_type_response, version):
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = post_event_type_response
        mock_response.text = json.dumps(post_event_type_response)
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_response  # <-- Fix here
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.post_event_type(post_event_type_payload, version=version)

        mock_session_instance.post.assert_called()
        assert result == post_event_type_response["data"]


def test_post_event_type_without_version_treated_like_v1(er_server_info, post_event_type_payload, post_event_type_response):
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = post_event_type_response
        mock_response.text = json.dumps(post_event_type_response)
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_response  # <-- Fix here
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.post_event_type(post_event_type_payload)

        mock_session_instance.post.assert_called()
        assert result == post_event_type_response["data"]


@pytest.mark.parametrize("version", ["v1", "v2"])
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
        result = er_client.patch_event_type(patch_event_type_payload, version=version)

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
