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
    ERClientBadCredentials,
)


@pytest.mark.asyncio
async def test_post_report_success(er_client, report, report_created_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a successful response
        route = respx_mock.post('activity/events')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=report_created_response)
        # Send an event using the async client
        response = await er_client.post_report(report)
        assert route.called  # Check that the api endpoint was called
        assert response == report_created_response['data']
        await er_client.close()


@pytest.mark.asyncio
async def test_post_report_connect_timeout(er_client, report):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a connection timeout error
        route = respx_mock.post('activity/events')
        route.side_effect = httpx.ConnectTimeout
        # Check that the right exception is raised by the client
        with pytest.raises(ERClientException):
            await er_client.post_report(report)
            assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_report_response_timeout(er_client, report):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a read timeout error
        route = respx_mock.post('activity/events')
        route.side_effect = httpx.ReadTimeout
        # Check that the right exception is raised by the client
        with pytest.raises(ERClientException):
            await er_client.post_report(report)
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_report_status_gateway_timeout(er_client, report):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a gateway timeout
        path = 'activity/events'
        route = respx_mock.post(path)
        route.return_value = httpx.Response(httpx.codes.GATEWAY_TIMEOUT, json={})
        # Check that the right exception is raised by the client
        expected_msg = f'ER Gateway Timeout ON POST {er_client.service_root}/{path}. (status_code={httpx.codes.GATEWAY_TIMEOUT}) (response_body={{}})'
        with pytest.raises(ERClientServiceUnreachable, match=re.escape(expected_msg)) as exc_info:
            await er_client.post_report(report)
        assert exc_info.value.status_code == httpx.codes.GATEWAY_TIMEOUT
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_report_status_bad_gateway(er_client, report):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a bad gateway error
        path = 'activity/events'
        route = respx_mock.post(path)
        route.return_value = httpx.Response(httpx.codes.BAD_GATEWAY, json={})
        # Check that the right exception is raised by the client
        expected_msg = f'ER Bad Gateway ON POST {er_client.service_root}/{path}. (status_code={httpx.codes.BAD_GATEWAY}) (response_body={{}})'
        with pytest.raises(ERClientServiceUnreachable, match=re.escape(expected_msg)) as exc_info:
            await er_client.post_report(report)
        assert exc_info.value.status_code == httpx.codes.BAD_GATEWAY
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_report_status_bad_request(er_client, report, bad_request_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a missing event type error
        route = respx_mock.post('activity/events')
        response_data = bad_request_response
        route.return_value = httpx.Response(
            httpx.codes.BAD_REQUEST,
            json=response_data
        )
        # Check that the right exception is raised by the client
        expected_message = f'ER Bad Request ON POST {er_client.service_root}/activity/events. (status_code={httpx.codes.BAD_REQUEST}) (response_body={json.dumps(response_data)})'
        with pytest.raises(ERClientException, match=re.escape(expected_message)) as exc_info:
            await er_client.post_report(report)
        assert exc_info.value.status_code == httpx.codes.BAD_REQUEST
        assert exc_info.value.response_body == json.dumps(response_data)  # The response body must be stored
        assert route.called


@pytest.mark.asyncio
async def test_post_report_status_forbidden(er_client, report, forbidden_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a permissions error
        route = respx_mock.post('activity/events')
        response_data = forbidden_response
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN,
            json=response_data
        )
        # Check that the right exception is raised by the client
        expected_message = f'ER Forbidden ON POST {er_client.service_root}/activity/events. (status_code={httpx.codes.FORBIDDEN}) (response_body={json.dumps(response_data)})'
        with pytest.raises(ERClientPermissionDenied, match=re.escape(expected_message)) as exc_info:
            await er_client.post_report(report)
        assert exc_info.value.status_code == httpx.codes.FORBIDDEN
        assert exc_info.value.response_body == json.dumps(response_data)
        assert route.called


@pytest.mark.asyncio
async def test_post_report_status_not_found(er_client, report, not_found_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a not found response
        route = respx_mock.post('activity/events')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json=not_found_response)
        # Check that the right exception is raised by the client
        with pytest.raises(ERClientNotFound):
            await er_client.post_report(report)
        assert route.called  # Check that the api endpoint was called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_report_status_(er_client, report, bad_credentials_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a permissions error
        route = respx_mock.post('activity/events')
        response_data = bad_credentials_response
        route.return_value = httpx.Response(
            httpx.codes.UNAUTHORIZED,
            json=response_data
        )
        # Check that the right exception is raised by the client
        expected_message = f'ER Unauthorized ON POST {er_client.service_root}/activity/events. (status_code={httpx.codes.UNAUTHORIZED}) (response_body={json.dumps(response_data)})'
        with pytest.raises(ERClientBadCredentials, match=re.escape(expected_message)) as exc_info:
            await er_client.post_report(report)
        assert exc_info.value.status_code == httpx.codes.UNAUTHORIZED
        assert exc_info.value.response_body == json.dumps(response_data)
        assert route.called
