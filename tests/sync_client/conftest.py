import pytest

from erclient.client import ERClient


@pytest.fixture
def er_server_info():
    return {
        "service_root": "https://fake-site.erdomain.org/api/v1.0",
        "username": "test",
        "password": "test",
        "token": "1110c87681cd1d12ad07c2d0f57d15d6079ae5d8",
        "token_url": "https://fake-auth.erdomain.org/oauth2/token",
        "client_id": "das_web_client",
        "provider_key": "testintegration",
    }


@pytest.fixture
def er_client(er_server_info):
    return ERClient(**er_server_info)


@pytest.fixture
def message():
    return {
        "message_type": "inbox",
        "text": "A test message!",
        "message_time": "2025-06-05T11:07:37.401Z",
        "device_location": {
            "latitude": -51.687,
            "longitude": -72.710,
        },
        "additional": {
            "status": {
                "autonomous": 0,
                "lowBattery": 1,
                "intervalChange": 0,
                "resetDetected": 0,
            }
        },
    }


@pytest.fixture
def message_created_response():
    return {
        "data": {
            "id": "da783214-0d79-4d8c-ba6c-687688e3f6e7",
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
            "text": "A test message!",
            "status": "received",
            "device_location": {"latitude": -51.687, "longitude": -72.71},
            "message_time": "2025-06-05T04:07:37.401000-07:00",
            "read": False,
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def message_detail_response():
    return {
        "data": {
            "id": "da783214-0d79-4d8c-ba6c-687688e3f6e7",
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
            "text": "A test message!",
            "status": "received",
            "device_location": {"latitude": -51.687, "longitude": -72.71},
            "message_time": "2025-06-05T04:07:37.401000-07:00",
            "read": False,
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def get_messages_single_page_response():
    return {
        "data": {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": "da783214-0d79-4d8c-ba6c-687688e3f6e7",
                    "sender": None,
                    "receiver": None,
                    "device": "443724d6-043f-4014-bea6-4d80a38469c8",
                    "message_type": "inbox",
                    "text": "First message",
                    "status": "received",
                    "device_location": {"latitude": -51.687, "longitude": -72.71},
                    "message_time": "2025-06-05T04:07:37.401000-07:00",
                    "read": False,
                },
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
    }


@pytest.fixture
def get_messages_page_one_response():
    return {
        "data": {
            "count": 3,
            "next": "https://fake-site.erdomain.org/api/v1.0/messages?page=2&page_size=2",
            "previous": None,
            "results": [
                {
                    "id": "da783214-0d79-4d8c-ba6c-687688e3f6e7",
                    "sender": None,
                    "receiver": None,
                    "device": "443724d6-043f-4014-bea6-4d80a38469c8",
                    "message_type": "inbox",
                    "text": "First message",
                    "status": "received",
                    "device_location": {"latitude": -51.687, "longitude": -72.71},
                    "message_time": "2025-06-05T04:07:37.401000-07:00",
                    "read": False,
                },
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
    }


@pytest.fixture
def get_messages_page_two_response():
    return {
        "data": {
            "count": 3,
            "next": None,
            "previous": "https://fake-site.erdomain.org/api/v1.0/messages?page_size=2",
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
    }
