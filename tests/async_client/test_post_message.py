import httpx
import pytest
import respx



@pytest.mark.asyncio
async def test_post_message_success(er_client, message, message_received_response):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a successful response
        route = respx_mock.post('messages')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=message_received_response)
        # Send an event using the async client
        response = await er_client.post_message(message=message, params={"manufacturer_id": "2175752245"})
        assert route.called  # Check that the api endpoint was called
        assert response == message_received_response
        await er_client.close()

