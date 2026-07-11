import re

import httpx
import pytest
import respx

from erclient import ERClientException, ERClientNotFound


V2_SERVICE_ROOT = "https://fake-site.erdomain.org/api/v2.0"


@pytest.fixture
def schema_response():
    return {
        "type": "object",
        "properties": {
            "amount_mm": {"type": "number", "title": "Amount (mm)"},
            "height_m": {"type": "number", "title": "Height (m)"},
        },
    }


@pytest.fixture
def schema_error_response():
    return {
        "errors": [
            {"code": "schema_not_found", "detail": "No schema found for event type."}
        ]
    }


@pytest.fixture
def schemas_bulk_response():
    return {
        "count": 2,
        "results": [
            {
                "status": "success",
                "event_type": "rainfall_rep",
                "schema": {"type": "object", "properties": {}},
            },
            {
                "status": "success",
                "event_type": "fire_rep",
                "schema": {"type": "object", "properties": {}},
            },
        ],
    }


@pytest.fixture
def updates_response():
    return {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "sequence": 2,
                "data": {"display": "Rainfall v2"},
                "created_at": "2025-01-15T10:00:00Z",
            },
            {
                "sequence": 1,
                "data": {"display": "Rainfall"},
                "created_at": "2025-01-10T10:00:00Z",
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_event_type_schema_success(er_client, schema_response):
    async with respx.mock(
        base_url=V2_SERVICE_ROOT, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("/eventtypes/rainfall_rep/schema").mock(
            return_value=httpx.Response(httpx.codes.OK, json={"data": schema_response})
        )
        result = await er_client.get_event_type_schema("rainfall_rep")
        assert route.called
        assert result == schema_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_type_schema_with_pre_render(er_client, schema_response):
    async with respx.mock(
        base_url=V2_SERVICE_ROOT, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("/eventtypes/rainfall_rep/schema").mock(
            return_value=httpx.Response(httpx.codes.OK, json={"data": schema_response})
        )
        result = await er_client.get_event_type_schema("rainfall_rep", pre_render=True)
        assert route.called
        # verify the pre_render param was sent
        request = route.calls[0].request
        assert "pre_render" in str(request.url)
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_type_schema_not_found(er_client, schema_error_response):
    async with respx.mock(
        base_url=V2_SERVICE_ROOT, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("/eventtypes/nonexistent/schema").mock(
            return_value=httpx.Response(httpx.codes.NOT_FOUND, json=schema_error_response)
        )
        with pytest.raises(ERClientNotFound):
            await er_client.get_event_type_schema("nonexistent")
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_type_updates_success(er_client, updates_response):
    async with respx.mock(
        base_url=V2_SERVICE_ROOT, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("/eventtypes/rainfall_rep/updates").mock(
            return_value=httpx.Response(httpx.codes.OK, json=updates_response)
        )
        result = await er_client.get_event_type_updates("rainfall_rep")
        assert route.called
        # response has no 'data' key, so the full dict is returned
        assert result["count"] == 2
        assert len(result["results"]) == 2
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_type_updates_not_found(er_client):
    async with respx.mock(
        base_url=V2_SERVICE_ROOT, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("/eventtypes/nonexistent/updates").mock(
            return_value=httpx.Response(httpx.codes.NOT_FOUND, json={})
        )
        with pytest.raises(ERClientNotFound):
            await er_client.get_event_type_updates("nonexistent")
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_type_schemas_bulk_success(er_client, schemas_bulk_response):
    async with respx.mock(
        base_url=V2_SERVICE_ROOT, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("/eventtypes/schemas").mock(
            return_value=httpx.Response(httpx.codes.OK, json=schemas_bulk_response)
        )
        result = await er_client.get_event_type_schemas()
        assert route.called
        assert result["count"] == 2
        assert len(result["results"]) == 2
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_type_schemas_bulk_with_pre_render(er_client, schemas_bulk_response):
    async with respx.mock(
        base_url=V2_SERVICE_ROOT, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("/eventtypes/schemas").mock(
            return_value=httpx.Response(httpx.codes.OK, json=schemas_bulk_response)
        )
        result = await er_client.get_event_type_schemas(pre_render=True)
        assert route.called
        request = route.calls[0].request
        assert "pre_render" in str(request.url)
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_type_schema_connect_timeout(er_client):
    async with respx.mock(
        base_url=V2_SERVICE_ROOT, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("/eventtypes/rainfall_rep/schema")
        route.side_effect = httpx.ConnectTimeout
        with pytest.raises(ERClientException):
            await er_client.get_event_type_schema("rainfall_rep")
        assert route.called
        await er_client.close()
