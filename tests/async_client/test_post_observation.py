import json
import re
from datetime import datetime, timezone

import httpx
import pytest
import respx

from erclient import (ERClientException, ERClientNotFound,
                      ERClientPermissionDenied, ERClientServiceUnreachable)


@pytest.mark.asyncio
async def test_post_observation_single_success(er_client, position, position_created_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('/observations')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=position_created_response)
        response = await er_client.post_observation(position)
        assert route.called
        assert response == {}
        await er_client.close()


@pytest.mark.asyncio
async def test_post_observation_list_success(er_client, position, position_created_response):
    observations = [position, {**position, "manufacturer_id": "018910981"}]
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('/observations')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=position_created_response)
        response = await er_client.post_observation(observations)
        assert route.called
        # verify we sent a list payload
        request_body = json.loads(route.calls[0].request.content)
        assert isinstance(request_body, list)
        assert len(request_body) == 2
        await er_client.close()


@pytest.mark.asyncio
async def test_post_observation_cleans_datetime(er_client, position_created_response):
    """Verify that datetime objects in recorded_at are converted to ISO strings."""
    dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    observation = {
        "manufacturer_id": "018910980",
        "source_type": "tracking-device",
        "subject_name": "Test Truck",
        "recorded_at": dt,
        "location": {"lon": 35.43903, "lat": -1.59083},
    }
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('/observations')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=position_created_response)
        await er_client.post_observation(observation)
        request_body = json.loads(route.calls[0].request.content)
        assert isinstance(request_body['recorded_at'], str)
        assert request_body['recorded_at'] == dt.isoformat()
        await er_client.close()


@pytest.mark.asyncio
async def test_post_observation_connect_timeout(er_client, position):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('/observations')
        route.side_effect = httpx.ConnectTimeout
        with pytest.raises(ERClientException):
            await er_client.post_observation(position)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_observation_not_found(er_client, position, not_found_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('/observations')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json=not_found_response)
        with pytest.raises(ERClientNotFound):
            await er_client.post_observation(position)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_observation_forbidden(er_client, position, forbidden_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        path = 'observations'
        route = respx_mock.post(path)
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json=forbidden_response)
        with pytest.raises(ERClientPermissionDenied) as exc_info:
            await er_client.post_observation(position)
        assert exc_info.value.status_code == httpx.codes.FORBIDDEN
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_observation_conflict(er_client, position, conflict_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('/observations')
        route.return_value = httpx.Response(
            httpx.codes.CONFLICT, json=conflict_response)
        with pytest.raises(ERClientException) as exc_info:
            await er_client.post_observation(position)
        assert exc_info.value.status_code == httpx.codes.CONFLICT
        assert route.called
        await er_client.close()
