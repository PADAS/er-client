import json
from unittest.mock import MagicMock, patch

import pytest

from erclient.client import ERClient


@pytest.fixture
def get_event_response():
    """Single event as returned by GET activity/event/{id} (with data wrapper)."""
    return {
        "data": {
            "id": "5b3bf4ec-64be-427a-bdb6-60e6894ba5ed",
            "title": "Test event",
            "event_type": "trailguard_rep",
            "state": "active",
            "time": "2023-11-16T15:14:35.066020-06:00",
        }
    }


def test_get_event_returns_event(er_server_info, get_event_response):
    """get_event(event_id=...) returns the event from the API."""
    event_id = "5b3bf4ec-64be-427a-bdb6-60e6894ba5ed"
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = json.dumps(get_event_response)
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        result = er_client.get_event(event_id=event_id)

        mock_session_instance.get.assert_called_once()
        call_url = mock_session_instance.get.call_args[0][0]
        call_kwargs = mock_session_instance.get.call_args[1]
        assert f"activity/event/{event_id}" in call_url
        assert call_kwargs["params"]["include_details"] is True
        assert result == get_event_response["data"]


def test_get_event_passes_include_params(er_server_info, get_event_response):
    """get_event passes include_details, include_updates, include_notes, etc. as query params."""
    event_id = "abc-123"
    with patch("erclient.client.requests.Session") as mock_session:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = json.dumps(get_event_response)
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        er_client = ERClient(**er_server_info)
        er_client.get_event(
            event_id=event_id,
            include_details=False,
            include_updates=True,
            include_notes=True,
            include_related_events=True,
            include_files=True,
        )

        call_kwargs = mock_session_instance.get.call_args[1]
        params = call_kwargs["params"]
        assert params["include_details"] is False
        assert params["include_updates"] is True
        assert params["include_notes"] is True
        assert params["include_related_events"] is True
        assert params["include_files"] is True
