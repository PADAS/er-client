import httpx
import pytest
import respx


@pytest.mark.asyncio
async def test_get_events_types(er_client, get_events_types_response):
    # Client assembles API root as {base}/api/v1.0
    api_root = er_client._api_root("v1.0")
    async with respx.mock(
            base_url=api_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('activity/events/eventtypes')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=get_events_types_response
        )

        event_types = await er_client.get_event_types()

        assert route.called
        await er_client.close()
        assert event_types == get_events_types_response['data']


@pytest.mark.asyncio
async def test_get_event_types_v2_uses_v2_path(er_client, get_events_types_response):
    """get_event_types(version="v2.0") uses .../api/v2.0/activity/eventtypes."""
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(
            base_url=api_root_v2, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('activity/eventtypes')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=get_events_types_response
        )

        event_types = await er_client.get_event_types(version="v2.0")

        assert route.called
        await er_client.close()
        assert event_types == get_events_types_response['data']


@pytest.mark.asyncio
async def test_get_event_type_version_alias_v2_uses_v2_api_root(er_client):
    """get_event_type(version="v2") alias is normalized; request goes to .../api/v2.0/activity/eventtypes/."""
    event_type_slug = "test_event_type"
    get_response = {"data": {"id": "et-uuid",
                             "value": event_type_slug, "display": "Test"}}
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(base_url=api_root_v2, assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"activity/eventtypes/{event_type_slug}")
        route.return_value = httpx.Response(httpx.codes.OK, json=get_response)

        result = await er_client.get_event_type(event_type_slug, version="v2")

        assert route.called
        await er_client.close()
        assert result == get_response["data"]
