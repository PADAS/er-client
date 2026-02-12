import pytest
import responses

from erclient import ERClientNotFound, ERClientPermissionDenied
from erclient.client import ERClient


PATROL_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SEGMENT_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
NOTE_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"
FILE_ID = "d4e5f6a7-b8c9-0123-defa-234567890123"
PATROL_TYPE_ID = "e5f6a7b8-c9d0-1234-efab-345678901234"
EVENT_ID = "f6a7b8c9-d0e1-2345-fabc-456789012345"


def _url(client, path):
    """Build full API URL like ERClient._er_url (match client after #23)."""
    base = client._api_root("v1.0")
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


# ============ get_patrol ============


@responses.activate
def test_get_patrol_success(er_client):
    patrol_data = {"data": {"id": PATROL_ID, "title": "Test Patrol"}}
    url = _url(er_client, f"activity/patrols/{PATROL_ID}")
    responses.get(url, json=patrol_data)
    result = er_client.get_patrol(PATROL_ID)
    assert result["id"] == PATROL_ID
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == url


@responses.activate
def test_get_patrol_not_found(er_client):
    url = _url(er_client, f"activity/patrols/{PATROL_ID}")
    responses.get(url, json={}, status=404)
    with pytest.raises(ERClientNotFound):
        er_client.get_patrol(PATROL_ID)


@responses.activate
def test_get_patrol_forbidden(er_client):
    url = _url(er_client, f"activity/patrols/{PATROL_ID}")
    responses.get(
        url,
        json={"status": {"code": 403, "detail": "Forbidden"}},
        status=403,
    )
    with pytest.raises(ERClientPermissionDenied):
        er_client.get_patrol(PATROL_ID)


# ============ patch_patrol ============


@responses.activate
def test_patch_patrol_success(er_client):
    patrol_data = {"data": {"id": PATROL_ID, "state": "done"}}
    url = _url(er_client, f"activity/patrols/{PATROL_ID}")
    responses.patch(url, json=patrol_data)
    result = er_client.patch_patrol(PATROL_ID, {"state": "done"})
    assert result["id"] == PATROL_ID
    assert result["state"] == "done"
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == url


# ============ delete_patrol ============


@responses.activate
def test_delete_patrol_success(er_client):
    url = _url(er_client, f"activity/patrols/{PATROL_ID}/")
    responses.delete(url, status=204)
    er_client.delete_patrol(PATROL_ID)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == url


@responses.activate
def test_delete_patrol_not_found(er_client):
    url = _url(er_client, f"activity/patrols/{PATROL_ID}/")
    responses.delete(url, json={}, status=404)
    with pytest.raises(ERClientNotFound):
        er_client.delete_patrol(PATROL_ID)


@responses.activate
def test_delete_patrol_forbidden(er_client):
    url = _url(er_client, f"activity/patrols/{PATROL_ID}/")
    responses.delete(
        url,
        json={"status": {"code": 403, "detail": "Forbidden"}},
        status=403,
    )
    with pytest.raises(ERClientPermissionDenied):
        er_client.delete_patrol(PATROL_ID)


# ============ Patrol Types ============


@responses.activate
def test_get_patrol_types(er_client):
    resp_data = {"data": [{"id": PATROL_TYPE_ID, "value": "routine"}]}
    url = _url(er_client, "activity/patrols/types")
    responses.get(url, json=resp_data)
    result = er_client.get_patrol_types()
    assert isinstance(result, list)
    assert result[0]["id"] == PATROL_TYPE_ID


@responses.activate
def test_get_patrol_type(er_client):
    resp_data = {"data": {"id": PATROL_TYPE_ID, "value": "routine"}}
    url = _url(er_client, f"activity/patrols/types/{PATROL_TYPE_ID}")
    responses.get(url, json=resp_data)
    result = er_client.get_patrol_type(PATROL_TYPE_ID)
    assert result["id"] == PATROL_TYPE_ID


@responses.activate
def test_post_patrol_type(er_client):
    resp_data = {"data": {"id": PATROL_TYPE_ID, "value": "routine"}}
    url = _url(er_client, "activity/patrols/types")
    responses.post(url, json=resp_data)
    result = er_client.post_patrol_type({"value": "routine"})
    assert result["id"] == PATROL_TYPE_ID


@responses.activate
def test_patch_patrol_type(er_client):
    resp_data = {"data": {"id": PATROL_TYPE_ID, "display": "Updated"}}
    url = _url(er_client, f"activity/patrols/types/{PATROL_TYPE_ID}")
    responses.patch(url, json=resp_data)
    result = er_client.patch_patrol_type(PATROL_TYPE_ID, {"display": "Updated"})
    assert result["display"] == "Updated"


@responses.activate
def test_delete_patrol_type(er_client):
    url = _url(er_client, f"activity/patrols/types/{PATROL_TYPE_ID}")
    responses.delete(url, status=204)
    result = er_client.delete_patrol_type(PATROL_TYPE_ID)
    assert result is True


# ============ Patrol Segments ============


