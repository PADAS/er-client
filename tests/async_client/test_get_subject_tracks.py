import httpx
import pytest
import respx
from datetime import datetime, timezone


@pytest.fixture
def v1_tracks_response():
    """Typical v1 subject tracks response (flat coordinate pairs)."""
    return {
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [36.7922, -1.2932],
                            [36.7921, -1.2931],
                            [36.7919, -1.2931],
                        ],
                    },
                    "properties": {
                        "title": "Test Subject",
                    },
                }
            ],
        }
    }


@pytest.fixture
def v2_tracks_response():
    """Typical v2 segmented tracks response (GeoJSON FeatureCollection)."""
    return {
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [36.7922, -1.2932],
                            [36.7921, -1.2931],
                        ],
                    },
                    "properties": {
                        "count": 2,
                        "start_time": "2025-01-01T00:00:00Z",
                        "end_time": "2025-01-01T01:00:00Z",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [36.7919, -1.2931],
                            [36.7917, -1.2931],
                        ],
                    },
                    "properties": {
                        "count": 2,
                        "start_time": "2025-01-01T02:00:00Z",
                        "end_time": "2025-01-01T03:00:00Z",
                    },
                },
            ],
        }
    }


SUBJECT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


# ── v1 (default) tracks ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_subject_tracks_v1_default(er_client, v1_tracks_response):
    """get_subject_tracks() with default version hits the v1 endpoint."""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"subject/{SUBJECT_ID}/tracks")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=v1_tracks_response
        )

        result = await er_client.get_subject_tracks(subject_id=SUBJECT_ID)

        assert route.called
        assert result == v1_tracks_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_v1_with_dates(er_client, v1_tracks_response):
    """v1 tracks pass since/until params when start/end are given."""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"subject/{SUBJECT_ID}/tracks")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=v1_tracks_response
        )

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        result = await er_client.get_subject_tracks(
            subject_id=SUBJECT_ID, start=start, end=end
        )

        assert route.called
        request = route.calls[0].request
        assert "since" in str(request.url)
        assert "until" in str(request.url)
        await er_client.close()


# ── v2 segmented tracks ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_subject_tracks_v2(er_client, v2_tracks_response):
    """get_subject_tracks(version='2.0') hits the v2 segmented endpoint."""
    v2_base = er_client._api_root("v2.0")
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{v2_base}/subject/{SUBJECT_ID}/tracks/"
        ).respond(httpx.codes.OK, json=v2_tracks_response)

        result = await er_client.get_subject_tracks(
            subject_id=SUBJECT_ID, version="2.0"
        )

        assert route.called
        assert result == v2_tracks_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_v2_with_dates(er_client, v2_tracks_response):
    """v2 tracks pass since/until when start/end are given."""
    v2_base = er_client._api_root("v2.0")
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{v2_base}/subject/{SUBJECT_ID}/tracks/"
        ).respond(httpx.codes.OK, json=v2_tracks_response)

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        result = await er_client.get_subject_tracks(
            subject_id=SUBJECT_ID, start=start, end=end, version="2.0"
        )

        assert route.called
        request = route.calls[0].request
        assert "since" in str(request.url)
        assert "until" in str(request.url)
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_v2_with_extra_params(er_client, v2_tracks_response):
    """v2 tracks forward additional filter params (show_excluded, max_speed_kmh, etc.)."""
    v2_base = er_client._api_root("v2.0")
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{v2_base}/subject/{SUBJECT_ID}/tracks/"
        ).respond(httpx.codes.OK, json=v2_tracks_response)

        result = await er_client.get_subject_tracks(
            subject_id=SUBJECT_ID,
            version="2.0",
            show_excluded="true",
            max_speed_kmh=120.0,
            max_gap_minutes=30,
        )

        assert route.called
        request = route.calls[0].request
        url_str = str(request.url)
        assert "show_excluded" in url_str
        assert "max_speed_kmh" in url_str
        assert "max_gap_minutes" in url_str
        await er_client.close()


# ── get_subject_source_tracks (async) ─────────────────────────────

@pytest.mark.asyncio
async def test_get_subject_source_tracks(er_client, v1_tracks_response):
    """get_subject_source_tracks() hits the correct endpoint."""
    source_id = "bbbb1111-2222-3333-4444-555566667777"
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(
            f"subject/{SUBJECT_ID}/source/{source_id}/tracks"
        )
        route.return_value = httpx.Response(
            httpx.codes.OK, json=v1_tracks_response
        )

        result = await er_client.get_subject_source_tracks(
            subject_id=SUBJECT_ID, src_id=source_id
        )

        assert route.called
        assert result == v1_tracks_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_source_tracks_with_since(er_client, v1_tracks_response):
    """get_subject_source_tracks() passes since param."""
    source_id = "bbbb1111-2222-3333-4444-555566667777"
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(
            f"subject/{SUBJECT_ID}/source/{source_id}/tracks"
        )
        route.return_value = httpx.Response(
            httpx.codes.OK, json=v1_tracks_response
        )

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = await er_client.get_subject_source_tracks(
            subject_id=SUBJECT_ID, src_id=source_id, start=start
        )

        assert route.called
        request = route.calls[0].request
        assert "since" in str(request.url)
        await er_client.close()


# ── Error handling ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_subject_tracks_not_found(er_client, not_found_response):
    """get_subject_tracks() raises ERClientNotFound on 404."""
    from erclient import ERClientNotFound

    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"subject/{SUBJECT_ID}/tracks")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json=not_found_response
        )

        with pytest.raises(ERClientNotFound):
            await er_client.get_subject_tracks(subject_id=SUBJECT_ID)

        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_v2_not_found(er_client, not_found_response):
    """get_subject_tracks(version='2.0') raises ERClientNotFound on 404."""
    from erclient import ERClientNotFound

    v2_base = er_client._api_root("v2.0")
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{v2_base}/subject/{SUBJECT_ID}/tracks/"
        ).respond(httpx.codes.NOT_FOUND, json=not_found_response)

        with pytest.raises(ERClientNotFound):
            await er_client.get_subject_tracks(
                subject_id=SUBJECT_ID, version="2.0"
            )

        await er_client.close()
