import httpx
import pytest
import respx

from erclient import (ERClientBadCredentials, ERClientException,
                      ERClientNotFound, ERClientPermissionDenied)


@pytest.fixture
def sources_page_one_response():
    """Paginated sources response - page 1"""
    return {
        "count": 3,
        "next": "https://fake-site.erdomain.org/api/v1.0/sources?page=2&page_size=2&use_cursor=true",
        "previous": None,
        "results": [
            {
                "id": "119feb94-a6cc-4485-8614-06fb0abc2a9c",
                "source_type": "tracking-device",
                "manufacturer_id": "collar-001",
                "model_name": "generic:test-provider",
                "additional": {},
                "provider": "test-provider",
                "content_type": "observations.source",
                "created_at": "2025-01-10T03:36:26.365680-08:00",
                "updated_at": "2025-01-10T03:36:26.365715-08:00",
                "url": "https://fake-site.erdomain.org/api/v1.0/source/119feb94-a6cc-4485-8614-06fb0abc2a9c",
            },
            {
                "id": "229feb94-b7dd-5596-9725-17gc1bcd3b0d",
                "source_type": "tracking-device",
                "manufacturer_id": "collar-002",
                "model_name": "generic:test-provider",
                "additional": {},
                "provider": "test-provider",
                "content_type": "observations.source",
                "created_at": "2025-01-11T03:36:26.365680-08:00",
                "updated_at": "2025-01-11T03:36:26.365715-08:00",
                "url": "https://fake-site.erdomain.org/api/v1.0/source/229feb94-b7dd-5596-9725-17gc1bcd3b0d",
            },
        ],
    }


@pytest.fixture
def sources_page_two_response():
    """Paginated sources response - page 2 (last)"""
    return {
        "count": 3,
        "next": None,
        "previous": "https://fake-site.erdomain.org/api/v1.0/sources?page_size=2&use_cursor=true",
        "results": [
            {
                "id": "339feb94-c8ee-6607-0836-28hd2cde4c1e",
                "source_type": "tracking-device",
                "manufacturer_id": "collar-003",
                "model_name": "generic:test-provider",
                "additional": {},
                "provider": "test-provider",
                "content_type": "observations.source",
                "created_at": "2025-01-12T03:36:26.365680-08:00",
                "updated_at": "2025-01-12T03:36:26.365715-08:00",
                "url": "https://fake-site.erdomain.org/api/v1.0/source/339feb94-c8ee-6607-0836-28hd2cde4c1e",
            },
        ],
    }


@pytest.fixture
def sources_single_page_response():
    """Non-paginated sources response"""
    return {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": "119feb94-a6cc-4485-8614-06fb0abc2a9c",
                "source_type": "tracking-device",
                "manufacturer_id": "collar-001",
                "model_name": "generic:test-provider",
                "additional": {},
                "provider": "test-provider",
                "content_type": "observations.source",
                "created_at": "2025-01-10T03:36:26.365680-08:00",
                "updated_at": "2025-01-10T03:36:26.365715-08:00",
                "url": "https://fake-site.erdomain.org/api/v1.0/source/119feb94-a6cc-4485-8614-06fb0abc2a9c",
            },
            {
                "id": "229feb94-b7dd-5596-9725-17gc1bcd3b0d",
                "source_type": "tracking-device",
                "manufacturer_id": "collar-002",
                "model_name": "generic:test-provider",
                "additional": {},
                "provider": "test-provider",
                "content_type": "observations.source",
                "created_at": "2025-01-11T03:36:26.365680-08:00",
                "updated_at": "2025-01-11T03:36:26.365715-08:00",
                "url": "https://fake-site.erdomain.org/api/v1.0/source/229feb94-b7dd-5596-9725-17gc1bcd3b0d",
            },
        ],
    }


