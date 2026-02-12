import httpx
import pytest
import respx

from erclient import ERClientNotFound


@pytest.mark.asyncio
async def test_get_message_success(er_client, message_received_response):
    message_id = "da783214-0d79-4d8c-ba6c-687688e3f6e7"
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"messages/{message_id}")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": message_received_response},
        )

        result = await er_client.get_message(message_id)
        assert route.called
        assert result == message_received_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_message_not_found(er_client, not_found_response):
    message_id = "nonexistent-id"
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f"messages/{message_id}")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json=not_found_response,
        )

        with pytest.raises(ERClientNotFound):
            await er_client.get_message(message_id)
        assert route.called
        await er_client.close()
