import httpx
import pytest
import respx

from erclient import (
    ERClientException,
    ERClientNotFound,
    ERClientPermissionDenied,
)


PATROL_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SEGMENT_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
NOTE_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"
FILE_ID = "d4e5f6a7-b8c9-0123-defa-234567890123"
PATROL_TYPE_ID = "e5f6a7b8-c9d0-1234-efab-345678901234"
EVENT_ID = "f6a7b8c9-d0e1-2345-fabc-456789012345"


@pytest.fixture
def patrol_data():
    return {
        "id": PATROL_ID,
        "serial_number": 1,
        "title": "Test Patrol",
        "state": "open",
        "patrol_segments": [
            {
                "id": SEGMENT_ID,
                "patrol_type": PATROL_TYPE_ID,
                "leader": None,
                "scheduled_start": None,
                "start_location": None,
                "time_range": {"start_time": "2026-01-01T00:00:00Z", "end_time": None},
            }
        ],
        "notes": [],
        "files": [],
        "updates": [],
    }


@pytest.fixture
def patrol_list_response(patrol_data):
    return {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [patrol_data],
    }


@pytest.fixture
def patrol_detail_response(patrol_data):
    return {"data": patrol_data}


@pytest.fixture
def patrol_type_data():
    return {
        "id": PATROL_TYPE_ID,
        "value": "routine_patrol",
        "display": "Routine Patrol",
        "icon_id": "routine_patrol",
        "default_priority": 0,
        "is_active": True,
    }


@pytest.fixture
def patrol_types_list_response(patrol_type_data):
    return {"data": [patrol_type_data]}


@pytest.fixture
def segment_data():
    return {
        "id": SEGMENT_ID,
        "patrol_type": PATROL_TYPE_ID,
        "leader": None,
        "scheduled_start": None,
        "time_range": {"start_time": "2026-01-01T00:00:00Z", "end_time": None},
        "events": [],
    }


@pytest.fixture
def segments_list_response(segment_data):
    return {"data": [segment_data]}


@pytest.fixture
def note_data():
    return {
        "id": NOTE_ID,
        "text": "Test patrol note",
        "created_at": "2026-01-01T12:00:00Z",
    }


@pytest.fixture
def notes_list_response(note_data):
    return {"data": [note_data]}


@pytest.fixture
def file_data():
    return {
        "id": FILE_ID,
        "comment": "Test file",
        "filename": "test.pdf",
        "created_at": "2026-01-01T12:00:00Z",
    }


@pytest.fixture
def files_list_response(file_data):
    return {"data": [file_data]}


@pytest.fixture
def trackedby_response():
    return {"data": {"schema": {"type": "object"}}}


# ============ get_patrols ============


@pytest.mark.asyncio
async def test_get_patrols_single_page(er_client, patrol_list_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/patrols").respond(
            json=patrol_list_response
        )
        patrols = []
        async for patrol in er_client.get_patrols():
            patrols.append(patrol)
        assert route.called
        assert len(patrols) == 1
        assert patrols[0]["id"] == PATROL_ID


@pytest.mark.asyncio
async def test_get_patrols_multi_page(er_client, patrol_data):
    page1 = {
        "count": 2,
        "next": f"{er_client.service_root}/activity/patrols?page=2&page_size=1&use_cursor=true",
        "previous": None,
        "results": [patrol_data],
    }
    page2 = {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {**patrol_data, "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}
        ],
    }
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/patrols")
        route.side_effect = [
            httpx.Response(httpx.codes.OK, json=page1),
            httpx.Response(httpx.codes.OK, json=page2),
        ]
        patrols = []
        async for patrol in er_client.get_patrols(page_size=1):
            patrols.append(patrol)
        assert route.call_count == 2
        assert len(patrols) == 2


# ============ get_patrol ============


@pytest.mark.asyncio
async def test_get_patrol_success(er_client, patrol_data, patrol_detail_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/patrols/{PATROL_ID}").respond(
            json=patrol_detail_response
        )
        result = await er_client.get_patrol(PATROL_ID)
        assert route.called
        assert result == patrol_data


@pytest.mark.asyncio
async def test_get_patrol_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        respx_mock.get(f"activity/patrols/{PATROL_ID}").respond(
            status_code=httpx.codes.NOT_FOUND, json={}
        )
        with pytest.raises(ERClientNotFound):
            await er_client.get_patrol(PATROL_ID)