@pytest.fixture
def empty_sources_response():
    return {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


@pytest.fixture
def source_detail_response():
    """Sample response for a single source"""
    return {
        "data": {
            "id": "119feb94-a6cc-4485-8614-06fb0abc2a9c",
            "source_type": "tracking-device",
            "manufacturer_id": "collar-001",
            "model_name": "generic:test-provider",
            "additional": {},
            "provider": "test-provider",
            "content_type": "observations.source",
            "created_at": "2025-01-10T03:36:26.365680-08:00",
            "updated_at": "2025-01-10T03:36:26.365715-08:00",
            "url": "https://fake-site.erdomain.org/api/v1.0/source/119feb94-a6cc-4485-8614-06fb0abc2a9c",
        },
        "status": {"code": 200, "message": "OK"},
    }


# ---- get_sources() tests ----


@pytest.mark.asyncio
async def test_get_sources_single_page(er_client, sources_single_page_response):
    """Test get_sources returns all sources from a single page"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("sources")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=sources_single_page_response
        )

        sources = []
        async for source in er_client.get_sources():
            sources.append(source)

        assert len(sources) == 2
        assert sources[0]["manufacturer_id"] == "collar-001"
        assert sources[1]["manufacturer_id"] == "collar-002"
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_sources_paginated(
    er_client, sources_page_one_response, sources_page_two_response
):
    """Test get_sources handles pagination across multiple pages"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("sources")
        route.side_effect = [
            httpx.Response(httpx.codes.OK, json=sources_page_one_response),
            httpx.Response(httpx.codes.OK, json=sources_page_two_response),
        ]

        sources = []
        async for source in er_client.get_sources(page_size=2):
            sources.append(source)

        assert len(sources) == 3
        assert sources[0]["manufacturer_id"] == "collar-001"
        assert sources[2]["manufacturer_id"] == "collar-003"
        assert route.call_count == 2
        await er_client.close()


@pytest.mark.asyncio
async def test_get_sources_empty(er_client, empty_sources_response):
    """Test get_sources with no sources"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("sources")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=empty_sources_response
        )

        sources = []
        async for source in er_client.get_sources():
            sources.append(source)

        assert len(sources) == 0
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_sources_unauthorized(er_client):
    """Test get_sources raises ERClientBadCredentials on 401"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("sources")
        route.return_value = httpx.Response(httpx.codes.UNAUTHORIZED, json={})

        with pytest.raises(ERClientBadCredentials):
            async for _ in er_client.get_sources():
                pass

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_sources_network_error(er_client):
    """Test get_sources raises ERClientException on network error"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("sources")
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            async for _ in er_client.get_sources():
                pass

        assert route.called
        await er_client.close()


# ---- get_source_by_id() tests ----


@pytest.mark.asyncio
async def test_get_source_by_id_success(er_client, source_detail_response):
    """Test get_source_by_id returns a single source"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        source_id = "119feb94-a6cc-4485-8614-06fb0abc2a9c"
        route = respx_mock.get(f"source/{source_id}")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=source_detail_response
        )

        result = await er_client.get_source_by_id(source_id)

        assert result == source_detail_response["data"]
        assert result["id"] == source_id
        assert result["manufacturer_id"] == "collar-001"
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_id_not_found(er_client):
    """Test get_source_by_id raises ERClientNotFound on 404"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        source_id = "nonexistent-id"
        route = respx_mock.get(f"source/{source_id}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.get_source_by_id(source_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_id_unauthorized(er_client):
    """Test get_source_by_id raises ERClientBadCredentials on 401"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        source_id = "119feb94-a6cc-4485-8614-06fb0abc2a9c"
        route = respx_mock.get(f"source/{source_id}")
        route.return_value = httpx.Response(httpx.codes.UNAUTHORIZED, json={})

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_source_by_id(source_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_id_forbidden(er_client):
    """Test get_source_by_id raises ERClientPermissionDenied on 403"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        source_id = "119feb94-a6cc-4485-8614-06fb0abc2a9c"
        route = respx_mock.get(f"source/{source_id}")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_source_by_id(source_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_source_by_id_network_error(er_client):
    """Test get_source_by_id raises ERClientException on network error"""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        source_id = "119feb94-a6cc-4485-8614-06fb0abc2a9c"
        route = respx_mock.get(f"source/{source_id}")
        route.side_effect = httpx.ReadTimeout

        with pytest.raises(ERClientException):
            await er_client.get_source_by_id(source_id)

        assert route.called
        await er_client.close()
