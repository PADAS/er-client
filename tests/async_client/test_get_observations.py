
import httpx
import pytest
import respx


@pytest.mark.asyncio
async def test_get_observations_with_filter(er_client, get_observations_response_single_page):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('observations')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=get_observations_response_single_page
        )
        start_datetime = "2023-11-10T00:00:00-06:00"

        i = 0
        async for event in er_client.get_observations(start=start_datetime):
            assert event
            assert event == get_observations_response_single_page["results"][i]
            i += 1

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_observations_in_batches(er_client, get_observations_response_single_page):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('observations')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=get_observations_response_single_page
        )

        i = 0
        batches = 0
        batch_size = 2
        async for batch in er_client.get_observations(batch_size=2):
            assert batch
            assert isinstance(batch, list)
            assert len(batch) <= batch_size  # The last batch may be smaller
            batches += 1
            for event in batch:
                assert event == get_observations_response_single_page["results"][i]
                i += 1

        assert batches == 3
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_observations_with_pagination(er_client, get_observations_response_page_one, get_observations_response_page_two):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get('observations')
        route.side_effect = (  # Simulate pagination
            httpx.Response(
                httpx.codes.OK,
                json=get_observations_response_page_one
            ),
            httpx.Response(
                httpx.codes.OK,
                json=get_observations_response_page_two
            )
        )

        # Check that the client handles pagination correctly
        i = 0
        page_size = 5
        page_response = get_observations_response_page_one
        async for event in er_client.get_observations():
            assert event
            if i == page_size:
                page_response = get_observations_response_page_two
                i = 0
            assert event == page_response["results"][i]
            i += 1

        assert route.called
        await er_client.close()
