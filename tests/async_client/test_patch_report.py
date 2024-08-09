import httpx
import pytest
import respx


@pytest.mark.asyncio
async def test_patch_report_success(er_client, report_updated_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a successful response
        event_id = "fake-id"
        route = respx_mock.patch(f"activity/event/{event_id}")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=report_updated_response)
        # Send an event using the async client
        response = await er_client.patch_report(
            event_id=event_id,
            data={
                "event_type": "wilddog_sighting_rep",
                "event_details": {"species": "Wilddog"}
            }
        )
        assert route.called  # Check that the api endpoint was called
        assert response == report_updated_response['data']
        await er_client.close()
