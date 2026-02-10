import httpx
import pytest
import respx


@pytest.fixture
def get_messages_single_page_response(message_received_response):
    return {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            message_received_response,
            {
                "id": "ab123456-0d79-4d8c-ba6c-687688e3f6e7",
                "sender": {
                    "content_type": "observations.subject",
                    "id": "d2bd0ac8-080d-4be9-a8c2-2250623e6782",
                    "name": "gundi2",
                    "subject_type": "unassigned",
                    "subject_subtype": "mm-inreach-test",
                    "common_name": None,
                    "additional": {},
                    "created_at": "2025-06-05T07:05:12.817899-07:00",
                    "updated_at": "2025-06-05T07:05:12.817926-07:00",
                    "is_active": True,
                    "user": None,
                    "tracks_available": False,
                    "image_url": "/static/pin-black.svg",
                },
                "receiver": None,
                "device": "443724d6-043f-4014-bea6-4d80a38469c8",
                "message_type": "inbox",
                "text": "Second test message",
                "status": "received",
                "device_location": {"latitude": -51.687, "longitude": -72.71},
                "message_time": "2025-06-05T04:08:00.000000-07:00",
                "read": False,
            },
        ],
    }


@pytest.fixture
def get_messages_page_one_response(message_received_response):
    return {
        "count": 3,
        "next": "https://fake-site.erdomain.org/api/v1.0/messages?page=2&page_size=2&use_cursor=true",
        "previous": None,
        "results": [
            message_received_response,
            {
                "id": "ab123456-0d79-4d8c-ba6c-687688e3f6e7",
                "sender": None,
                "receiver": None,
                "device": "443724d6-043f-4014-bea6-4d80a38469c8",
                "message_type": "inbox",
                "text": "Second message",
                "status": "received",
                "device_location": {"latitude": -51.687, "longitude": -72.71},
                "message_time": "2025-06-05T04:08:00.000000-07:00",
                "read": False,
            },
        ],
    }


@pytest.fixture
def get_messages_page_two_response():
    return {
        "count": 3,
        "next": None,
        "previous": "https://fake-site.erdomain.org/api/v1.0/messages?page_size=2&use_cursor=true",
        "results": [
            {
                "id": "cd789012-0d79-4d8c-ba6c-687688e3f6e7",
                "sender": None,
                "receiver": None,
                "device": "443724d6-043f-4014-bea6-4d80a38469c8",
                "message_type": "inbox",
                "text": "Third message",
                "status": "received",
                "device_location": {"latitude": -51.687, "longitude": -72.71},
                "message_time": "2025-06-05T04:09:00.000000-07:00",
                "read": True,
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_messages_single_page(er_client, get_messages_single_page_response):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("messages").return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": get_messages_single_page_response},
        )

        messages = []
        async for msg in er_client.get_messages():
            messages.append(msg)

        assert len(messages) == 2
        assert messages[0]["id"] == "da783214-0d79-4d8c-ba6c-687688e3f6e7"
        assert messages[1]["id"] == "ab123456-0d79-4d8c-ba6c-687688e3f6e7"
        await er_client.close()


@pytest.mark.asyncio
async def test_get_messages_paginated(
    er_client, get_messages_page_one_response, get_messages_page_two_response
):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        # First page
        respx_mock.get("messages").mock(
            side_effect=[
                httpx.Response(
                    httpx.codes.OK,
                    json={"data": get_messages_page_one_response},
                ),
                httpx.Response(
                    httpx.codes.OK,
                    json={"data": get_messages_page_two_response},
                ),
            ]
        )

        messages = []
        async for msg in er_client.get_messages(page_size=2):
            messages.append(msg)

        assert len(messages) == 3
        assert messages[0]["id"] == "da783214-0d79-4d8c-ba6c-687688e3f6e7"
        assert messages[2]["id"] == "cd789012-0d79-4d8c-ba6c-687688e3f6e7"
        await er_client.close()


@pytest.mark.asyncio
async def test_get_messages_empty(er_client):
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        respx_mock.get("messages").return_value = httpx.Response(
            httpx.codes.OK,
            json={"data": {"count": 0, "next": None, "previous": None, "results": []}},
        )

        messages = []
        async for msg in er_client.get_messages():
            messages.append(msg)

        assert len(messages) == 0
        await er_client.close()
