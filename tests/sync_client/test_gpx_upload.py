import io
import json
from unittest.mock import patch, MagicMock

import pytest
import requests

from erclient import (
    ERClientException,
    ERClientNotFound,
    ERClientPermissionDenied,
)
from erclient.client import ERClient

from .conftest import _mock_response


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


# ---- upload_gpx tests (sync) ----


class TestUploadGpx:
    def test_upload_gpx_with_file_object_success(self, er_client, gpx_file, gpx_upload_response):
        mock_resp = _mock_response(201, json_data=gpx_upload_response)
        with patch.object(requests, "post", return_value=mock_resp) as mock_post:
            result = er_client.upload_gpx(source_id=SOURCE_ID, file=gpx_file)
            assert mock_post.called
            assert result == gpx_upload_response["data"]
            assert result["process_status"]["task_id"] == TASK_ID

    def test_upload_gpx_with_filepath_success(self, er_client, gpx_file_content, gpx_upload_response, tmp_path):
        gpx_path = tmp_path / "test_track.gpx"
        gpx_path.write_bytes(gpx_file_content)

        mock_resp = _mock_response(201, json_data=gpx_upload_response)
        with patch.object(requests, "post", return_value=mock_resp) as mock_post:
            result = er_client.upload_gpx(source_id=SOURCE_ID, filepath=str(gpx_path))
            assert mock_post.called
            assert result == gpx_upload_response["data"]

    def test_upload_gpx_no_file_raises_error(self, er_client):
        with pytest.raises(ValueError, match="Either filepath or file must be provided"):
            er_client.upload_gpx(source_id=SOURCE_ID)

    def test_upload_gpx_not_found(self, er_client, gpx_file):
        not_found = {"status": {"code": 404, "detail": "source not found"}}
        mock_resp = _mock_response(404, json_data=not_found)
        with patch.object(requests, "post", return_value=mock_resp):
            with pytest.raises(ERClientNotFound):
                er_client.upload_gpx(source_id=SOURCE_ID, file=gpx_file)

    def test_upload_gpx_forbidden(self, er_client, gpx_file):
        forbidden = {
            "status": {
                "code": 403,
                "detail": "You do not have permission to perform this action.",
            }
        }
        mock_resp = _mock_response(403, json_data=forbidden)
        with patch.object(requests, "post", return_value=mock_resp):
            with pytest.raises(ERClientPermissionDenied):
                er_client.upload_gpx(source_id=SOURCE_ID, file=gpx_file)

    def test_upload_gpx_server_error(self, er_client, gpx_file):
        error_resp = {"status": {"code": 500, "message": "Internal Server Error"}}
        mock_resp = _mock_response(500, json_data=error_resp)
        with patch.object(requests, "post", return_value=mock_resp):
            with pytest.raises(ERClientException):
                er_client.upload_gpx(source_id=SOURCE_ID, file=gpx_file)


# ---- get_gpx_upload_status tests (sync) ----


class TestGetGpxUploadStatus:
    def test_get_gpx_upload_status_pending(self, er_client, gpx_status_pending_response):
        mock_resp = _mock_response(200, json_data=gpx_status_pending_response)
        with patch.object(er_client._http_session, "get", return_value=mock_resp):
            result = er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)
            assert result == gpx_status_pending_response["data"]
            assert result["task_status"] == "Pending"
            assert result["task_success"] is False

    def test_get_gpx_upload_status_success(self, er_client, gpx_status_success_response):
        mock_resp = _mock_response(200, json_data=gpx_status_success_response)
        with patch.object(er_client._http_session, "get", return_value=mock_resp):
            result = er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)
            assert result == gpx_status_success_response["data"]
            assert result["task_status"] == "Success"
            assert result["task_success"] is True
            assert result["task_result"]["observations_created"] == 42

    def test_get_gpx_upload_status_not_found(self, er_client):
        not_found = {"status": {"code": 404, "detail": "not found"}}
        mock_resp = _mock_response(404, json_data=not_found)
        with patch.object(er_client._http_session, "get", return_value=mock_resp):
            with pytest.raises(ERClientNotFound):
                er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)

    def test_get_gpx_upload_status_forbidden(self, er_client):
        forbidden = {
            "status": {
                "code": 403,
                "detail": "You do not have permission to perform this action.",
            }
        }
        mock_resp = _mock_response(403, json_data=forbidden)
        with patch.object(er_client._http_session, "get", return_value=mock_resp):
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)

    def test_get_gpx_upload_status_server_error(self, er_client):
        error_resp = {"status": {"code": 500, "message": "Internal Server Error"}}
        mock_resp = _mock_response(500, json_data=error_resp)
        with patch.object(er_client._http_session, "get", return_value=mock_resp):
            with pytest.raises(ERClientException):
                er_client.get_gpx_upload_status(source_id=SOURCE_ID, task_id=TASK_ID)
