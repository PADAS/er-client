import httpx
import pytest
import respx

from erclient import (ERClientBadCredentials, ERClientBadRequest,
                      ERClientException, ERClientInternalError,
                      ERClientNotFound, ERClientPermissionDenied,
                      ERClientRateLimitExceeded, ERClientServiceUnreachable)


ALERT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


@pytest.fixture
def alert_list_response():
    return {
        "data": [
            {
                "id": ALERT_ID,
                "title": "Poaching Alert",
                "is_active": True,
                "ordernum": 0,
                "conditions": {"all": [{"name": "state_is_new", "value": True}]},
                "schedule": {"periods": {}},
                "reportTypes": ["poaching_rep"],
                "notification_method_ids": [],
            }
        ],
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def alert_detail_response():
    return {
        "data": {
            "id": ALERT_ID,
            "title": "Poaching Alert",
            "is_active": True,
            "ordernum": 0,
            "conditions": {"all": [{"name": "state_is_new", "value": True}]},
            "schedule": {"periods": {}},
            "reportTypes": ["poaching_rep"],
            "notification_method_ids": [],
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def alert_created_response():
    return {
        "data": {
            "id": ALERT_ID,
            "title": "New Alert",
            "is_active": True,
            "ordernum": 0,
            "conditions": {},
            "schedule": {"periods": {}},
            "reportTypes": ["fire_rep"],
            "notification_method_ids": [],
        },
        "status": {"code": 201, "message": "Created"},
    }


# ---- get_alerts tests ----

@pytest.mark.asyncio
async def test_get_alerts_success(er_client, alert_list_response):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=alert_list_response
        )

        result = await er_client.get_alerts()
        assert result == alert_list_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_alerts_empty(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts")
        route.return_value = httpx.Response(
            httpx.codes.OK, json={"data": [], "status": {"code": 200, "message": "OK"}}
        )

        result = await er_client.get_alerts()
        assert result == []
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_alerts_unauthorized(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts")
        route.return_value = httpx.Response(httpx.codes.UNAUTHORIZED, json={})

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_alerts()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_alerts_forbidden(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_alerts()

        assert route.called
        await er_client.close()


# ---- get_alert tests ----

@pytest.mark.asyncio
async def test_get_alert_success(er_client, alert_detail_response):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/alert/{ALERT_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=alert_detail_response
        )

        result = await er_client.get_alert(ALERT_ID)
        assert result == alert_detail_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_alert_not_found(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/alert/{ALERT_ID}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.get_alert(ALERT_ID)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_alert_forbidden(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"activity/alert/{ALERT_ID}")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_alert(ALERT_ID)

        assert route.called
        await er_client.close()


# ---- post_alert tests ----

@pytest.mark.asyncio
async def test_post_alert_success(er_client, alert_created_response):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/alerts")
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=alert_created_response
        )

        result = await er_client.post_alert({
            "title": "New Alert",
            "reportTypes": ["fire_rep"],
        })
        assert result == alert_created_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_alert_bad_request(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/alerts")
        route.return_value = httpx.Response(httpx.codes.BAD_REQUEST, json={})

        with pytest.raises(ERClientBadRequest):
            await er_client.post_alert({})

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_alert_forbidden(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/alerts")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_alert({"title": "test"})

        assert route.called
        await er_client.close()


# ---- patch_alert tests ----

@pytest.mark.asyncio
async def test_patch_alert_success(er_client, alert_detail_response):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/alert/{ALERT_ID}")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=alert_detail_response
        )

        result = await er_client.patch_alert(ALERT_ID, {"is_active": False})
        assert result == alert_detail_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_alert_not_found(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/alert/{ALERT_ID}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.patch_alert(ALERT_ID, {"is_active": False})

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_alert_bad_request(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f"activity/alert/{ALERT_ID}")
        route.return_value = httpx.Response(httpx.codes.BAD_REQUEST, json={})

        with pytest.raises(ERClientBadRequest):
            await er_client.patch_alert(ALERT_ID, {"invalid": "data"})

        assert route.called
        await er_client.close()


# ---- delete_alert tests ----

@pytest.mark.asyncio
async def test_delete_alert_success(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/alert/{ALERT_ID}/")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        result = await er_client.delete_alert(ALERT_ID)
        assert result is True
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_alert_not_found(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/alert/{ALERT_ID}/")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.delete_alert(ALERT_ID)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_alert_forbidden(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/alert/{ALERT_ID}/")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.delete_alert(ALERT_ID)

        assert route.called
        await er_client.close()


# ---- get_alert_conditions tests ----

@pytest.mark.asyncio
async def test_get_alert_conditions_success(er_client):
    conditions_response = {
        "data": [
            {"value": "poaching_rep", "display": "Poaching Report", "factors": []},
            {"value": "fire_rep", "display": "Fire Report", "factors": []},
        ],
        "status": {"code": 200, "message": "OK"},
    }
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts/conditions")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=conditions_response
        )

        result = await er_client.get_alert_conditions()
        assert result == conditions_response["data"]
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_alert_conditions_empty(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts/conditions")
        route.return_value = httpx.Response(
            httpx.codes.OK, json={"data": [], "status": {"code": 200, "message": "OK"}}
        )

        result = await er_client.get_alert_conditions()
        assert result == []
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_alert_conditions_forbidden(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts/conditions")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_alert_conditions()

        assert route.called
        await er_client.close()


# ---- Error edge cases (network, server errors) ----

@pytest.mark.asyncio
async def test_get_alerts_internal_server_error(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/alerts")
        route.return_value = httpx.Response(httpx.codes.INTERNAL_SERVER_ERROR, json={})

        with pytest.raises(ERClientInternalError):
            await er_client.get_alerts()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_alert_network_error(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post("activity/alerts")
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            await er_client.post_alert({"title": "test"})

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_alert_service_unavailable(er_client):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f"activity/alert/{ALERT_ID}/")
        route.return_value = httpx.Response(httpx.codes.SERVICE_UNAVAILABLE, json={})

        with pytest.raises(ERClientServiceUnreachable):
            await er_client.delete_alert(ALERT_ID)

        assert route.called
        await er_client.close()
