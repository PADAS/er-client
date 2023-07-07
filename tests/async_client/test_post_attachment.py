import httpx
import pytest
import respx


@pytest.mark.asyncio
async def test_post_report_attachment_success(
        er_client, report_created_response, camera_trap_file, attachment_created_response
):
    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # Mock the call to the ER API and simulate a successful response
        # id of a previously-created report
        er_report_id = report_created_response["data"]["id"]
        route = respx_mock.post(
            f'activity/event/{er_report_id}/files/')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=attachment_created_response)
        # Send an attachment for a previously-created report
        response = await er_client.post_report_attachment(
            report_id=er_report_id, file=camera_trap_file
        )
        assert route.called  # Check that the api endpoint was called
        assert response == attachment_created_response['data']
        await er_client.close()
        camera_trap_file.close()
