import httpx
import pytest
import respx

from erclient import (ERClientBadCredentials, ERClientBadRequest,
                      ERClientException, ERClientInternalError,
                      ERClientNotFound, ERClientPermissionDenied,
                      ERClientRateLimitExceeded, ERClientServiceUnreachable)


@pytest.fixture
def subject_updated_response():
    """Sample response for an updated subject"""
    return {
        "data": {
            "content_type": "observations.subject",
            "id": "d8ad9955-8301-43c4-9000-9a02f1cba675",
            "name": "MMVessel",
            "subject_type": "vehicle",
            "subject_subtype": "vessel",
            "common_name": None,
            "additional": {},
            "created_at": "2026-01-12T03:36:26.383023-08:00",
            "updated_at": "2026-01-12T04:30:12.289513-08:00",
            "is_active": False,
            "user": None,
            "tracks_available": True,
            "image_url": "/static/ranger-black.svg",
            "last_position_status": {
                "last_voice_call_start_at": None,
                "radio_state_at": None,
                "radio_state": "na"
            },
            "last_position_date": "2026-01-12T11:51:07+00:00",
            "last_position": {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [27.721512, -24.24426]
                },
                "properties": {
                    "title": "MMVessel",
                    "subject_type": "vehicle",
                    "subject_subtype": "vessel",
                    "id": "d8ad9955-8301-43c4-9000-9a02f1cba675",
                    "stroke": "#FFFF00",
                    "stroke-opacity": 1.0,
                    "stroke-width": 2,
                    "image": "https://gundi-dev.staging.pamdas.org/static/ranger-black.svg",
                    "last_voice_call_start_at": None,
                    "location_requested_at": None,
                    "radio_state_at": "1970-01-01T00:00:00+00:00",
                    "radio_state": "na",
                    "coordinateProperties": {
                        "time": "2026-01-12T11:51:07+00:00"
                    },
                    "DateTime": "2026-01-12T11:51:07+00:00"
                }
            },
            "device_status_properties": None,
            "url": "https://gundi-dev.staging.pamdas.org/api/v1.0/subject/d8ad9955-8301-43c4-9000-9a02f1cba675"
        },
        "status": {
            "code": 200,
            "message": "OK"
        }
    }


@pytest.mark.asyncio
async def test_patch_subject_success(er_client, subject_updated_response):
    """Test patch_subject with successful response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subject_updated_response
        )

        result = await er_client.patch_subject(
            subject_id=subject_id,
            data={"is_active": False}
        )

        assert result == subject_updated_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_multiple_fields(er_client, subject_updated_response):
    """Test patch_subject with multiple fields"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subject_updated_response
        )

        result = await er_client.patch_subject(
            subject_id=subject_id,
            data={
                "is_active": False,
                "name": "Updated Subject Name"
            }
        )

        assert result == subject_updated_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_not_found(er_client):
    """Test patch_subject with 404 Not Found response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "nonexistent-id"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json={}
        )

        with pytest.raises(ERClientNotFound):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_unauthorized(er_client):
    """Test patch_subject with 401 Unauthorized response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.UNAUTHORIZED, json={}
        )

        with pytest.raises(ERClientBadCredentials):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_forbidden(er_client):
    """Test patch_subject with 403 Forbidden response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json={}
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_bad_request(er_client):
    """Test patch_subject with 400 Bad Request response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.BAD_REQUEST, json={}
        )

        with pytest.raises(ERClientBadRequest):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"invalid_field": "value"}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_internal_server_error(er_client):
    """Test patch_subject with 500 Internal Server Error response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.INTERNAL_SERVER_ERROR, json={}
        )

        with pytest.raises(ERClientInternalError):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_service_unavailable(er_client):
    """Test patch_subject with 503 Service Unavailable response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.SERVICE_UNAVAILABLE, json={}
        )

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_bad_gateway(er_client):
    """Test patch_subject with 502 Bad Gateway response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.BAD_GATEWAY, json={}
        )

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_gateway_timeout(er_client):
    """Test patch_subject with 504 Gateway Timeout response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.GATEWAY_TIMEOUT, json={}
        )

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_rate_limit_exceeded(er_client):
    """Test patch_subject with 429 Too Many Requests response"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.return_value = httpx.Response(
            httpx.codes.TOO_MANY_REQUESTS, json={}
        )

        with pytest.raises(ERClientRateLimitExceeded):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_network_error(er_client):
    """Test patch_subject with network connection error"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_subject_read_timeout(er_client):
    """Test patch_subject with read timeout error"""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.patch(f'subject/{subject_id}')
        route.side_effect = httpx.ReadTimeout

        with pytest.raises(ERClientException):
            await er_client.patch_subject(
                subject_id=subject_id,
                data={"is_active": False}
            )

        assert route.called
        await er_client.close()
