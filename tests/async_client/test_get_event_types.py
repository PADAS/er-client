import httpx
import pytest
import respx


@pytest.mark.asyncio
async def test_get_events_types(er_client, get_events_types_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
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
