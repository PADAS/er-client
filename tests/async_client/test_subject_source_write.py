import httpx
import pytest
import respx

from erclient import (ERClientBadCredentials, ERClientBadRequest,
                      ERClientException, ERClientInternalError,
                      ERClientNotFound, ERClientPermissionDenied,
                      ERClientRateLimitExceeded, ERClientServiceUnreachable)


# ---- Fixtures ----

@pytest.fixture
def subject_payload():
    return {
        "name": "Test Elephant",
        "subject_type": "wildlife",
        "subject_subtype": "elephant",
        "is_active": True,
        "additional": {},
    }


@pytest.fixture
def subject_created_response():
    return {
        "data": {
            "content_type": "observations.subject",
            "id": "aabbccdd-1234-5678-9012-abcdefabcdef",
            "name": "Test Elephant",
            "subject_type": "wildlife",
            "subject_subtype": "elephant",
            "common_name": None,
            "additional": {},
            "created_at": "2026-02-10T12:00:00.000000-08:00",
            "updated_at": "2026-02-10T12:00:00.000000-08:00",
            "is_active": True,
            "user": None,
            "tracks_available": False,
            "image_url": "/static/elephant-black.svg",
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def source_payload():
    return {
        "manufacturer_id": "collar-9999",
        "source_type": "tracking-device",
        "model_name": "Test Collar",
        "additional": {},
    }


@pytest.fixture
def source_created_response():
    return {
        "data": {
            "id": "ee112233-4455-6677-8899-aabbccddeeff",
            "manufacturer_id": "collar-9999",
            "source_type": "tracking-device",
            "model_name": "Test Collar",
            "additional": {},
            "created_at": "2026-02-10T12:00:00.000000-08:00",
            "updated_at": "2026-02-10T12:00:00.000000-08:00",
        },
        "status": {"code": 201, "message": "Created"},
    }


# ---- post_subject tests ----

@pytest.mark.asyncio
async def test_post_subject_success(er_client, subject_payload, subject_created_response):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('subjects')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=subject_created_response
        )

        result = await er_client.post_subject(subject_payload)

        assert result == subject_created_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_subject_bad_request(er_client, subject_payload):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('subjects')
        route.return_value = httpx.Response(
            httpx.codes.BAD_REQUEST, json={}
        )

        with pytest.raises(ERClientBadRequest):
            await er_client.post_subject(subject_payload)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_subject_forbidden(er_client, subject_payload):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('subjects')
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json={}
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_subject(subject_payload)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_subject_unauthorized(er_client, subject_payload):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('subjects')
        route.return_value = httpx.Response(
            httpx.codes.UNAUTHORIZED, json={}
        )

        with pytest.raises(ERClientBadCredentials):
            await er_client.post_subject(subject_payload)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_subject_network_error(er_client, subject_payload):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('subjects')
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            await er_client.post_subject(subject_payload)

        assert route.called
        await er_client.close()


# ---- delete_subject tests ----

@pytest.mark.asyncio
async def test_delete_subject_success(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "aabbccdd-1234-5678-9012-abcdefabcdef"
        route = respx_mock.delete(f'subject/{subject_id}/')
        route.return_value = httpx.Response(
            httpx.codes.NO_CONTENT, json={}
        )

        # Should not raise
        await er_client.delete_subject(subject_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_subject_not_found(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "nonexistent-id"
        route = respx_mock.delete(f'subject/{subject_id}/')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json={}
        )

        with pytest.raises(ERClientNotFound):
            await er_client.delete_subject(subject_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_subject_forbidden(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "aabbccdd-1234-5678-9012-abcdefabcdef"
        route = respx_mock.delete(f'subject/{subject_id}/')
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json={}
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.delete_subject(subject_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_subject_network_error(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "aabbccdd-1234-5678-9012-abcdefabcdef"
        route = respx_mock.delete(f'subject/{subject_id}/')
        route.side_effect = httpx.ReadTimeout

        with pytest.raises(ERClientException):
            await er_client.delete_subject(subject_id)

        assert route.called
        await er_client.close()


# ---- post_source tests ----

@pytest.mark.asyncio
async def test_post_source_success(er_client, source_payload, source_created_response):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('sources')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=source_created_response
        )

        result = await er_client.post_source(source_payload)

        assert result == source_created_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_source_bad_request(er_client, source_payload):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('sources')
        route.return_value = httpx.Response(
            httpx.codes.BAD_REQUEST, json={}
        )

        with pytest.raises(ERClientBadRequest):
            await er_client.post_source(source_payload)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_source_forbidden(er_client, source_payload):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('sources')
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json={}
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_source(source_payload)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_source_network_error(er_client, source_payload):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('sources')
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            await er_client.post_source(source_payload)

        assert route.called
        await er_client.close()


# ---- delete_source tests ----

@pytest.mark.asyncio
async def test_delete_source_success(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        source_id = "ee112233-4455-6677-8899-aabbccddeeff"
        route = respx_mock.delete(f'source/{source_id}/')
        route.return_value = httpx.Response(
            httpx.codes.NO_CONTENT, json={}
        )

        await er_client.delete_source(source_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_source_not_found(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        source_id = "nonexistent-source-id"
        route = respx_mock.delete(f'source/{source_id}/')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json={}
        )

        with pytest.raises(ERClientNotFound):
            await er_client.delete_source(source_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_source_forbidden(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        source_id = "ee112233-4455-6677-8899-aabbccddeeff"
        route = respx_mock.delete(f'source/{source_id}/')
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json={}
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.delete_source(source_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_source_network_error(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        source_id = "ee112233-4455-6677-8899-aabbccddeeff"
        route = respx_mock.delete(f'source/{source_id}/')
        route.side_effect = httpx.ReadTimeout

        with pytest.raises(ERClientException):
            await er_client.delete_source(source_id)

        assert route.called
        await er_client.close()
