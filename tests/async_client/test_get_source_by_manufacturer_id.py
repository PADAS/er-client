import httpx
import pytest
import respx

from erclient import (ERClientBadCredentials, ERClientBadRequest,
                      ERClientException, ERClientInternalError,
                      ERClientNotFound, ERClientPermissionDenied,
                      ERClientRateLimitExceeded, ERClientServiceUnreachable)


@pytest.fixture
def source_response():
    """Sample response for a source"""
    return {
        "data": {
            "id": "119feb94-a6cc-4485-8614-06fb0abc2a9c",
            "source_type": None,
            "manufacturer_id": "42",
            "model_name": "generic:mariano-test",
            "additional": {},
            "provider": "mariano-test",
            "content_type": "observations.source",
            "created_at": "2026-01-12T03:36:26.365680-08:00",
            "updated_at": "2026-01-12T03:36:26.365715-08:00",
            "url": "https://gundi-dev.staging.pamdas.org/api/v1.0/source/119feb94-a6cc-4485-8614-06fb0abc2a9c"
        },
        "status": {
            "code": 200,
            "message": "OK"
        }
    }


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_success(er_client, source_response):
    """Test get_source_by_manufacturer_id with successful response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.OK, json=source_response
        )

        result = await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert result == source_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_not_found(er_client):
    """Test get_source_by_manufacturer_id with 404 Not Found response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "nonexistent-id"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json={}
        )

        with pytest.raises(ERClientNotFound):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_unauthorized(er_client):
    """Test get_source_by_manufacturer_id with 401 Unauthorized response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.UNAUTHORIZED, json={}
        )

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_forbidden(er_client):
    """Test get_source_by_manufacturer_id with 403 Forbidden response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json={}
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_bad_request(er_client):
    """Test get_source_by_manufacturer_id with 400 Bad Request response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.BAD_REQUEST, json={}
        )

        with pytest.raises(ERClientBadRequest):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_internal_server_error(er_client):
    """Test get_source_by_manufacturer_id with 500 Internal Server Error response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.INTERNAL_SERVER_ERROR, json={}
        )

        with pytest.raises(ERClientInternalError):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_service_unavailable(er_client):
    """Test get_source_by_manufacturer_id with 503 Service Unavailable response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.SERVICE_UNAVAILABLE, json={}
        )

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_bad_gateway(er_client):
    """Test get_source_by_manufacturer_id with 502 Bad Gateway response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.BAD_GATEWAY, json={}
        )

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_gateway_timeout(er_client):
    """Test get_source_by_manufacturer_id with 504 Gateway Timeout response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.GATEWAY_TIMEOUT, json={}
        )

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_rate_limit_exceeded(er_client):
    """Test get_source_by_manufacturer_id with 429 Too Many Requests response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.return_value = httpx.Response(
            httpx.codes.TOO_MANY_REQUESTS, json={}
        )

        with pytest.raises(ERClientRateLimitExceeded):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_network_error(er_client):
    """Test get_source_by_manufacturer_id with network connection error"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_manufacturer_id_read_timeout(er_client):
    """Test get_source_by_manufacturer_id with read timeout error"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        manufacturer_id = "42"
        route = respx_mock.get(f'source/{manufacturer_id}/')
        route.side_effect = httpx.ReadTimeout

        with pytest.raises(ERClientException):
            await er_client.get_source_by_manufacturer_id(manufacturer_id)

        assert route.called
        await er_client.close()
