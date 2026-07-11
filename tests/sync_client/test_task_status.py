"""Tests for get_task_status in the sync ERClient."""
import json
from unittest.mock import patch, MagicMock

import pytest


SERVICE_ROOT = "https://fake-site.erdomain.org/api/v1.0"
TASK_ID = "abc12345-def6-7890-ghij-klmnopqrstuv"


def _mock_response(json_data=None, status_code=200, ok=True):
    """Helper to build a mock requests.Response."""
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    resp.text = json.dumps(json_data) if json_data is not None else ""
    resp.json.return_value = json_data
    return resp


@pytest.fixture
def task_pending_response():
    return {
        "data": {
            "task_id": TASK_ID,
            "status": "PENDING",
            "result": None,
            "location": f"/api/v1.0/core/taskstatus/{TASK_ID}/",
        }
    }


@pytest.fixture
def task_success_response():
    return {
        "data": {
            "task_id": TASK_ID,
            "status": "SUCCESS",
            "result": {"imported": 42, "errors": 0},
            "location": f"/api/v1.0/core/taskstatus/{TASK_ID}/",
        }
    }


@pytest.fixture
def task_failure_response():
    return {
        "data": {
            "task_id": TASK_ID,
            "status": "FAILURE",
            "result": "File format not recognized",
            "location": f"/api/v1.0/core/taskstatus/{TASK_ID}/",
        }
    }


@pytest.fixture
def task_started_response():
    return {
        "data": {
            "task_id": TASK_ID,
            "status": "STARTED",
            "result": None,
            "location": f"/api/v1.0/core/taskstatus/{TASK_ID}/",
        }
    }


def test_get_task_status_pending(er_client, task_pending_response):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(task_pending_response)
        result = er_client.get_task_status(TASK_ID)

        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert f"core/taskstatus/{TASK_ID}/" in call_url
        assert result["task_id"] == TASK_ID
        assert result["status"] == "PENDING"
        assert result["result"] is None


def test_get_task_status_success(er_client, task_success_response):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(task_success_response)
        result = er_client.get_task_status(TASK_ID)

        assert result["status"] == "SUCCESS"
        assert result["result"]["imported"] == 42


def test_get_task_status_failure(er_client, task_failure_response):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(task_failure_response)
        result = er_client.get_task_status(TASK_ID)

        assert result["status"] == "FAILURE"
        assert result["result"] == "File format not recognized"


def test_get_task_status_started(er_client, task_started_response):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(task_started_response)
        result = er_client.get_task_status(TASK_ID)

        assert result["status"] == "STARTED"


def test_get_task_status_url_construction(er_client, task_pending_response):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(task_pending_response)
        er_client.get_task_status(TASK_ID)

        call_url = mock_get.call_args[0][0]
        assert call_url == f"{SERVICE_ROOT}/core/taskstatus/{TASK_ID}/"


def test_get_task_status_not_found(er_client):
    from erclient.er_errors import ERClientNotFound
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(status_code=404, ok=False)
        with pytest.raises(ERClientNotFound):
            er_client.get_task_status("nonexistent-task-id")
