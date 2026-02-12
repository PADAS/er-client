from datetime import datetime, timezone

import httpx
import pytest
import respx

from erclient import (ERClientBadCredentials, ERClientException,
                      ERClientNotFound, ERClientPermissionDenied)


@pytest.fixture
def subject_tracks_response():
    """Sample response for subject tracks"""
    return {
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [36.7922397, -1.2932121],
                            [36.7921529, -1.2931406],
                            [36.7919254, -1.2931796],
                        ],
                    },
                    "properties": {
                        "title": "Elephant Alpha",
                        "subject_id": "d8ad9955-8301-43c4-9000-9a02f1cba675",
                        "coordinateProperties": {
                            "times": [
                                "2025-01-10T06:01:06+00:00",
                                "2025-01-10T06:02:08+00:00",
                                "2025-01-10T06:02:30+00:00",
                            ]
                        },
                    },
                }
            ],
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def empty_tracks_response():
    return {
        "data": {
            "type": "FeatureCollection",
            "features": [],
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.mark.asyncio
async def test_get_subject_tracks_success(er_client, subject_tracks_response):
    """Test get_subject_tracks returns track data"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}/tracks")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subject_tracks_response
        )

        result = await er_client.get_subject_tracks(subject_id)

        assert result == subject_tracks_response["data"]
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_empty(er_client, empty_tracks_response):
    """Test get_subject_tracks with no tracks"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}/tracks")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=empty_tracks_response
        )

        result = await er_client.get_subject_tracks(subject_id)

        assert result["features"] == []
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_with_date_range(er_client, subject_tracks_response):
    """Test get_subject_tracks passes since/until params from datetime objects"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}/tracks")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subject_tracks_response
        )

        start = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 11, 0, 0, 0, tzinfo=timezone.utc)

        result = await er_client.get_subject_tracks(subject_id, start=start, end=end)

        assert result == subject_tracks_response["data"]
        assert route.called
        request = route.calls.last.request
        assert b"since=" in request.url.query
        assert b"until=" in request.url.query
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_with_start_only(er_client, subject_tracks_response):
    """Test get_subject_tracks with only start date"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}/tracks")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subject_tracks_response
        )

        start = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)

        result = await er_client.get_subject_tracks(subject_id, start=start)

        assert result == subject_tracks_response["data"]
        assert route.called
        request = route.calls.last.request
        assert b"since=" in request.url.query
        assert b"until=" not in request.url.query
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_no_date_params(er_client, subject_tracks_response):
    """Test get_subject_tracks without date params sends no since/until"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}/tracks")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subject_tracks_response
        )

        result = await er_client.get_subject_tracks(subject_id)

        assert route.called
        request = route.calls.last.request
        # No query params should be set for empty dict
        assert b"since=" not in (request.url.query or b"")
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_not_found(er_client):
    """Test get_subject_tracks raises ERClientNotFound on 404"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "nonexistent-id"
        route = respx_mock.get(f"subject/{subject_id}/tracks")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.get_subject_tracks(subject_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_unauthorized(er_client):
    """Test get_subject_tracks raises ERClientBadCredentials on 401"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}/tracks")
        route.return_value = httpx.Response(httpx.codes.UNAUTHORIZED, json={})

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_subject_tracks(subject_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_forbidden(er_client):
    """Test get_subject_tracks raises ERClientPermissionDenied on 403"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}/tracks")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_subject_tracks(subject_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_tracks_network_error(er_client):
    """Test get_subject_tracks raises ERClientException on network error"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}/tracks")
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            await er_client.get_subject_tracks(subject_id)

        assert route.called
        await er_client.close()
