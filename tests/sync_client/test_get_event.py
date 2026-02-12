import json
from unittest.mock import MagicMock, patch

import pytest

from erclient.client import ERClient
from erclient.er_errors import ERClientNotFound, ERClientBadCredentials, ERClientPermissionDenied


class TestGetEvent:
    """Tests for ERClient.get_event() -- single event detail retrieval."""

    def test_get_event_basic(self, er_client, single_event_response):
        """get_event returns the event data dict for a valid event_id."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = json.dumps(single_event_response)

        with patch.object(er_client._http_session, 'get', return_value=mock_response) as mock_get:
            event_id = "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f"
            result = er_client.get_event(event_id=event_id)

            # Verify it called the correct URL
            call_args = mock_get.call_args
            url = call_args[0][0]
            assert f"activity/event/{event_id}" in url

            # Verify the result is the event data
            assert result["id"] == event_id
            assert result["event_type"] == "rainfall_rep"
            assert result["title"] == "Rainfall"

    def test_get_event_default_params(self, er_client, single_event_response):
        """get_event sends correct default query parameters."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = json.dumps(single_event_response)

        with patch.object(er_client._http_session, 'get', return_value=mock_response) as mock_get:
            er_client.get_event(event_id="9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f")

            call_args = mock_get.call_args
            params = call_args[1]['params']

            # Default: include_details=True, everything else False
            assert params['include_details'] is True
            assert params['include_updates'] is False
            assert params['include_notes'] is False
            assert params['include_related_events'] is False
            assert params['include_files'] is False

    def test_get_event_with_all_includes(self, er_client, single_event_response):
        """get_event forwards all include flags as query params."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = json.dumps(single_event_response)

        with patch.object(er_client._http_session, 'get', return_value=mock_response) as mock_get:
            er_client.get_event(
                event_id="9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f",
                include_details=True,
                include_updates=True,
                include_notes=True,
                include_related_events=True,
                include_files=True,
            )

            call_args = mock_get.call_args
            params = call_args[1]['params']

            assert params['include_details'] is True
            assert params['include_updates'] is True
            assert params['include_notes'] is True
            assert params['include_related_events'] is True
            assert params['include_files'] is True

    def test_get_event_with_notes(self, er_client, single_event_with_notes_response):
        """get_event returns notes when include_notes=True."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = json.dumps(single_event_with_notes_response)

        with patch.object(er_client._http_session, 'get', return_value=mock_response):
            result = er_client.get_event(
                event_id="9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f",
                include_notes=True,
            )

            assert len(result["notes"]) == 1
            assert "heavy rainfall" in result["notes"][0]["text"]

    def test_get_event_include_details_false(self, er_client, single_event_response):
        """get_event can be called with include_details=False."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = json.dumps(single_event_response)

        with patch.object(er_client._http_session, 'get', return_value=mock_response) as mock_get:
            er_client.get_event(
                event_id="9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f",
                include_details=False,
            )

            call_args = mock_get.call_args
            params = call_args[1]['params']
            assert params['include_details'] is False

    def test_get_event_not_found(self, er_client):
        """get_event raises ERClientNotFound for 404 responses."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = json.dumps({"status": {"detail": "Not found."}})

        with patch.object(er_client._http_session, 'get', return_value=mock_response):
            with pytest.raises(ERClientNotFound):
                er_client.get_event(event_id="00000000-0000-0000-0000-000000000000")

    def test_get_event_unauthorized(self, er_client):
        """get_event raises ERClientBadCredentials for 401 responses."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = json.dumps(
            {"status": {"detail": "Authentication credentials were not provided."}}
        )

        with patch.object(er_client._http_session, 'get', return_value=mock_response):
            with pytest.raises(ERClientBadCredentials):
                er_client.get_event(event_id="9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f")

    def test_get_event_forbidden(self, er_client):
        """get_event raises ERClientPermissionDenied for 403 responses."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.text = json.dumps(
            {"status": {"detail": "You do not have permission to perform this action."}}
        )

        with patch.object(er_client._http_session, 'get', return_value=mock_response):
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_event(event_id="9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f")

    def test_get_event_returns_event_details(self, er_client, single_event_response):
        """get_event response includes event_details when requested."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = json.dumps(single_event_response)

        with patch.object(er_client._http_session, 'get', return_value=mock_response):
            result = er_client.get_event(event_id="9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f")

            assert "event_details" in result
            assert result["event_details"]["height_m"] == 5
            assert result["event_details"]["amount_mm"] == 8

    def test_get_event_url_construction(self, er_client, single_event_response):
        """get_event constructs the correct URL including activity/event/{id}."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = json.dumps(single_event_response)

        with patch.object(er_client._http_session, 'get', return_value=mock_response) as mock_get:
            event_id = "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f"
            er_client.get_event(event_id=event_id)

            call_args = mock_get.call_args
            url = call_args[0][0]
            assert f"activity/event/{event_id}" in url
            assert event_id in url
