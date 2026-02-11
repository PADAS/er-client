import httpx
import pytest
import respx

from erclient.er_errors import (
    ERClientNotFound,
    ERClientPermissionDenied,
)

ALERT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
NOTIF_ID = "f0e1d2c3-b4a5-6789-abcd-0123456789ab"

ALERT_DATA = {"id": ALERT_ID, "title": "Geofence breach", "is_active": True}
NOTIF_DATA = {"id": NOTIF_ID, "method_type": "email", "value": "me@example.com"}


# -- Alert rules: GET list ---------------------------------------------------

@pytest.mark.asyncio
async def test_get_alerts_success(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": [ALERT_DATA]},
        )
        result = await er_client.get_alerts()
        assert result == [ALERT_DATA]
        assert route.called
    await er_client.close()


@pytest.mark.asyncio
async def test_get_alerts_forbidden(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts")
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN,
            json={"status": {"code": 403, "detail": "Forbidden"}},
        )
        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_alerts()
    await er_client.close()


# -- Alert rules: GET single -------------------------------------------------

@pytest.mark.asyncio
async def test_get_alert_success(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/alert/{ALERT_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": ALERT_DATA},
        )
        result = await er_client.get_alert(ALERT_ID)
        assert result == ALERT_DATA
    await er_client.close()


@pytest.mark.asyncio
async def test_get_alert_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/alert/{ALERT_ID}")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "Not found"}},
        )
        with pytest.raises(ERClientNotFound):
            await er_client.get_alert(ALERT_ID)
    await er_client.close()


# -- Alert rules: POST -------------------------------------------------------

@pytest.mark.asyncio
async def test_post_alert_success(er_client):
    payload = {"title": "New alert", "conditions": []}
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/alerts")
        route.return_value = httpx.Response(
            httpx.codes.CREATED,
            json={"data": {**payload, "id": ALERT_ID}},
        )
        result = await er_client.post_alert(payload)
        assert result["id"] == ALERT_ID
    await er_client.close()


# -- Alert rules: PATCH ------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_alert_success(er_client):
    payload = {"title": "Updated alert"}
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/alert/{ALERT_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": {**ALERT_DATA, **payload}},
        )
        result = await er_client.patch_alert(ALERT_ID, payload)
        assert result["title"] == "Updated alert"
    await er_client.close()


# -- Alert rules: DELETE -----------------------------------------------------

@pytest.mark.asyncio
async def test_delete_alert_success(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/alert/{ALERT_ID}/")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)
        result = await er_client.delete_alert(ALERT_ID)
        assert result is True
    await er_client.close()


@pytest.mark.asyncio
async def test_delete_alert_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/alert/{ALERT_ID}/")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "Not found"}},
        )
        with pytest.raises(ERClientNotFound):
            await er_client.delete_alert(ALERT_ID)
    await er_client.close()


# -- Alert conditions --------------------------------------------------------

@pytest.mark.asyncio
async def test_get_alert_conditions_success(er_client):
    conditions = [{"type": "geofence"}, {"type": "proximity"}]
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts/conditions")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": conditions},
        )
        result = await er_client.get_alert_conditions()
        assert result == conditions
    await er_client.close()


# -- Notification methods: GET list ------------------------------------------

@pytest.mark.asyncio
async def test_get_notification_methods_success(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/notificationmethods")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": [NOTIF_DATA]},
        )
        result = await er_client.get_notification_methods()
        assert result == [NOTIF_DATA]
    await er_client.close()


# -- Notification methods: GET single ----------------------------------------

@pytest.mark.asyncio
async def test_get_notification_method_success(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/notificationmethod/{NOTIF_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": NOTIF_DATA},
        )
        result = await er_client.get_notification_method(NOTIF_ID)
        assert result == NOTIF_DATA
    await er_client.close()


@pytest.mark.asyncio
async def test_get_notification_method_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/notificationmethod/{NOTIF_ID}")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "Not found"}},
        )
        with pytest.raises(ERClientNotFound):
            await er_client.get_notification_method(NOTIF_ID)
    await er_client.close()


# -- Notification methods: POST ----------------------------------------------

@pytest.mark.asyncio
async def test_post_notification_method_success(er_client):
    payload = {"method_type": "email", "value": "test@example.com"}
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/notificationmethods")
        route.return_value = httpx.Response(
            httpx.codes.CREATED,
            json={"data": {**payload, "id": NOTIF_ID}},
        )
        result = await er_client.post_notification_method(payload)
        assert result["id"] == NOTIF_ID
    await er_client.close()


# -- Notification methods: PATCH ---------------------------------------------

@pytest.mark.asyncio
async def test_patch_notification_method_success(er_client):
    payload = {"value": "updated@example.com"}
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/notificationmethod/{NOTIF_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": {**NOTIF_DATA, **payload}},
        )
        result = await er_client.patch_notification_method(NOTIF_ID, payload)
        assert result["value"] == "updated@example.com"
    await er_client.close()


# -- Notification methods: DELETE --------------------------------------------

@pytest.mark.asyncio
async def test_delete_notification_method_success(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/notificationmethod/{NOTIF_ID}/")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)
        result = await er_client.delete_notification_method(NOTIF_ID)
        assert result is True
    await er_client.close()


@pytest.mark.asyncio
async def test_delete_notification_method_not_found(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/notificationmethod/{NOTIF_ID}/")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "Not found"}},
        )
        with pytest.raises(ERClientNotFound):
            await er_client.delete_notification_method(NOTIF_ID)
    await er_client.close()
