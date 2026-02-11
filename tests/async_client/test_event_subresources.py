import httpx
import pytest
import respx

from erclient import (
    ERClientException,
    ERClientNotFound,
    ERClientPermissionDenied,
    ERClientBadRequest,
)

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

@pytest.mark.asyncio
async def test_get_event_geometry_success(er_client, event_geometry_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/event/{EVENT_ID}/geometry")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=event_geometry_response
        )
        response = await er_client.get_event_geometry(EVENT_ID)
        assert route.called
        assert response == event_geometry_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_geometry_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/event/{EVENT_ID}/geometry")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "Not found"}},
        )
        with pytest.raises(ERClientNotFound):
            await er_client.get_event_geometry(EVENT_ID)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_geometry_forbidden(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/event/{EVENT_ID}/geometry")
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN,
            json={"status": {"code": 403, "message": "Forbidden"}},
        )
        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_event_geometry(EVENT_ID)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_geometry_no_geometry(er_client):
    """Event exists but has no geometry attached."""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/event/{EVENT_ID}/geometry")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": None, "status": {"code": 200, "message": "OK"}},
        )
        response = await er_client.get_event_geometry(EVENT_ID)
        assert route.called
        # data is None, which is falsy -- should return the full json since data is falsy
        await er_client.close()


# ---- POST event state ----

@pytest.mark.asyncio
async def test_post_event_state_success(er_client, event_state_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f"activity/event/{EVENT_ID}/state")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=event_state_response
        )
        response = await er_client.post_event_state(
            EVENT_ID, {"state": "active"}
        )
        assert route.called
        assert response == event_state_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_post_event_state_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f"activity/event/{EVENT_ID}/state")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "Not found"}},
        )
        with pytest.raises(ERClientNotFound):
            await er_client.post_event_state(EVENT_ID, {"state": "active"})
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_event_state_bad_request(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f"activity/event/{EVENT_ID}/state")
        route.return_value = httpx.Response(
            httpx.codes.BAD_REQUEST,
            json={"status": {"code": 400, "detail": "Invalid state transition"}},
        )
        with pytest.raises(ERClientBadRequest):
            await er_client.post_event_state(EVENT_ID, {"state": "invalid"})
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_event_state_forbidden(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f"activity/event/{EVENT_ID}/state")
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN,
            json={"status": {"code": 403, "message": "Forbidden"}},
        )
        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_event_state(EVENT_ID, {"state": "active"})
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_event_state_timeout(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f"activity/event/{EVENT_ID}/state")
        route.side_effect = httpx.ConnectTimeout
        with pytest.raises(ERClientException):
            await er_client.post_event_state(EVENT_ID, {"state": "active"})
        assert route.called
        await er_client.close()


# ---- GET event segments ----

@pytest.mark.asyncio
async def test_get_event_segments_success(er_client, event_segments_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/event/{EVENT_ID}/segments")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=event_segments_response
        )
        response = await er_client.get_event_segments(EVENT_ID)
        assert route.called
        assert response == event_segments_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_segments_empty(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/event/{EVENT_ID}/segments")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": [], "status": {"code": 200, "message": "OK"}},
        )
        response = await er_client.get_event_segments(EVENT_ID)
        assert route.called
        assert response == []
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_segments_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/event/{EVENT_ID}/segments")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "Not found"}},
        )
        with pytest.raises(ERClientNotFound):
            await er_client.get_event_segments(EVENT_ID)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_segments_forbidden(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/event/{EVENT_ID}/segments")
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN,
            json={"status": {"code": 403, "message": "Forbidden"}},
        )
        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_event_segments(EVENT_ID)
        assert route.called
        await er_client.close()
