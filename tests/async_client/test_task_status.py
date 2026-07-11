"""Tests for get_task_status in the async AsyncERClient."""
import httpx
import pytest
import respx


SERVICE_ROOT = "https://fake-site.erdomain.org/api/v1.0"
TASK_ID = "abc12345-def6-7890-ghij-klmnopqrstuv"


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


@pytest.mark.asyncio
async def test_get_task_status_pending(er_client, task_pending_response):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/core/taskstatus/{TASK_ID}/"
        ).respond(httpx.codes.OK, json=task_pending_response)

        result = await er_client.get_task_status(TASK_ID)
        assert route.called
        assert result["task_id"] == TASK_ID
        assert result["status"] == "PENDING"
        assert result["result"] is None
        await er_client.close()


@pytest.mark.asyncio
async def test_get_task_status_success(er_client, task_success_response):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/core/taskstatus/{TASK_ID}/"
        ).respond(httpx.codes.OK, json=task_success_response)

        result = await er_client.get_task_status(TASK_ID)
        assert route.called
        assert result["status"] == "SUCCESS"
        assert result["result"]["imported"] == 42
        await er_client.close()


@pytest.mark.asyncio
async def test_get_task_status_failure(er_client, task_failure_response):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/core/taskstatus/{TASK_ID}/"
        ).respond(httpx.codes.OK, json=task_failure_response)

        result = await er_client.get_task_status(TASK_ID)
        assert route.called
        assert result["status"] == "FAILURE"
        assert result["result"] == "File format not recognized"
        await er_client.close()


@pytest.mark.asyncio
async def test_get_task_status_started(er_client, task_started_response):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/core/taskstatus/{TASK_ID}/"
        ).respond(httpx.codes.OK, json=task_started_response)

        result = await er_client.get_task_status(TASK_ID)
        assert route.called
        assert result["status"] == "STARTED"
        await er_client.close()


@pytest.mark.asyncio
async def test_get_task_status_not_found(er_client):
    from erclient.er_errors import ERClientNotFound
    async with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(
            f"{SERVICE_ROOT}/core/taskstatus/nonexistent-task-id/"
        ).respond(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})

        with pytest.raises(ERClientNotFound):
            await er_client.get_task_status("nonexistent-task-id")
        await er_client.close()


@pytest.mark.asyncio
async def test_get_task_status_url_construction(er_client, task_pending_response):
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(
            f"{SERVICE_ROOT}/core/taskstatus/{TASK_ID}/"
        ).respond(httpx.codes.OK, json=task_pending_response)

        await er_client.get_task_status(TASK_ID)
        assert route.called
        req = route.calls[0].request
        assert str(req.url).startswith(f"{SERVICE_ROOT}/core/taskstatus/{TASK_ID}/")
        await er_client.close()
