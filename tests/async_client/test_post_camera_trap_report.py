import json
import re

import httpx
import pytest
import respx

from erclient import (ERClientException, ERClientNotFound,
                      ERClientPermissionDenied, ERClientServiceUnreachable)


@pytest.mark.asyncio
async def test_post_camera_trap_report_success(er_client, camera_trap_payload, camera_trap_file, camera_trap_report_created_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a successful response
        route = respx_mock.post(
            f'sensors/camera-trap/{er_client.provider_key}/status/')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=camera_trap_report_created_response)
        # Send a camera trap event using the async client
        response = await er_client.post_camera_trap_report(camera_trap_payload, camera_trap_file)
        assert route.called  # Check that the api endpoint was called
        assert response == camera_trap_report_created_response['data']
        await er_client.close()
        camera_trap_file.close()


@pytest.mark.asyncio
async def test_post_camera_trap_report_status_conflict(er_client, camera_trap_payload, camera_trap_file, camera_trap_conflict_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a "conflict" (409) response
        # This status is returned when a file with the same name already exists in ER
        route = respx_mock.post(
            f'sensors/camera-trap/{er_client.provider_key}/status/')
        route.return_value = httpx.Response(
            httpx.codes.CONFLICT, json=camera_trap_conflict_response)
        # Check that the right exception is raised by the client
        with pytest.raises(ERClientException):
            await er_client.post_camera_trap_report(camera_trap_payload, camera_trap_file)
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_camera_trap_report_connect_timeout(er_client, camera_trap_payload, camera_trap_file):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a connection timeout error
        route = respx_mock.post(
            f'sensors/camera-trap/{er_client.provider_key}/status/')
        route.side_effect = httpx.ConnectTimeout
        # Check that the right exception is raised by the client
        with pytest.raises(ERClientException):
            await er_client.post_camera_trap_report(camera_trap_payload, camera_trap_file)
            assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_camera_trap_report_response_timeout(er_client, camera_trap_payload, camera_trap_file):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a read timeout error
        route = respx_mock.post(
            f'sensors/camera-trap/{er_client.provider_key}/status/')
        route.side_effect = httpx.ReadTimeout
        # Check that the right exception is raised by the client
        with pytest.raises(ERClientException):
            await er_client.post_camera_trap_report(camera_trap_payload, camera_trap_file)
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_camera_trap_report_status_gateway_timeout(er_client, camera_trap_payload, camera_trap_file):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a gateway timeout
        path = f'sensors/camera-trap/{er_client.provider_key}/status/'
        route = respx_mock.post(path)
        route.return_value = httpx.Response(httpx.codes.GATEWAY_TIMEOUT, json={})
        # Check that the right exception is raised by the client
        expected_error = f'ER Gateway Timeout ON POST {er_client.service_root}/{path}. (status_code=504) (response_body={{}})'
        with pytest.raises(ERClientServiceUnreachable, match=re.escape(expected_error)):
            await er_client.post_camera_trap_report(camera_trap_payload, camera_trap_file)
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_camera_trap_report_status_bad_gateway(er_client, camera_trap_payload, camera_trap_file):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a bad gateway error
        path = f'sensors/camera-trap/{er_client.provider_key}/status/'
        route = respx_mock.post(path)
        route.return_value = httpx.Response(httpx.codes.BAD_GATEWAY, json={})
        # Check that the right exception is raised by the client
        expected_error = f'ER Bad Gateway ON POST {er_client.service_root}/{path}. (status_code=502) (response_body={{}})'
        with pytest.raises(ERClientServiceUnreachable, match=re.escape(expected_error)) as exc_info:
            await er_client.post_camera_trap_report(camera_trap_payload, camera_trap_file)
        assert exc_info.value.status_code == httpx.codes.BAD_GATEWAY
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_camera_trap_report_status_bad_request(er_client, camera_trap_payload, camera_trap_file, bad_request_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a client error
        route = respx_mock.post(
            f'sensors/camera-trap/{er_client.provider_key}/status/')
        route.return_value = httpx.Response(
            httpx.codes.BAD_REQUEST, json=bad_request_response)
        # Check that the right exception is raised by the client
        with pytest.raises(ERClientException) as e:
            await er_client.post_camera_trap_report(camera_trap_payload, camera_trap_file)
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_camera_trap_report_status_forbidden(er_client, camera_trap_payload, camera_trap_file, forbidden_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a permissions error
        path = f'sensors/camera-trap/{er_client.provider_key}/status/'
        route = respx_mock.post(path)
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json=forbidden_response)
        # Check that the right exception is raised by the client
        expected_message = f'ER Forbidden ON POST {er_client.service_root}/{path}. (status_code={httpx.codes.FORBIDDEN}) (response_body={json.dumps(forbidden_response)})'
        with pytest.raises(ERClientPermissionDenied, match=re.escape(expected_message)) as exc_info:
            await er_client.post_camera_trap_report(camera_trap_payload, camera_trap_file)
        assert exc_info.value.status_code == httpx.codes.FORBIDDEN
        assert exc_info.value.response_body == json.dumps(forbidden_response)
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_camera_trap_report_status_not_found(er_client, camera_trap_payload, camera_trap_file, not_found_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a not found response
        route = respx_mock.post(
            f'sensors/camera-trap/{er_client.provider_key}/status/')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json=not_found_response)
        # Check that the right exception is raised by the client
        with pytest.raises(ERClientNotFound):
            await er_client.post_camera_trap_report(camera_trap_payload, camera_trap_file)
        assert route.called  # Check that the api endpoint was called
        await er_client.close()
