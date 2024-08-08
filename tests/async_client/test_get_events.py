import json

import httpx
import pytest
import respx


@pytest.mark.asyncio
async def test_get_events_with_filter(er_client, get_events_response_single_page):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('activity/events')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=get_events_response_single_page
        )
        start_datetime = "2023-11-10T00:00:00-06:00"
        json_filter = json.dumps(
            {
                "date_range": {
                    "lower": start_datetime,
                }
            }
        )

        i = 0
        async for event in er_client.get_events(filter=json_filter):
            assert event
            assert event == get_events_response_single_page["results"][i]
            i += 1

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_events_in_batches(er_client, get_events_response_single_page):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('activity/events')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=get_events_response_single_page
        )

        i = 0
        batches = 0
        batch_size = 2
        async for batch in er_client.get_events(batch_size=batch_size):
            assert batch
            assert isinstance(batch, list)
            assert len(batch) <= batch_size  # The last batch may be smaller
            batches += 1
            for event in batch:
                assert event == get_events_response_single_page["results"][i]
                i += 1

        assert batches == len(
            get_events_response_single_page["results"]) // batch_size + 1
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_events_with_pagination(er_client, get_events_response_page_one, get_events_response_page_two):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('activity/events')
        route.side_effect = (  # Simulate pagination
            httpx.Response(
                httpx.codes.OK,
                json=get_events_response_page_one
            ),
            httpx.Response(
                httpx.codes.OK,
                json=get_events_response_page_two
            )
        )

        # Check that the client handles pagination correctly
        i = 0
        page_size = 5
        page_response = get_events_response_page_one
        async for event in er_client.get_events():
            assert event
            if i == page_size:
                page_response = get_events_response_page_two
                i = 0
            assert event == page_response["results"][i]
            i += 1

        assert route.called
        await er_client.close()