# ============ post_patrol ============


@pytest.mark.asyncio
async def test_post_patrol_success(er_client, patrol_data, patrol_detail_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/patrols").respond(
            status_code=httpx.codes.CREATED, json=patrol_detail_response
        )
        result = await er_client.post_patrol(patrol_data)
        assert route.called
        assert result == patrol_data


@pytest.mark.asyncio
async def test_post_patrol_forbidden(er_client, patrol_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        respx_mock.post("activity/patrols").respond(
            status_code=httpx.codes.FORBIDDEN,
            json={"status": {"code": 403, "detail": "Forbidden"}},
        )
        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_patrol(patrol_data)


# ============ patch_patrol ============


@pytest.mark.asyncio
async def test_patch_patrol_success(er_client, patrol_data, patrol_detail_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/patrols/{PATROL_ID}").respond(
            json=patrol_detail_response
        )
        result = await er_client.patch_patrol(PATROL_ID, {"state": "done"})
        assert route.called
        assert result == patrol_data


# ============ delete_patrol ============


@pytest.mark.asyncio
async def test_delete_patrol_success(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/patrols/{PATROL_ID}/").respond(
            status_code=httpx.codes.NO_CONTENT, json={}
        )
        await er_client.delete_patrol(PATROL_ID)
        assert route.called


@pytest.mark.asyncio
async def test_delete_patrol_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        respx_mock.delete(f"activity/patrols/{PATROL_ID}/").respond(
            status_code=httpx.codes.NOT_FOUND, json={}
        )
        with pytest.raises(ERClientNotFound):
            await er_client.delete_patrol(PATROL_ID)


# ============ Patrol Types ============


@pytest.mark.asyncio
async def test_get_patrol_types(er_client, patrol_types_list_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/patrols/types").respond(
            json=patrol_types_list_response
        )
        result = await er_client.get_patrol_types()
        assert route.called
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_patrol_type(er_client, patrol_type_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(
            f"activity/patrols/types/{PATROL_TYPE_ID}"
        ).respond(json={"data": patrol_type_data})
        result = await er_client.get_patrol_type(PATROL_TYPE_ID)
        assert route.called
        assert result == patrol_type_data


@pytest.mark.asyncio
async def test_post_patrol_type(er_client, patrol_type_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/patrols/types").respond(
            status_code=httpx.codes.CREATED,
            json={"data": patrol_type_data},
        )
        result = await er_client.post_patrol_type(patrol_type_data)
        assert route.called
        assert result == patrol_type_data


@pytest.mark.asyncio
async def test_patch_patrol_type(er_client, patrol_type_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(
            f"activity/patrols/types/{PATROL_TYPE_ID}"
        ).respond(json={"data": patrol_type_data})
        result = await er_client.patch_patrol_type(
            PATROL_TYPE_ID, {"display": "Updated"}
        )
        assert route.called


@pytest.mark.asyncio
async def test_delete_patrol_type(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(
            f"activity/patrols/types/{PATROL_TYPE_ID}"
        ).respond(status_code=httpx.codes.NO_CONTENT, json={})
        await er_client.delete_patrol_type(PATROL_TYPE_ID)
        assert route.called


# ============ Patrol Segments ============


@pytest.mark.asyncio
async def test_get_patrol_segments(er_client, segments_list_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/patrols/segments").respond(
            json=segments_list_response
        )
        result = await er_client.get_patrol_segments()
        assert route.called


@pytest.mark.asyncio
async def test_get_patrol_segment(er_client, segment_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(
            f"activity/patrols/segments/{SEGMENT_ID}"
        ).respond(json={"data": segment_data})
        result = await er_client.get_patrol_segment(SEGMENT_ID)
        assert route.called
        assert result == segment_data


@pytest.mark.asyncio
async def test_post_patrol_segment(er_client, segment_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/patrols/segments").respond(
            status_code=httpx.codes.CREATED,
            json={"data": segment_data},
        )
        result = await er_client.post_patrol_segment(segment_data)
        assert route.called
        assert result == segment_data


@pytest.mark.asyncio
async def test_patch_patrol_segment(er_client, segment_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(
            f"activity/patrols/segments/{SEGMENT_ID}"
        ).respond(json={"data": segment_data})
        result = await er_client.patch_patrol_segment(
            SEGMENT_ID, {"leader": "some-user-id"}
        )
        assert route.called


@pytest.mark.asyncio
async def test_get_patrol_segment_events(er_client):
    events_resp = {"data": [{"id": EVENT_ID, "event_type": "test"}]}
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(
            f"activity/patrols/segments/{SEGMENT_ID}/events"
        ).respond(json=events_resp)
        result = await er_client.get_patrol_segment_events(SEGMENT_ID)
        assert route.called
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_add_events_to_patrol_segment(er_client):
    events = [{"id": EVENT_ID}]
    patrol_segment = {"id": SEGMENT_ID}
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/event/{EVENT_ID}").respond(
            json={"data": {"id": EVENT_ID, "patrol_segments": [SEGMENT_ID]}}
        )
        await er_client.add_events_to_patrol_segment(events, patrol_segment)
        assert route.called


# ============ Patrol Notes ============


@pytest.mark.asyncio
async def test_get_patrol_notes(er_client, notes_list_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(
            f"activity/patrols/{PATROL_ID}/notes"
        ).respond(json=notes_list_response)
        result = await er_client.get_patrol_notes(PATROL_ID)
        assert route.called


@pytest.mark.asyncio
async def test_post_patrol_note(er_client, note_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(
            f"activity/patrols/{PATROL_ID}/notes"
        ).respond(
            status_code=httpx.codes.CREATED,
            json={"data": note_data},
        )
        result = await er_client.post_patrol_note(
            PATROL_ID, {"text": "Test patrol note"}
        )
        assert route.called
        assert result == note_data


@pytest.mark.asyncio
async def test_patch_patrol_note(er_client, note_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(
            f"activity/patrols/{PATROL_ID}/notes/{NOTE_ID}"
        ).respond(json={"data": note_data})
        result = await er_client.patch_patrol_note(
            PATROL_ID, NOTE_ID, {"text": "Updated note"}
        )
        assert route.called


@pytest.mark.asyncio
async def test_delete_patrol_note(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(
            f"activity/patrols/{PATROL_ID}/notes/{NOTE_ID}"
        ).respond(status_code=httpx.codes.NO_CONTENT, json={})
        await er_client.delete_patrol_note(PATROL_ID, NOTE_ID)
        assert route.called


# ============ Patrol Files ============


@pytest.mark.asyncio
async def test_get_patrol_files(er_client, files_list_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(
            f"activity/patrols/{PATROL_ID}/files"
        ).respond(json=files_list_response)
        result = await er_client.get_patrol_files(PATROL_ID)
        assert route.called


@pytest.mark.asyncio
async def test_post_patrol_file(er_client, file_data):
    import io

    fake_file = io.BytesIO(b"test file content")
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(
            f"activity/patrols/{PATROL_ID}/files/"
        ).respond(
            status_code=httpx.codes.CREATED,
            json={"data": file_data},
        )
        result = await er_client.post_patrol_file(
            PATROL_ID, fake_file, comment="test"
        )
        assert route.called
        assert result == file_data


@pytest.mark.asyncio
async def test_get_patrol_file(er_client, file_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(
            f"activity/patrols/{PATROL_ID}/file/{FILE_ID}"
        ).respond(json={"data": file_data})
        result = await er_client.get_patrol_file(PATROL_ID, FILE_ID)
        assert route.called
        assert result == file_data


# ============ Patrol Tracked-By ============


@pytest.mark.asyncio
async def test_get_patrol_trackedby(er_client, trackedby_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/patrols/trackedby").respond(
            json=trackedby_response
        )
        result = await er_client.get_patrol_trackedby()
        assert route.called


# ============ Error Handling ============


@pytest.mark.asyncio
async def test_post_patrol_connect_timeout(er_client, patrol_data):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/patrols")
        route.side_effect = httpx.ConnectTimeout
        with pytest.raises(ERClientException):
            await er_client.post_patrol(patrol_data)
        assert route.called


@pytest.mark.asyncio
async def test_patch_patrol_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        respx_mock.patch(f"activity/patrols/{PATROL_ID}").respond(
            status_code=httpx.codes.NOT_FOUND, json={}
        )
        with pytest.raises(ERClientNotFound):
            await er_client.patch_patrol(PATROL_ID, {"state": "done"})
