import io
import json
import re

import httpx
import pytest
import respx

from erclient import (
    ERClientException,
    ERClientNotFound,
    ERClientPermissionDenied,
    ERClientServiceUnreachable,
)


SOURCE_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
TASK_ID = "f9e8d7c6-b5a4-3210-fedc-ba9876543210"


@pytest.fixture
def gpx_file_content():
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Track</name>
    <trkseg>
      <trkpt lat="-1.293" lon="36.792">
        <time>2026-01-15T10:00:00Z</time>
      </trkpt>
      <trkpt lat="-1.294" lon="36.793">
        <time>2026-01-15T10:01:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


@pytest.fixture
def gpx_file(gpx_file_content):
    return io.BytesIO(gpx_file_content)


@pytest.fixture
def gpx_upload_response():
    return {
        "data": {
            "source_id": SOURCE_ID,
            "filename": "track.gpx",
            "filesize_bytes": 512,
            "process_status": {
                "task_info": None,
                "task_id": TASK_ID,
                "task_success": False,
                "task_failed": False,
                "task_url": f"https://fake-site.erdomain.org/api/v1.0/source/{SOURCE_ID}/gpxdata/status/{TASK_ID}",
            },
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def gpx_status_pending_response():
    return {
        "data": {
            "task_result": None,
            "task_status": "Pending",
            "task_success": False,
            "task_failed": False,
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def gpx_status_success_response():
    return {
        "data": {
            "task_result": {"observations_created": 42},
            "task_status": "Success",
            "task_success": True,
            "task_failed": False,
        },
        "status": {"code": 200, "message": "OK"},
    }


# ---- upload_gpx tests ----


@pytest.mark.asyncio
async def test_upload_gpx_with_file_object_success(er_client, gpx_file, gpx_upload_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f"source/{SOURCE_ID}/gpxdata")
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=gpx_upload_response
        )
        response = await er_client.upload_gpx(source_id=SOURCE_ID, file=gpx_file)
        assert route.called
        assert response == gpx_upload_response["data"]
        assert response["process_status"]["task_id"] == TASK_ID
        await er_client.close()


@pytest.mark.asyncio
async def test_upload_gpx_with_filepath_success(er_client, gpx_file_content, gpx_upload_response, tmp_path):
    gpx_path = tmp_path / "test_track.gpx"
    gpx_path.write_bytes(gpx_file_content)

    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f"source/{SOURCE_ID}/gpxdata")
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=gpx_upload_response
        )
        response = await er_client.upload_gpx(source_id=SOURCE_ID, filepath=str(gpx_path))
        assert route.called
        assert response == gpx_upload_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_upload_gpx_no_file_raises_error(er_client):
    with pytest.raises(ValueError, match="Either filepath or file must be provided"):
        await er_client.upload_gpx(source_id=SOURCE_ID)
    await er_client.close()


@pytest.mark.asyncio
async def test_upload_gpx_not_found(er_client, gpx_file):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f"source/{SOURCE_ID}/gpxdata")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "source not found"}},
        )
        with pytest.raises(ERClientNotFound):
            await er_client.upload_gpx(source_id=SOURCE_ID, file=gpx_file)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_upload_gpx_forbidden(er_client, gpx_file):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        path = f"source/{SOURCE_ID}/gpxdata"
        route = respx_mock.post(path)
        forbidden_response = {
            "data": [],
            "status": {
                "code": 403,
                "message": "Forbidden",
                "detail": "You do not have permission to perform this action.",
            },
        }
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json=forbidden_response
        )
        with pytest.raises(ERClientPermissionDenied) as exc_info:
            await er_client.upload_gpx(source_id=SOURCE_ID, file=gpx_file)
        assert exc_info.value.status_code == httpx.codes.FORBIDDEN
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_upload_gpx_timeout(er_client, gpx_file):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f"source/{SOURCE_ID}/gpxdata")
        route.side_effect = httpx.ConnectTimeout
        with pytest.raises(ERClientException):
            await er_client.upload_gpx(source_id=SOURCE_ID, file=gpx_file)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_upload_gpx_gateway_timeout(er_client, gpx_file):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        path = f"source/{SOURCE_ID}/gpxdata"
        route = respx_mock.post(path)
        route.return_value = httpx.Response(
            httpx.codes.GATEWAY_TIMEOUT, json={}
        )
        expected_error = f"ER Gateway Timeout ON POST {er_client.service_root}/{path}. (status_code=504) (response_body={{}})"
        with pytest.raises(ERClientServiceUnreachable, match=re.escape(expected_error)):
            await er_client.upload_gpx(source_id=SOURCE_ID, file=gpx_file)
        assert route.called
        await er_client.close()


# ---- get_gpx_upload_status tests ----


@pytest.mark.asyncio
async def test_get_gpx_upload_status_pending(er_client, gpx_status_pending_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"source/{SOURCE_ID}/gpxdata/status/{TASK_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=gpx_status_pending_response
        )
        response = await er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)
        assert route.called
        assert response == gpx_status_pending_response["data"]
        assert response["task_status"] == "Pending"
        assert response["task_success"] is False
        await er_client.close()


@pytest.mark.asyncio
async def test_get_gpx_upload_status_success(er_client, gpx_status_success_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"source/{SOURCE_ID}/gpxdata/status/{TASK_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=gpx_status_success_response
        )
        response = await er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)
        assert route.called
        assert response == gpx_status_success_response["data"]
        assert response["task_status"] == "Success"
        assert response["task_success"] is True
        assert response["task_result"]["observations_created"] == 42
        await er_client.close()


@pytest.mark.asyncio
async def test_get_gpx_upload_status_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"source/{SOURCE_ID}/gpxdata/status/{TASK_ID}")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "not found"}},
        )
        with pytest.raises(ERClientNotFound):
            await er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_gpx_upload_status_forbidden(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        path = f"source/{SOURCE_ID}/gpxdata/status/{TASK_ID}"
        route = respx_mock.get(path)
        forbidden_response = {
            "data": [],
            "status": {
                "code": 403,
                "message": "Forbidden",
                "detail": "You do not have permission to perform this action.",
            },
        }
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json=forbidden_response
        )
        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_gpx_upload_status_timeout(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"source/{SOURCE_ID}/gpxdata/status/{TASK_ID}")
        route.side_effect = httpx.ReadTimeout
        with pytest.raises(ERClientException):
            await er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)
        assert route.called
        await er_client.close()
