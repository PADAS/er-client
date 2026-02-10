import json
from unittest.mock import MagicMock, patch

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
