"""Tests for GeoJSON, KML, and vector tile endpoints in the async AsyncERClient."""
import httpx
import pytest
import respx


SERVICE_ROOT = "https://fake-site.erdomain.org/api/v1.0"
SUBJECT_ID = "aaaa1111-2222-3333-4444-bbbbccccdddd"


# --- Fixtures ---

@pytest.fixture
def events_geojson_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-122.359, 47.686]},
                "properties": {"event_type": "rainfall_rep", "title": "Rainfall"},
            }
        ],
    }


@pytest.fixture
def subjects_geojson_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [36.79, -1.29]},
                "properties": {"name": "Lion A", "subject_subtype": "lion"},
            }
        ],
    }


# --- GeoJSON tests ---

@pytest.mark.asyncio
async def test_get_events_geojson(er_client, events_geojson_response):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/activity/events/geojson"
        ).respond(httpx.codes.OK, json=events_geojson_response)

        result = await er_client.get_events_geojson()
        assert route.called
        assert result == events_geojson_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_events_geojson_with_params(er_client, events_geojson_response):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/activity/events/geojson"
        ).respond(httpx.codes.OK, json=events_geojson_response)

        result = await er_client.get_events_geojson(
            state="active", event_type="rainfall_rep", page_size=10
        )
        assert route.called
        req = route.calls[0].request
        assert "state=active" in str(req.url)
        assert "event_type=rainfall_rep" in str(req.url)
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_geojson(er_client, subjects_geojson_response):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/subjects/geojson"
        ).respond(httpx.codes.OK, json=subjects_geojson_response)

        result = await er_client.get_subjects_geojson()
        assert route.called
        assert result == subjects_geojson_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_geojson_with_params(er_client, subjects_geojson_response):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/subjects/geojson"
        ).respond(httpx.codes.OK, json=subjects_geojson_response)

        result = await er_client.get_subjects_geojson(
            include_inactive=True, subject_group="abc"
        )
        assert route.called
        req = route.calls[0].request
        assert "include_inactive=True" in str(req.url) or "include_inactive=true" in str(req.url)
        await er_client.close()


# --- KML tests ---

@pytest.mark.asyncio
async def test_get_subjects_kml(er_client):
    kmz_bytes = b"PK\x03\x04mock-kmz-data"
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/subjects/kml"
        ).respond(httpx.codes.OK, content=kmz_bytes)

        result = await er_client.get_subjects_kml()
        assert route.called
        assert isinstance(result, httpx.Response)
        assert result.content == kmz_bytes
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_kml_with_dates(er_client):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/subjects/kml"
        ).respond(httpx.codes.OK, content=b"KMZ")

        await er_client.get_subjects_kml(start="2024-01-01", end="2024-06-01")
        assert route.called
        req = route.calls[0].request
        assert "start=2024-01-01" in str(req.url)
        assert "end=2024-06-01" in str(req.url)
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_kml(er_client):
    kmz_bytes = b"PK\x03\x04mock-kmz-subject"
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/subject/{SUBJECT_ID}/kml"
        ).respond(httpx.codes.OK, content=kmz_bytes)

        result = await er_client.get_subject_kml(subject_id=SUBJECT_ID)
        assert route.called
        assert isinstance(result, httpx.Response)
        assert result.content == kmz_bytes
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_kml_with_dates(er_client):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/subject/{SUBJECT_ID}/kml"
        ).respond(httpx.codes.OK, content=b"KMZ")

        await er_client.get_subject_kml(
            subject_id=SUBJECT_ID, start="2024-03-01", end="2024-09-01"
        )
        assert route.called
        req = route.calls[0].request
        assert "start=2024-03-01" in str(req.url)
        assert "end=2024-09-01" in str(req.url)
        await er_client.close()


# --- Vector tile tests ---

@pytest.mark.asyncio
async def test_get_observation_segment_tiles(er_client):
    pbf_bytes = b"\x1a\x02\x00\x00mock-pbf"
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/observations/segments/tiles/10/512/512.pbf"
        ).respond(httpx.codes.OK, content=pbf_bytes)

        result = await er_client.get_observation_segment_tiles(z=10, x=512, y=512)
        assert route.called
        assert isinstance(result, httpx.Response)
        assert result.content == pbf_bytes
        await er_client.close()


@pytest.mark.asyncio
async def test_get_spatial_feature_tiles(er_client):
    pbf_bytes = b"\x1a\x02\x00\x00mock-spatial-pbf"
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/spatialfeatures/tiles/8/128/256.pbf"
        ).respond(httpx.codes.OK, content=pbf_bytes)

        result = await er_client.get_spatial_feature_tiles(z=8, x=128, y=256)
        assert route.called
        assert isinstance(result, httpx.Response)
        assert result.content == pbf_bytes
        await er_client.close()


@pytest.mark.asyncio
async def test_get_observation_segment_tiles_with_params(er_client):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/observations/segments/tiles/10/512/512.pbf"
        ).respond(httpx.codes.OK, content=b"PBF")

        await er_client.get_observation_segment_tiles(
            z=10, x=512, y=512, show_excluded="true"
        )
        assert route.called
        req = route.calls[0].request
        assert "show_excluded=true" in str(req.url)
        await er_client.close()


# --- Error handling tests ---

@pytest.mark.asyncio
async def test_get_events_geojson_not_found(er_client):
    from erclient.er_errors import ERClientNotFound
    async with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(
            f"{SERVICE_ROOT}/activity/events/geojson"
        ).respond(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})

        with pytest.raises(ERClientNotFound):
            await er_client.get_events_geojson()
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_kml_not_found(er_client):
    from erclient.er_errors import ERClientNotFound
    async with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(
            f"{SERVICE_ROOT}/subjects/kml"
        ).respond(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})

        with pytest.raises(ERClientNotFound):
            await er_client.get_subjects_kml()
        await er_client.close()


@pytest.mark.asyncio
async def test_get_tiles_not_found(er_client):
    from erclient.er_errors import ERClientNotFound
    async with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(
            f"{SERVICE_ROOT}/observations/segments/tiles/10/512/512.pbf"
        ).respond(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})

        with pytest.raises(ERClientNotFound):
            await er_client.get_observation_segment_tiles(z=10, x=512, y=512)
        await er_client.close()
