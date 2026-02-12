import httpx
import pytest
import respx

from erclient import ERClientNotFound, ERClientPermissionDenied


EVENTPROVIDER_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
EVENTSOURCE_ID = "f0e1d2c3-b4a5-6789-0fed-cba987654321"


@pytest.fixture
def eventprovider_payload():
    return {
        "display": "My Test Provider",
        "owner": {"id": "user-id-123"},
    }


@pytest.fixture
def eventprovider_response():
    return {
        "data": {
            "id": EVENTPROVIDER_ID,
            "display": "My Test Provider",
            "is_active": True,
            "owner": {"id": "user-id-123"},
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def eventprovider_detail_response():
    return {
        "data": {
            "id": EVENTPROVIDER_ID,
            "display": "My Test Provider",
            "is_active": True,
            "owner": {"id": "user-id-123"},
        },
    }


@pytest.fixture
def eventproviders_list_response():
    return {
        "data": [
            {
                "id": EVENTPROVIDER_ID,
                "display": "My Test Provider",
                "is_active": True,
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "display": "Another Provider",
                "is_active": False,
            },
        ],
    }


@pytest.fixture
def eventprovider_patched_response():
    return {
        "data": {
            "id": EVENTPROVIDER_ID,
            "display": "Updated Provider Name",
            "is_active": True,
        },
    }


@pytest.fixture
def eventsource_payload():
    return {
        "display": "Test Event Source",
    }


@pytest.fixture
def eventsource_response():
    return {
        "data": {
            "id": EVENTSOURCE_ID,
            "display": "Test Event Source",
            "eventprovider": EVENTPROVIDER_ID,
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def eventsources_list_response():
    return {
        "data": [
            {
                "id": EVENTSOURCE_ID,
                "display": "Test Event Source",
                "eventprovider": EVENTPROVIDER_ID,
            },
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "display": "Second Source",
                "eventprovider": EVENTPROVIDER_ID,
            },
        ],
    }


@pytest.fixture
def eventsource_detail_response():
    return {
        "data": {
            "id": EVENTSOURCE_ID,
            "display": "Test Event Source",
            "eventprovider": EVENTPROVIDER_ID,
        },
    }


@pytest.fixture
def eventsource_patched_response():
    return {
        "data": {
            "id": EVENTSOURCE_ID,
            "display": "Renamed Source",
            "eventprovider": EVENTPROVIDER_ID,
        },
    }


# -- Event Provider Tests --


@pytest.mark.asyncio
async def test_post_eventprovider_success(er_client, eventprovider_payload, eventprovider_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.post("activity/eventproviders/")
        route.return_value = httpx.Response(httpx.codes.CREATED, json=eventprovider_response)
        result = await er_client.post_eventprovider(eventprovider_payload)
        assert route.called
        assert result == eventprovider_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_post_eventprovider_forbidden(er_client, eventprovider_payload, forbidden_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.post("activity/eventproviders/")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json=forbidden_response)
        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_eventprovider(eventprovider_payload)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_eventproviders_success(er_client, eventproviders_list_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.get("activity/eventproviders")
        route.return_value = httpx.Response(httpx.codes.OK, json=eventproviders_list_response)
        result = await er_client.get_eventproviders()
        assert route.called
        assert result == eventproviders_list_response["data"]
        assert len(result) == 2
        await er_client.close()


@pytest.mark.asyncio
async def test_get_eventprovider_success(er_client, eventprovider_detail_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"activity/eventprovider/{EVENTPROVIDER_ID}")
        route.return_value = httpx.Response(httpx.codes.OK, json=eventprovider_detail_response)
        result = await er_client.get_eventprovider(EVENTPROVIDER_ID)
        assert route.called
        assert result == eventprovider_detail_response["data"]
        assert result["id"] == EVENTPROVIDER_ID
        await er_client.close()


@pytest.mark.asyncio
async def test_get_eventprovider_not_found(er_client, not_found_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"activity/eventprovider/{EVENTPROVIDER_ID}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json=not_found_response)
        with pytest.raises(ERClientNotFound):
            await er_client.get_eventprovider(EVENTPROVIDER_ID)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_eventprovider_success(er_client, eventprovider_patched_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.patch(f"activity/eventprovider/{EVENTPROVIDER_ID}")
        route.return_value = httpx.Response(httpx.codes.OK, json=eventprovider_patched_response)
        result = await er_client.patch_eventprovider(
            EVENTPROVIDER_ID, {"display": "Updated Provider Name"}
        )
        assert route.called
        assert result == eventprovider_patched_response["data"]
        assert result["display"] == "Updated Provider Name"
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_eventprovider_not_found(er_client, not_found_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.patch(f"activity/eventprovider/{EVENTPROVIDER_ID}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json=not_found_response)
        with pytest.raises(ERClientNotFound):
            await er_client.patch_eventprovider(EVENTPROVIDER_ID, {"display": "X"})
        assert route.called
        await er_client.close()


# -- Event Source Tests --


@pytest.mark.asyncio
async def test_post_eventsource_success(er_client, eventsource_payload, eventsource_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.post(f"activity/eventprovider/{EVENTPROVIDER_ID}/eventsources")
        route.return_value = httpx.Response(httpx.codes.CREATED, json=eventsource_response)
        result = await er_client.post_eventsource(EVENTPROVIDER_ID, eventsource_payload)
        assert route.called
        assert result == eventsource_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_post_eventsource_provider_not_found(er_client, eventsource_payload, not_found_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.post(f"activity/eventprovider/{EVENTPROVIDER_ID}/eventsources")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json=not_found_response)
        with pytest.raises(ERClientNotFound):
            await er_client.post_eventsource(EVENTPROVIDER_ID, eventsource_payload)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_eventsources_success(er_client, eventsources_list_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"activity/eventprovider/{EVENTPROVIDER_ID}/eventsources")
        route.return_value = httpx.Response(httpx.codes.OK, json=eventsources_list_response)
        result = await er_client.get_eventsources(EVENTPROVIDER_ID)
        assert route.called
        assert result == eventsources_list_response["data"]
        assert len(result) == 2
        await er_client.close()


@pytest.mark.asyncio
async def test_get_eventsource_success(er_client, eventsource_detail_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"activity/eventsource/{EVENTSOURCE_ID}")
        route.return_value = httpx.Response(httpx.codes.OK, json=eventsource_detail_response)
        result = await er_client.get_eventsource(EVENTSOURCE_ID)
        assert route.called
        assert result == eventsource_detail_response["data"]
        assert result["id"] == EVENTSOURCE_ID
        await er_client.close()


@pytest.mark.asyncio
async def test_get_eventsource_not_found(er_client, not_found_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"activity/eventsource/{EVENTSOURCE_ID}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json=not_found_response)
        with pytest.raises(ERClientNotFound):
            await er_client.get_eventsource(EVENTSOURCE_ID)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_eventsource_success(er_client, eventsource_patched_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.patch(f"activity/eventsource/{EVENTSOURCE_ID}")
        route.return_value = httpx.Response(httpx.codes.OK, json=eventsource_patched_response)
        result = await er_client.patch_eventsource(
            EVENTSOURCE_ID, {"display": "Renamed Source"}
        )
        assert route.called
        assert result == eventsource_patched_response["data"]
        assert result["display"] == "Renamed Source"
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_eventsource_not_found(er_client, not_found_response):
    async with respx.mock(base_url=er_client._api_root("v1.0"), assert_all_called=False) as respx_mock:
        route = respx_mock.patch(f"activity/eventsource/{EVENTSOURCE_ID}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json=not_found_response)
        with pytest.raises(ERClientNotFound):
            await er_client.patch_eventsource(EVENTSOURCE_ID, {"display": "X"})
        assert route.called
        await er_client.close()