@responses.activate
def test_get_patrol_segments(er_client):
    resp_data = {"data": [{"id": SEGMENT_ID}]}
    url = _url(er_client, "activity/patrols/segments")
    responses.get(url, json=resp_data)
    result = er_client.get_patrol_segments()
    assert isinstance(result, list)


@responses.activate
def test_get_patrol_segment(er_client):
    resp_data = {"data": {"id": SEGMENT_ID}}
    url = _url(er_client, f"activity/patrols/segments/{SEGMENT_ID}")
    responses.get(url, json=resp_data)
    result = er_client.get_patrol_segment(SEGMENT_ID)
    assert result["id"] == SEGMENT_ID


@responses.activate
def test_post_patrol_segment(er_client):
    resp_data = {"data": {"id": SEGMENT_ID}}
    url = _url(er_client, "activity/patrols/segments")
    responses.post(url, json=resp_data)
    result = er_client.post_patrol_segment({"patrol_type": PATROL_TYPE_ID})
    assert result["id"] == SEGMENT_ID


@responses.activate
def test_patch_patrol_segment(er_client):
    resp_data = {"data": {"id": SEGMENT_ID, "leader": "user-1"}}
    url = _url(er_client, f"activity/patrols/segments/{SEGMENT_ID}")
    responses.patch(url, json=resp_data)
    result = er_client.patch_patrol_segment(SEGMENT_ID, {"leader": "user-1"})
    assert result["leader"] == "user-1"


@responses.activate
def test_get_patrol_segment_events(er_client):
    resp_data = {"data": [{"id": EVENT_ID}]}
    url = _url(er_client, f"activity/patrols/segments/{SEGMENT_ID}/events")
    responses.get(url, json=resp_data)
    result = er_client.get_patrol_segment_events(SEGMENT_ID)
    assert isinstance(result, list)


# ============ Patrol Notes ============


@responses.activate
def test_get_patrol_notes(er_client):
    resp_data = {"data": [{"id": NOTE_ID, "text": "A note"}]}
    url = _url(er_client, f"activity/patrols/{PATROL_ID}/notes")
    responses.get(url, json=resp_data)
    result = er_client.get_patrol_notes(PATROL_ID)
    assert isinstance(result, list)


@responses.activate
def test_post_patrol_note(er_client):
    resp_data = {"data": {"id": NOTE_ID, "text": "New note"}}
    url = _url(er_client, f"activity/patrols/{PATROL_ID}/notes")
    responses.post(url, json=resp_data)
    result = er_client.post_patrol_note(PATROL_ID, {"text": "New note"})
    assert result["id"] == NOTE_ID


@responses.activate
def test_patch_patrol_note(er_client):
    resp_data = {"data": {"id": NOTE_ID, "text": "Updated note"}}
    url = _url(er_client, f"activity/patrols/{PATROL_ID}/notes/{NOTE_ID}")
    responses.patch(url, json=resp_data)
    result = er_client.patch_patrol_note(PATROL_ID, NOTE_ID, {"text": "Updated note"})
    assert result["text"] == "Updated note"


@responses.activate
def test_delete_patrol_note(er_client):
    url = _url(er_client, f"activity/patrols/{PATROL_ID}/notes/{NOTE_ID}")
    responses.delete(url, status=204)
    result = er_client.delete_patrol_note(PATROL_ID, NOTE_ID)
    assert result is True


# ============ Patrol Files ============


@responses.activate
def test_get_patrol_files(er_client):
    resp_data = {"data": [{"id": FILE_ID}]}
    url = _url(er_client, f"activity/patrols/{PATROL_ID}/files")
    responses.get(url, json=resp_data)
    result = er_client.get_patrol_files(PATROL_ID)
    assert isinstance(result, list)


@responses.activate
def test_get_patrol_file(er_client):
    resp_data = {"data": {"id": FILE_ID, "filename": "report.pdf"}}
    url = _url(er_client, f"activity/patrols/{PATROL_ID}/file/{FILE_ID}")
    responses.get(url, json=resp_data)
    result = er_client.get_patrol_file(PATROL_ID, FILE_ID)
    assert result["id"] == FILE_ID


# ============ Patrol Tracked-By ============


@responses.activate
def test_get_patrol_trackedby(er_client):
    resp_data = {"data": {"schema": {"type": "object"}}}
    url = _url(er_client, "activity/patrols/trackedby")
    responses.get(url, json=resp_data)
    result = er_client.get_patrol_trackedby()
    assert "schema" in result


# ============ add_events_to_patrol_segment ============


@responses.activate
def test_add_events_to_patrol_segment(er_client):
    events = [{"id": EVENT_ID}]
    patrol_segment = {"id": SEGMENT_ID}
    resp_data = {"data": {"id": EVENT_ID, "patrol_segments": [SEGMENT_ID]}}
    url = _url(er_client, f"activity/event/{EVENT_ID}")
    responses.patch(url, json=resp_data)
    er_client.add_events_to_patrol_segment(events, patrol_segment)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == url
