import json
from unittest.mock import MagicMock, patch

import pytest

from erclient.client import ERClient
from erclient.er_errors import ERClientException, ERClientNotFound, ERClientPermissionDenied


def test_delete_event_type_success_defaults_to_v2(er_server_info):
    """delete_event_type() defaults to v2.0 and hits .../api/v2.0/activity/eventtypes/{slug}."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.delete_event_type("rainfall_rep")

        assert result is True
        mock_session_instance.delete.assert_called_once()
        call_url = mock_session_instance.delete.call_args[0][0]
        assert "/api/v2.0/" in call_url
        assert "activity/eventtypes/rainfall_rep" in call_url


def test_delete_event_type_explicit_v2(er_server_info):
    """delete_event_type(version="v2.0") uses v2.0 API path."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.delete_event_type("immobility_rep", version="v2.0")

        assert result is True
        call_url = mock_session_instance.delete.call_args[0][0]
        assert "/api/v2.0/" in call_url
        assert "activity/eventtypes/immobility_rep" in call_url


def test_delete_event_type_v1(er_server_info):
    """delete_event_type(version="v1.0") uses the v1.0 path."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.delete_event_type("some_type", version="v1.0")

        assert result is True
        call_url = mock_session_instance.delete.call_args[0][0]
        assert "/api/v1.0/" in call_url
        assert "activity/events/eventtypes/some_type" in call_url


def test_delete_event_type_version_alias_v2(er_server_info):
    """delete_event_type(version="v2") alias is normalized to v2.0."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.delete_event_type("test_type", version="v2")

        assert result is True
        call_url = mock_session_instance.delete.call_args[0][0]
        assert "/api/v2.0/" in call_url
        assert "activity/eventtypes/test_type" in call_url


def test_delete_event_type_not_found(er_server_info):
    """delete_event_type() raises ERClientNotFound on 404."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = '{"detail": "Not found."}'
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        with pytest.raises(ERClientNotFound):
            er_client.delete_event_type("nonexistent_type")


def test_delete_event_type_forbidden(er_server_info):
    """delete_event_type() raises ERClientPermissionDenied on 403."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.text = json.dumps({
            "status": {"detail": "You do not have permission to perform this action."}
        })
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        with pytest.raises(ERClientPermissionDenied):
            er_client.delete_event_type("protected_type")


def test_delete_event_type_conflict_raises_with_detail(er_server_info):
    """delete_event_type() raises ERClientException with detail on 409 Conflict."""
    conflict_detail = (
        "Cannot delete Event Type 'In Use Type' because it is associated "
        "with existing Events, and it is associated with existing Alert Rules."
    )
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 409
        mock_response.text = json.dumps({"detail": conflict_detail})
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        with pytest.raises(ERClientException, match="Cannot delete"):
            er_client.delete_event_type("in_use_type")


def test_delete_event_type_conflict_events_only(er_server_info):
    """409 with only events dependency surfaces the correct detail."""
    conflict_detail = (
        "Cannot delete Event Type 'Events Only' because it is associated "
        "with existing Events."
    )
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 409
        mock_response.text = json.dumps({"detail": conflict_detail})
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        with pytest.raises(ERClientException, match="existing Events"):
            er_client.delete_event_type("events_only_type")


def test_delete_event_type_server_error(er_server_info):
    """delete_event_type() raises ERClientException on 500."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        with pytest.raises(ERClientException, match="Failed to delete"):
            er_client.delete_event_type("server_error_type")


def test_delete_event_type_base_url_assembles_api_path(er_server_info):
    """When service_root is a base URL (no /api/), client assembles .../api/v2.0."""
    base_only = {**er_server_info,
                 "service_root": "https://something.pamdas.org"}
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**base_only)
        er_client.delete_event_type("test_slug")

        call_url = mock_session_instance.delete.call_args[0][0]
        assert call_url.startswith("https://something.pamdas.org/api/v2.0/")
        assert "activity/eventtypes/test_slug" in call_url
