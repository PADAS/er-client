import httpx
import pytest
import respx

from erclient import (ERClientBadCredentials, ERClientBadRequest,
                      ERClientException, ERClientInternalError,
                      ERClientNotFound, ERClientPermissionDenied,
                      ERClientRateLimitExceeded, ERClientServiceUnreachable)


@pytest.fixture
def source_assignments_response():
    """Sample response for source assignments"""
    return {
        "data": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "subject": "123e4567-e89b-12d3-a456-426614174001",
                "source": "123e4567-e89b-12d3-a456-426614174002",
                "assigned_range": {
                    "lower": "2023-06-01T01:41:00+02:00",
                    "upper": "2024-01-11T19:41:00+02:00",
                    "bounds": "[)"
                }
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "subject": "123e4567-e89b-12d3-a456-426614174001",
                "source": "123e4567-e89b-12d3-a456-426614174003",
                "assigned_range": {
                    "upper": "2024-06-01T01:41:00+02:00",
                    "lower": "2024-01-11T19:41:00+02:00",
                    "bounds": "[)"
                }
            }
        ],
        "status": {"code": 200, "message": "OK"}
    }


@pytest.fixture
def empty_source_assignments_response():
    """Empty response for source assignments"""
    return {
        "data": [],
        "status": {"code": 200, "message": "OK"}
    }


@pytest.fixture
def source_assignments_filtered_response():
    """Filtered response for source assignments with subject_ids"""
    return {
        "data": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "subject": "123e4567-e89b-12d3-a456-426614174001",
                "source": "123e4567-e89b-12d3-a456-426614174002",
                "assigned_range": {
                    "lower": "2023-06-01T01:41:00+02:00",
                    "upper": "2024-01-11T19:41:00+02:00",
                    "bounds": "[)"
                }
            }
        ],
        "status": {"code": 200, "message": "OK"}
    }


@pytest.mark.asyncio
async def test_get_source_assignments_empty_payload(er_client, empty_source_assignments_response):
    """Test get_source_assignments with no parameters (empty payload)"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.OK, json=empty_source_assignments_response
        )

        result = await er_client.get_source_assignments()

        assert result == empty_source_assignments_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_with_subject_ids(er_client, source_assignments_filtered_response):
    """Test get_source_assignments with subject_ids filter"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.OK, json=source_assignments_filtered_response
        )

        subject_ids = ["123e4567-e89b-12d3-a456-426614174001"]
        result = await er_client.get_source_assignments(subject_ids=subject_ids)

        assert result == source_assignments_filtered_response["data"]
        assert route.called
        # Verify the query parameter was sent correctly
        assert "subjects=123e4567-e89b-12d3-a456-426614174001" in str(
            route.calls[0].request.url)
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_with_source_ids(er_client, source_assignments_filtered_response):
    """Test get_source_assignments with source_ids filter"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.OK, json=source_assignments_filtered_response
        )

        source_ids = ["123e4567-e89b-12d3-a456-426614174002"]
        result = await er_client.get_source_assignments(source_ids=source_ids)

        assert result == source_assignments_filtered_response["data"]
        assert route.called
        # Verify the query parameter was sent correctly
        assert "sources=123e4567-e89b-12d3-a456-426614174002" in str(
            route.calls[0].request.url)
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_with_both_filters(er_client, source_assignments_filtered_response):
    """Test get_source_assignments with both subject_ids and source_ids filters"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.OK, json=source_assignments_filtered_response
        )

        subject_ids = ["123e4567-e89b-12d3-a456-426614174001"]
        source_ids = ["123e4567-e89b-12d3-a456-426614174002"]
        result = await er_client.get_source_assignments(subject_ids=subject_ids, source_ids=source_ids)

        assert result == source_assignments_filtered_response["data"]
        assert route.called
        # Verify both query parameters were sent correctly
        request_url = str(route.calls[0].request.url)
        assert "subjects=123e4567-e89b-12d3-a456-426614174001" in request_url
        assert "sources=123e4567-e89b-12d3-a456-426614174002" in request_url
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_unauthorized(er_client):
    """Test get_source_assignments with 401 Unauthorized response"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.UNAUTHORIZED, json={}
        )

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_forbidden(er_client):
    """Test get_source_assignments with 403 Forbidden response"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json={}
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_not_found(er_client):
    """Test get_source_assignments with 404 Not Found response"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json={}
        )

        with pytest.raises(ERClientNotFound):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_bad_request(er_client):
    """Test get_source_assignments with 400 Bad Request response"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.BAD_REQUEST, json={}
        )

        with pytest.raises(ERClientBadRequest):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_internal_server_error(er_client):
    """Test get_source_assignments with 500 Internal Server Error response"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.INTERNAL_SERVER_ERROR, json={}
        )

        with pytest.raises(ERClientInternalError):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_service_unavailable(er_client):
    """Test get_source_assignments with 503 Service Unavailable response"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.SERVICE_UNAVAILABLE, json={}
        )

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_bad_gateway(er_client):
    """Test get_source_assignments with 502 Bad Gateway response"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.BAD_GATEWAY, json={}
        )

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_gateway_timeout(er_client):
    """Test get_source_assignments with 504 Gateway Timeout response"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.GATEWAY_TIMEOUT, json={}
        )

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_rate_limit_exceeded(er_client):
    """Test get_source_assignments with 429 Too Many Requests response"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.return_value = httpx.Response(
            httpx.codes.TOO_MANY_REQUESTS, json={}
        )

        with pytest.raises(ERClientRateLimitExceeded):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_network_error(er_client):
    """Test get_source_assignments with network connection error"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_assignments_read_timeout(er_client):
    """Test get_source_assignments with read timeout error"""
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('subjectsources')
        route.side_effect = httpx.ReadTimeout

        with pytest.raises(ERClientException):
            await er_client.get_source_assignments()

        assert route.called
        await er_client.close()
