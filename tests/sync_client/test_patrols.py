import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from erclient import ERClientNotFound, ERClientPermissionDenied
from erclient.client import ERClient


PATROL_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SEGMENT_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
NOTE_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"
FILE_ID = "d4e5f6a7-b8c9-0123-defa-234567890123"
PATROL_TYPE_ID = "e5f6a7b8-c9d0-1234-efab-345678901234"
EVENT_ID = "f6a7b8c9-d0e1-2345-fabc-456789012345"


def _mock_response(json_data, status_code=200, ok=True):
    """Helper to build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.ok = ok
    resp.status_code = status_code
    resp.text = json.dumps(json_data)
    resp.json.return_value = json_data
    return resp


# ============ get_patrol ============


def test_get_patrol_success(er_client):
    patrol_data = {"data": {"id": PATROL_ID, "title": "Test Patrol"}}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(patrol_data)):
        result = er_client.get_patrol(PATROL_ID)
    assert result["id"] == PATROL_ID


def test_get_patrol_not_found(er_client):
    with patch.object(
        er_client._http_session, "get",
        return_value=_mock_response({}, status_code=404, ok=False),
    ):
        with pytest.raises(ERClientNotFound):
            er_client.get_patrol(PATROL_ID)


# ============ patch_patrol ============


def test_patch_patrol_success(er_client):
    patrol_data = {"data": {"id": PATROL_ID, "state": "done"}}
    with patch.object(er_client._http_session, "patch", return_value=_mock_response(patrol_data)):
        result = er_client.patch_patrol(PATROL_ID, {"state": "done"})
    assert result["id"] == PATROL_ID
    assert result["state"] == "done"


# ============ Patrol Types ============


def test_get_patrol_types(er_client):
    resp_data = {"data": [{"id": PATROL_TYPE_ID, "value": "routine"}]}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(resp_data)):
        result = er_client.get_patrol_types()
    assert isinstance(result, list)
    assert result[0]["id"] == PATROL_TYPE_ID


def test_get_patrol_type(er_client):
    resp_data = {"data": {"id": PATROL_TYPE_ID, "value": "routine"}}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(resp_data)):
        result = er_client.get_patrol_type(PATROL_TYPE_ID)
    assert result["id"] == PATROL_TYPE_ID


def test_post_patrol_type(er_client):
    resp_data = {"data": {"id": PATROL_TYPE_ID, "value": "routine"}}
    with patch.object(er_client._http_session, "post", return_value=_mock_response(resp_data)):
        result = er_client.post_patrol_type({"value": "routine"})
    assert result["id"] == PATROL_TYPE_ID


def test_patch_patrol_type(er_client):
    resp_data = {"data": {"id": PATROL_TYPE_ID, "display": "Updated"}}
    with patch.object(er_client._http_session, "patch", return_value=_mock_response(resp_data)):
        result = er_client.patch_patrol_type(PATROL_TYPE_ID, {"display": "Updated"})
    assert result["display"] == "Updated"


def test_delete_patrol_type(er_client):
    with patch.object(
        er_client._http_session, "delete",
        return_value=_mock_response({}, status_code=204, ok=True),
    ):
        result = er_client.delete_patrol_type(PATROL_TYPE_ID)
    assert result is True


# ============ Patrol Segments ============


def test_get_patrol_segments(er_client):
    resp_data = {"data": [{"id": SEGMENT_ID}]}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(resp_data)):
        result = er_client.get_patrol_segments()
    assert isinstance(result, list)


def test_get_patrol_segment(er_client):
    resp_data = {"data": {"id": SEGMENT_ID}}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(resp_data)):
        result = er_client.get_patrol_segment(SEGMENT_ID)
    assert result["id"] == SEGMENT_ID


def test_post_patrol_segment(er_client):
    resp_data = {"data": {"id": SEGMENT_ID}}
    with patch.object(er_client._http_session, "post", return_value=_mock_response(resp_data)):
        result = er_client.post_patrol_segment({"patrol_type": PATROL_TYPE_ID})
    assert result["id"] == SEGMENT_ID


def test_patch_patrol_segment(er_client):
    resp_data = {"data": {"id": SEGMENT_ID, "leader": "user-1"}}
    with patch.object(er_client._http_session, "patch", return_value=_mock_response(resp_data)):
        result = er_client.patch_patrol_segment(SEGMENT_ID, {"leader": "user-1"})
    assert result["leader"] == "user-1"


def test_get_patrol_segment_events(er_client):
    resp_data = {"data": [{"id": EVENT_ID}]}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(resp_data)):
        result = er_client.get_patrol_segment_events(SEGMENT_ID)
    assert isinstance(result, list)


# ============ Patrol Notes ============


def test_get_patrol_notes(er_client):
    resp_data = {"data": [{"id": NOTE_ID, "text": "A note"}]}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(resp_data)):
        result = er_client.get_patrol_notes(PATROL_ID)
    assert isinstance(result, list)


def test_post_patrol_note(er_client):
    resp_data = {"data": {"id": NOTE_ID, "text": "New note"}}
    with patch.object(er_client._http_session, "post", return_value=_mock_response(resp_data)):
        result = er_client.post_patrol_note(PATROL_ID, {"text": "New note"})
    assert result["id"] == NOTE_ID


def test_patch_patrol_note(er_client):
    resp_data = {"data": {"id": NOTE_ID, "text": "Updated note"}}
    with patch.object(er_client._http_session, "patch", return_value=_mock_response(resp_data)):
        result = er_client.patch_patrol_note(PATROL_ID, NOTE_ID, {"text": "Updated note"})
    assert result["text"] == "Updated note"


def test_delete_patrol_note(er_client):
    with patch.object(
        er_client._http_session, "delete",
        return_value=_mock_response({}, status_code=204, ok=True),
    ):
        result = er_client.delete_patrol_note(PATROL_ID, NOTE_ID)
    assert result is True


# ============ Patrol Files ============


def test_get_patrol_files(er_client):
    resp_data = {"data": [{"id": FILE_ID}]}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(resp_data)):
        result = er_client.get_patrol_files(PATROL_ID)
    assert isinstance(result, list)


def test_get_patrol_file(er_client):
    resp_data = {"data": {"id": FILE_ID, "filename": "report.pdf"}}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(resp_data)):
        result = er_client.get_patrol_file(PATROL_ID, FILE_ID)
    assert result["id"] == FILE_ID


# ============ Patrol Tracked-By ============


def test_get_patrol_trackedby(er_client):
    resp_data = {"data": {"schema": {"type": "object"}}}
    with patch.object(er_client._http_session, "get", return_value=_mock_response(resp_data)):
        result = er_client.get_patrol_trackedby()
    assert "schema" in result


# ============ add_events_to_patrol_segment ============


def test_add_events_to_patrol_segment(er_client):
    events = [{"id": EVENT_ID}]
    patrol_segment = {"id": SEGMENT_ID}
    resp_data = {"data": {"id": EVENT_ID, "patrol_segments": [SEGMENT_ID]}}
    with patch.object(er_client._http_session, "patch", return_value=_mock_response(resp_data)):
        er_client.add_events_to_patrol_segment(events, patrol_segment)
