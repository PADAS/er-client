import json
from unittest.mock import patch

import pytest

from erclient import (
    ERClientException,
    ERClientNotFound,
    ERClientPermissionDenied,
)
from tests.sync_client.conftest import _mock_response

EVENT_ID = "e1e2e3e4-f5f6-7890-abcd-aabbccddeeff"


# ---- Fixtures ----

@pytest.fixture
def event_geometry_response():
    return {
        "data": {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [36.79, -1.29],
                        [36.80, -1.29],
                        [36.80, -1.30],
                        [36.79, -1.30],
                        [36.79, -1.29],
                    ]
                ],
            },
            "properties": {},
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def event_state_response():
    return {
        "data": {
            "id": EVENT_ID,
            "state": "active",
            "updated_at": "2025-01-15T10:30:00Z",
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def event_segments_response():
    return {
        "data": [
            {
                "id": "seg-11111111-2222-3333-4444-555555555555",
                "patrol": "pat-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "time_range": {
                    "start_time": "2025-01-15T08:00:00Z",
                    "end_time": "2025-01-15T16:00:00Z",
                },
                "leader": {"username": "ranger1"},
            },
        ],
        "status": {"code": 200, "message": "OK"},
    }


# ---- GET event geometry ----

class TestGetEventGeometry:
    def test_success(self, er_client, event_geometry_response):
        with patch.object(er_client._http_session, "get") as mock_get:
            mock_get.return_value = _mock_response(200, event_geometry_response)
            result = er_client.get_event_geometry(EVENT_ID)
            assert mock_get.called
            assert result == event_geometry_response["data"]
            call_url = mock_get.call_args[0][0]
            assert f"activity/event/{EVENT_ID}/geometry" in call_url

    def test_not_found(self, er_client):
        with patch.object(er_client._http_session, "get") as mock_get:
            mock_get.return_value = _mock_response(404)
            with pytest.raises(ERClientNotFound):
                er_client.get_event_geometry(EVENT_ID)

    def test_forbidden(self, er_client):
        with patch.object(er_client._http_session, "get") as mock_get:
            mock_get.return_value = _mock_response(
                403, {"status": {"detail": "Forbidden"}}
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_event_geometry(EVENT_ID)


# ---- POST event state ----

class TestPostEventState:
    def test_success(self, er_client, event_state_response):
        with patch.object(er_client._http_session, "post") as mock_post:
            mock_post.return_value = _mock_response(200, event_state_response)
            result = er_client.post_event_state(EVENT_ID, {"state": "active"})
            assert mock_post.called
            assert result == event_state_response["data"]

    def test_not_found(self, er_client):
        with patch.object(er_client._http_session, "post") as mock_post:
            mock_post.return_value = _mock_response(404)
            with pytest.raises(ERClientNotFound):
                er_client.post_event_state(EVENT_ID, {"state": "active"})

    def test_forbidden(self, er_client):
        with patch.object(er_client._http_session, "post") as mock_post:
            mock_post.return_value = _mock_response(
                403, {"status": {"detail": "Forbidden"}}
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.post_event_state(EVENT_ID, {"state": "active"})


# ---- GET event segments ----

class TestGetEventSegments:
    def test_success(self, er_client, event_segments_response):
        with patch.object(er_client._http_session, "get") as mock_get:
            mock_get.return_value = _mock_response(200, event_segments_response)
            result = er_client.get_event_segments(EVENT_ID)
            assert mock_get.called
            assert result == event_segments_response["data"]
            call_url = mock_get.call_args[0][0]
            assert f"activity/event/{EVENT_ID}/segments" in call_url

    def test_empty(self, er_client):
        with patch.object(er_client._http_session, "get") as mock_get:
            mock_get.return_value = _mock_response(
                200, {"data": [], "status": {"code": 200, "message": "OK"}}
            )
            result = er_client.get_event_segments(EVENT_ID)
            assert mock_get.called
            assert result == []

    def test_not_found(self, er_client):
        with patch.object(er_client._http_session, "get") as mock_get:
            mock_get.return_value = _mock_response(404)
            with pytest.raises(ERClientNotFound):
                er_client.get_event_segments(EVENT_ID)

    def test_forbidden(self, er_client):
        with patch.object(er_client._http_session, "get") as mock_get:
            mock_get.return_value = _mock_response(
                403, {"status": {"detail": "Forbidden"}}
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_event_segments(EVENT_ID)
