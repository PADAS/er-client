import json
from unittest.mock import MagicMock

import pytest
import requests

from erclient.client import ERClient


def _mock_response(status_code, json_data=None, text=None, ok=None, url="https://fake-site.erdomain.org/api/v1.0/mock"):
    """Create a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.url = url
    if json_data is not None:
        resp.text = json.dumps(json_data)
        resp.json.return_value = json_data
    elif text is not None:
        resp.text = text
    else:
        resp.text = ""
    if ok is not None:
        resp.ok = ok
    else:
        resp.ok = 200 <= status_code < 300
    return resp


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
def single_event_response():
    """Response from activity/event/{id} -- single event detail."""
    return {
        "data": {
            "id": "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f",
            "location": {"latitude": 20.806785, "longitude": -55.784995},
            "time": "2023-01-11T12:30:02-08:00",
            "end_time": None,
            "serial_number": 76819,
            "message": "",
            "provenance": "",
            "event_type": "rainfall_rep",
            "priority": 0,
            "priority_label": "Gray",
            "attributes": {},
            "comment": None,
            "title": "Rainfall",
            "notes": [],
            "reported_by": None,
            "state": "new",
            "event_details": {"height_m": 5, "amount_mm": 8},
            "contains": [],
            "is_linked_to": [],
            "is_contained_in": [],
            "files": [],
            "related_subjects": [],
            "sort_at": "2023-01-12T04:18:25.573925-08:00",
            "patrol_segments": [],
            "geometry": None,
            "updated_at": "2023-01-12T04:18:25.573925-08:00",
            "created_at": "2023-01-12T04:18:25.574854-08:00",
            "icon_id": "rainfall_rep",
            "event_category": "monitoring",
            "url": "https://fake-site.erdomain.org/api/v1.0/activity/event/9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f",
            "image_url": "https://fake-site.erdomain.org/static/sprite-src/rainfall_rep.svg",
            "geojson": {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-55.784995, 20.806785]},
                "properties": {
                    "message": "",
                    "datetime": "2023-01-11T20:30:02+00:00",
                    "image": "https://fake-site.erdomain.org/static/sprite-src/rainfall_rep.svg",
                    "icon": {
                        "iconUrl": "https://fake-site.erdomain.org/static/sprite-src/rainfall_rep.svg",
                        "iconSize": [25, 25],
                        "iconAncor": [12, 12],
                        "popupAncor": [0, -13],
                        "className": "dot",
                    },
                },
            },
            "is_collection": False,
            "updates": [
                {
                    "message": "Added",
                    "time": "2023-01-12T12:18:25.585183+00:00",
                    "user": {
                        "username": "gundi_serviceaccount",
                        "first_name": "Gundi",
                        "last_name": "Service Account",
                        "id": "c925e69e-51cf-43d0-b659-2000ae023664",
                        "content_type": "accounts.user",
                    },
                    "type": "add_event",
                }
            ],
            "patrols": [],
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def single_event_with_notes_response():
    """Response with notes included."""
    return {
        "data": {
            "id": "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f",
            "location": {"latitude": 20.806785, "longitude": -55.784995},
            "time": "2023-01-11T12:30:02-08:00",
            "end_time": None,
            "serial_number": 76819,
            "message": "",
            "provenance": "",
            "event_type": "rainfall_rep",
            "priority": 0,
            "priority_label": "Gray",
            "attributes": {},
            "comment": None,
            "title": "Rainfall",
            "notes": [
                {
                    "id": "abc12345-0000-0000-0000-000000000001",
                    "text": "Initial observation noted heavy rainfall.",
                    "created_at": "2023-01-12T04:20:00.000000-08:00",
                }
            ],
            "reported_by": None,
            "state": "new",
            "event_details": {"height_m": 5, "amount_mm": 8},
            "contains": [],
            "is_linked_to": [],
            "is_contained_in": [],
            "files": [],
            "related_subjects": [],
            "sort_at": "2023-01-12T04:18:25.573925-08:00",
            "patrol_segments": [],
            "geometry": None,
            "updated_at": "2023-01-12T04:18:25.573925-08:00",
            "created_at": "2023-01-12T04:18:25.574854-08:00",
            "icon_id": "rainfall_rep",
            "event_category": "monitoring",
            "url": "https://fake-site.erdomain.org/api/v1.0/activity/event/9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f",
            "is_collection": False,
            "updates": [],
            "patrols": [],
        },
        "status": {"code": 200, "message": "OK"},
    }


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
