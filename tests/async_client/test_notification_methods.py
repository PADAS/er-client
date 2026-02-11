import httpx
import pytest
import respx

from erclient import (ERClientBadCredentials, ERClientBadRequest,
                      ERClientException, ERClientInternalError,
                      ERClientNotFound, ERClientPermissionDenied,
                      ERClientServiceUnreachable)


NM_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"


@pytest.fixture
def notification_method_list_response():
    return {
        "data": {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": NM_ID,
                    "title": "Email Notification",
                    "contact": {"method": "email", "value": "test@example.com"},
                    "is_active": True,
                    "owner": {"username": "testuser"},
                },
                {
                    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "title": "SMS Notification",
                    "contact": {"method": "sms", "value": "+15551234567"},
                    "is_active": True,
                    "owner": {"username": "testuser"},
                },
            ],
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def notification_method_detail_response():
    return {
        "data": {
            "id": NM_ID,
            "title": "Email Notification",
            "contact": {"method": "email", "value": "test@example.com"},
            "is_active": True,
            "owner": {"username": "testuser"},
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def notification_method_created_response():
    return {
        "data": {
            "id": NM_ID,
            "title": "New Email Notification",
            "contact": {"method": "email", "value": "new@example.com"},
            "is_active": True,
            "owner": {"username": "testuser"},
        },
        "status": {"code": 201, "message": "Created"},
    }


# ---- get_notification_methods tests ----

@pytest.mark.asyncio
async def test_get_notification_methods_success(er_client, notification_method_list_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/notificationmethods")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=notification_method_list_response
        )

        result = await er_client.get_notification_methods()
        assert result == notification_method_list_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_notification_methods_empty(er_client):
    empty_response = {
        "data": {
            "count": 0, "next": None, "previous": None, "results": []
        },
        "status": {"code": 200, "message": "OK"},
    }
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/notificationmethods")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=empty_response
        )

        result = await er_client.get_notification_methods()
        assert result == empty_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_notification_methods_unauthorized(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/notificationmethods")
        route.return_value = httpx.Response(httpx.codes.UNAUTHORIZED, json={})

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_notification_methods()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_notification_methods_forbidden(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/notificationmethods")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_notification_methods()

        assert route.called
        await er_client.close()


# ---- get_notification_method tests ----

@pytest.mark.asyncio
async def test_get_notification_method_success(er_client, notification_method_detail_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/notificationmethod/{NM_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=notification_method_detail_response
        )

        result = await er_client.get_notification_method(NM_ID)
        assert result == notification_method_detail_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_notification_method_not_found(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/notificationmethod/{NM_ID}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.get_notification_method(NM_ID)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_notification_method_forbidden(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/notificationmethod/{NM_ID}")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_notification_method(NM_ID)

        assert route.called
        await er_client.close()


# ---- post_notification_method tests ----

@pytest.mark.asyncio
async def test_post_notification_method_success(er_client, notification_method_created_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/notificationmethods")
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=notification_method_created_response
        )

        result = await er_client.post_notification_method({
            "title": "New Email Notification",
            "contact": {"method": "email", "value": "new@example.com"},
        })
        assert result == notification_method_created_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_notification_method_bad_request(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/notificationmethods")
        route.return_value = httpx.Response(httpx.codes.BAD_REQUEST, json={})

        with pytest.raises(ERClientBadRequest):
            await er_client.post_notification_method({})

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_notification_method_forbidden(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/notificationmethods")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_notification_method({"title": "test"})

        assert route.called
        await er_client.close()


# ---- patch_notification_method tests ----

@pytest.mark.asyncio
async def test_patch_notification_method_success(er_client, notification_method_detail_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/notificationmethod/{NM_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=notification_method_detail_response
        )

        result = await er_client.patch_notification_method(NM_ID, {"is_active": False})
        assert result == notification_method_detail_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_notification_method_not_found(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/notificationmethod/{NM_ID}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.patch_notification_method(NM_ID, {"is_active": False})

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_notification_method_bad_request(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/notificationmethod/{NM_ID}")
        route.return_value = httpx.Response(httpx.codes.BAD_REQUEST, json={})

        with pytest.raises(ERClientBadRequest):
            await er_client.patch_notification_method(NM_ID, {"invalid": "data"})

        assert route.called
        await er_client.close()


# ---- delete_notification_method tests ----

@pytest.mark.asyncio
async def test_delete_notification_method_success(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/notificationmethod/{NM_ID}/")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        result = await er_client.delete_notification_method(NM_ID)
        assert result is True
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_notification_method_not_found(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/notificationmethod/{NM_ID}/")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.delete_notification_method(NM_ID)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_notification_method_forbidden(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/notificationmethod/{NM_ID}/")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.delete_notification_method(NM_ID)

        assert route.called
        await er_client.close()


# ---- Error edge cases ----

@pytest.mark.asyncio
async def test_get_notification_methods_internal_server_error(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/notificationmethods")
        route.return_value = httpx.Response(httpx.codes.INTERNAL_SERVER_ERROR, json={})

        with pytest.raises(ERClientInternalError):
            await er_client.get_notification_methods()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_notification_method_network_error(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/notificationmethods")
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            await er_client.post_notification_method({"title": "test"})

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_notification_method_service_unavailable(er_client):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/notificationmethod/{NM_ID}/")
        route.return_value = httpx.Response(httpx.codes.SERVICE_UNAVAILABLE, json={})

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.delete_notification_method(NM_ID)

        assert route.called
        await er_client.close()
