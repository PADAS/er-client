from pathlib import Path

import pytest

from erclient.client import AsyncERClient


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
    return AsyncERClient(**er_server_info)


# ToDo: Use factories?
@pytest.fixture
def position():
    return {
        "manufacturer_id": "018910980",
        "source_type": "tracking-device",
        "subject_name": "Test Truck",
        "recorded_at": "2023-01-11 19:41:00+02:00",
        "location": {"lon": 35.43903, "lat": -1.59083},
        "additional": {"voltage": "7.4", "fuel_level": 71, "speed": "41 kph"},
    }


@pytest.fixture
def report():
    return {
        "title": "Rainfall",
        "event_type": "rainfall_rep",
        "event_details": {"amount_mm": 6, "height_m": 3},
        "time": "2023-01-11 17:28:02-03:00",
        "location": {"longitude": -55.784992, "latitude": 20.806785},
    }


@pytest.fixture
def camera_trap_payload():
    return {
        "file": "cameratrap.jpg",
        "camera_name": "Test camera",
        "camera_description": "Camera Trap",
        "time": "2023-01-11 17:05:00-03:00",
        "location": '{"longitude": -122.5, "latitude": 48.65}',
    }


@pytest.fixture
def camera_trap_conflict_response():
    return {"data": None, "status": {"code": 409, "message": "Conflict"}}


@pytest.fixture
def position_created_response():
    return {"data": {}, "status": {"code": 201, "message": "Created"}}


@pytest.fixture
def bad_request_response():
    # Typical response in skylight connections when the event type is missing in the ER site
    return {
        "data": [[{"event_type": {"event_type": "Value 'detection_alert_rep' does not exist."}}]],
        "status": {"code": 400, "message": "Bad Request"}
    }


@pytest.fixture
def bad_credentials_response():
    # Typical response in skylight connections when the event type is missing in the ER site
    return {
        "data": [],
        "status": {"code": 401, "message": "Unauthorized", "detail": "Authentication credentials were not provided."}
    }


@pytest.fixture
def forbidden_response():
    # Typical response when a token/user doesn't have permissions to create events in certain category
    return {
        "data": [],
        "status": {"code": 403, "message": "Forbidden", "detail": "You do not have permission to perform this action."}
    }


@pytest.fixture
def not_found_response():
    # ToDo. Get some real examples
    return {
        "status": {
            "code": 404,
            "detail": "a provider with the given key does not exist",
        }
    }


@pytest.fixture
def conflict_response():
    return {
        "status": {
            "code": 409,
            "detail": "an observation for this source and second already exists",
        }
    }


@pytest.fixture
def report_created_response():
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
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def report_updated_response():
    return {
        'data': {
            'id': 'bf7e56c7-0751-4899-844f-b5888eb813b1',
            'location': {'latitude': 13.688635, 'longitude': 13.783065},
            'time': '2024-07-24T07:18:12-07:00',
            'end_time': None,
            'message': '',
            'provenance': '',
            'event_type': 'wilddog_sighting_rep',
            'priority': 0,
            'priority_label': 'Gray',
            'attributes': {},
            'comment': None,
            'title': 'Animal Detected Test Event',
            'notes': [],
            'reported_by': None,
            'state': 'active',
            'event_details': {'species': 'Wilddog'},
            'contains': [], 'is_linked_to': [], 'is_contained_in': [],
            'files': [], 'related_subjects': [], 'sort_at': '2024-07-24T08:06:06.788195-07:00',
            'patrol_segments': [], 'geometry': None, 'updated_at': '2024-07-24T08:06:06.788195-07:00',
            'created_at': '2024-07-24T07:54:04.506420-07:00', 'icon_id': 'wild_dog_rep',
            'serial_number': 148556, 'event_category': 'monitoring',
            'url': 'https://gundi-dev.staging.pamdas.org/api/v1.0/activity/event/bf7e56c7-0751-4899-844f-b5888eb813b1',
            'image_url': 'https://gundi-dev.staging.pamdas.org/static/sprite-src/wild_dog_rep.svg',
            'geojson': {
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [13.783065, 13.688635]},
                'properties': {'message': '', 'datetime': '2024-07-24T14:18:12+00:00',
                               'image': 'https://gundi-dev.staging.pamdas.org/static/sprite-src/wild_dog_rep.svg',
                               'icon': {
                                   'iconUrl': 'https://gundi-dev.staging.pamdas.org/static/sprite-src/wild_dog_rep.svg',
                                   'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                   'className': 'dot'}}
            },
            'is_collection': False,
            'updates': [{
                'message': 'Changed State: active → active, Changed Event type: 1ef54da1-25d2-42df-b2a1-f529c122d94c → a4e413d5-ac39-42bf-8451-04da99f73ab0',
                'time': '2024-07-24T15:06:06.796070+00:00',
                'user': {
                    'username': 'gundi_serviceaccount',
                    'first_name': 'Gundi',
                    'last_name': 'Service Account',
                    'id': '21706d8b-98f7-4be1-bf9e-ad1639a63914',
                    'content_type': 'accounts.user'},
                'type': 'update_event_state'},
                {
                    'message': 'Changed State: new → active',
                    'time': '2024-07-24T15:06:06.758903+00:00',
                    'user': {
                        'username': 'gundi_serviceaccount',
                        'first_name': 'Gundi',
                        'last_name': 'Service Account',
                        'id': '21706d8b-98f7-4be1-bf9e-ad1639a63914',
                        'content_type': 'accounts.user'},
                    'type': 'read'},
                {
                    'message': 'Updated fields: Species',
                    'time': '2024-07-24T15:06:06.709827+00:00',
                    'text': '',
                    'user': {
                        'username': 'gundi_serviceaccount',
                        'first_name': 'Gundi',
                        'last_name': 'Service Account',
                        'id': '21706d8b-98f7-4be1-bf9e-ad1639a63914',
                        'content_type': 'accounts.user'},
                    'type': 'update_event'},
                {
                    'message': 'Created',
                    'time': '2024-07-24T14:54:04.515311+00:00',
                    'user': {
                        'username': 'gundi_serviceaccount',
                        'first_name': 'Gundi',
                        'last_name': 'Service Account',
                        'id': '21706d8b-98f7-4be1-bf9e-ad1639a63914',
                        'content_type': 'accounts.user'},
                    'type': 'add_event'}],
            'patrols': []},
        'status': {'code': 200, 'message': 'OK'}
    }


@pytest.fixture
def camera_trap_report_created_response():
    return {
        "data": {"group_id": "f14f241f-ad51-4c06-85ca-0aca8c5965a0"},
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def attachment_created_response():
    return {
        "data": {
            "id": "8e095bc9-94bd-44bd-aeaf-d2765de1fd12",
            "comment": "",
            "created_at": "2023-07-03T07:09:08.814290-07:00",
            "updated_at": "2023-07-03T07:09:08.814313-07:00",
            "updates": [
                {
                    "message": "File Added",
                    "time": "2023-07-03T14:09:08.820647+00:00",
                    "text": "",
                    "user": {
                        "username": "gundi_serviceaccount",
                        "first_name": "Gundi",
                        "last_name": "Service Account",
                        "id": "558388d0-bb42-43f2-a2c3-6775bcb5f315",
                        "content_type": "accounts.user",
                    },
                    "type": "add_eventfile",
                }
            ],
            "url": "https://gundi-load-testing.pamdas.org/api/v1.0/activity/event/73846dd9-42ed-4c22-b8e8-fbc1cd19299b/file/7f095bc9-94bd-44bd-aeaf-d2765de1fdec/",
            "images": {
                "original": "https://gundi-load-testing.pamdas.org/api/v1.0/activity/event/73846dd9-42ed-4c22-b8e8-fbc1cd19299b/file/7f095bc9-94bd-44bd-aeaf-d2765de1fdec/original/f1a8894b-ff2e-4286-90a0-8f17303e91df_2023-06-26-1053_leopard.jpg",
                "icon": "https://gundi-load-testing.pamdas.org/api/v1.0/activity/event/73846dd9-42ed-4c22-b8e8-fbc1cd19299b/file/7f095bc9-94bd-44bd-aeaf-d2765de1fdec/icon/f1a8894b-ff2e-4286-90a0-8f17303e91df_2023-06-26-1053_leopard.jpg",
                "thumbnail": "https://gundi-load-testing.pamdas.org/api/v1.0/activity/event/73846dd9-42ed-4c22-b8e8-fbc1cd19299b/file/7f095bc9-94bd-44bd-aeaf-d2765de1fdec/thumbnail/f1a8894b-ff2e-4286-90a0-8f17303e91df_2023-06-26-1053_leopard.jpg",
                "large": "https://gundi-load-testing.pamdas.org/api/v1.0/activity/event/73846dd9-42ed-4c22-b8e8-fbc1cd19299b/file/7f095bc9-94bd-44bd-aeaf-d2765de1fdec/large/f1a8894b-ff2e-4286-90a0-8f17303e91df_2023-06-26-1053_leopard.jpg",
                "xlarge": "https://gundi-load-testing.pamdas.org/api/v1.0/activity/event/73846dd9-42ed-4c22-b8e8-fbc1cd19299b/file/7f095bc9-94bd-44bd-aeaf-d2765de1fdec/xlarge/f1a8894b-ff2e-4286-90a0-8f17303e91df_2023-06-26-1053_leopard.jpg",
            },
            "filename": "f1a8894b-ff2e-4286-90a0-8f17303e91df_2023-06-26-1053_leopard.jpg",
            "file_type": "image",
            "icon_url": "https://gundi-load-testing.pamdas.org/api/v1.0/activity/event/73846dd9-42ed-4c22-b8e8-fbc1cd19299b/file/7f095bc9-94bd-44bd-aeaf-d2765de1fdec/icon/f1a8894b-ff2e-4286-90a0-8f17303e91df_2023-06-26-1053_leopard.jpg",
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def camera_trap_file():
    file_path = Path(__file__).resolve().parent.parent.joinpath(
        "images/cameratrap.jpg")
    # ToDo: open the files using async (aiofiles)
    return open(file_path, "rb")

@pytest.fixture
def message():
    return {
        "message_type": "inbox",
        "text": "A test message!",
        "message_time": "2025-06-05T11:07:37.401Z",
        "device_location": {
            "latitude": -51.687,
            "longitude": -72.710
        },
        "additional": {
            "status": {
                "autonomous": 0,
                "lowBattery": 1,
                "intervalChange": 0,
                "resetDetected": 0
            }
        }
    }


@pytest.fixture
def message_received_response():
    return {
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
            "image_url": "/static/pin-black.svg"
        },
        "receiver": None,
        "device": "443724d6-043f-4014-bea6-4d80a38469c8",
        "message_type": "inbox",
        "text": "A test message!",
        "status": "received",
        "device_location": {
            "latitude": -51.687,
            "longitude": -72.71
        },
        "message_time": "2025-06-05T04:07:37.401000-07:00",
        "read": False
    }


@pytest.fixture
def get_events_response_single_page():
    return {
        'count': 5,
        'next': None,
        'previous': None,
        'results': [
            {'id': '5b3bf4ec-64be-427a-bdb6-60e6894ba5ed', 'location': None, 'time': '2023-11-16T15:14:35.066020-06:00',
             'end_time': None, 'serial_number': 386, 'message': '', 'provenance': '',
             'event_type': 'silence_source_provider_rep', 'priority': 0, 'priority_label': 'Gray', 'attributes': {},
             'comment': None, 'title': '265de4c0-07b8-4e30-b136-5d5a75ff5912 integration disrupted',
             'reported_by': None, 'state': 'new', 'is_contained_in': [], 'sort_at': '2023-11-16T15:14:35.067904-06:00',
             'patrol_segments': [], 'geometry': None, 'updated_at': '2023-11-16T15:14:35.067904-06:00',
             'created_at': '2023-11-16T15:14:35.068127-06:00', 'icon_id': 'silence_source_provider_rep',
             'event_details': {'report_time': '2023-11-16 21:14:34', 'silence_threshold': '00:00',
                               'last_device_reported_at': '2023-10-26 21:24:02', 'updates': []}, 'files': [],
             'related_subjects': [], 'event_category': 'analyzer_event',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5b3bf4ec-64be-427a-bdb6-60e6894ba5ed',
             'image_url': 'https://gundi-er.pamdas.org/static/generic-gray.svg', 'geojson': None,
             'is_collection': False, 'updates': [{'message': 'Created', 'time': '2023-11-16T21:14:35.072819+00:00',
                                                  'user': {'first_name': '', 'last_name': '', 'username': ''},
                                                  'type': 'add_event'}], 'patrols': []},
            {'id': '76bd95d1-de8c-44e5-834f-35e6f1bbd9f7', 'location': None, 'time': '2023-11-16T15:14:34.484414-06:00',
             'end_time': None, 'serial_number': 385, 'message': '', 'provenance': '',
             'event_type': 'silence_source_provider_rep', 'priority': 0, 'priority_label': 'Gray', 'attributes': {},
             'comment': None, 'title': 'A7a9e1ab-44e2-4585-8d4f-7770ca0b36e2 integration disrupted',
             'reported_by': None, 'state': 'new', 'is_contained_in': [], 'sort_at': '2023-11-16T15:14:34.486739-06:00',
             'patrol_segments': [], 'geometry': None, 'updated_at': '2023-11-16T15:14:34.486739-06:00',
             'created_at': '2023-11-16T15:14:34.487028-06:00', 'icon_id': 'silence_source_provider_rep',
             'event_details': {'report_time': '2023-11-16 21:14:34', 'silence_threshold': '00:01',
                               'last_device_reported_at': '2023-10-23 00:44:32', 'updates': []}, 'files': [],
             'related_subjects': [], 'event_category': 'analyzer_event',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/76bd95d1-de8c-44e5-834f-35e6f1bbd9f7',
             'image_url': 'https://gundi-er.pamdas.org/static/generic-gray.svg', 'geojson': None,
             'is_collection': False, 'updates': [{'message': 'Created', 'time': '2023-11-16T21:14:34.522653+00:00',
                                                  'user': {'first_name': '', 'last_name': '', 'username': ''},
                                                  'type': 'add_event'}], 'patrols': []},
            {'id': 'e87ccabd-7b7a-446d-bfcc-c52424dc97b5', 'location': {'latitude': 47.686, 'longitude': -122.359},
             'time': '2023-11-16T14:58:38.497389-06:00', 'end_time': None, 'serial_number': 384, 'message': '',
             'provenance': '', 'event_type': 'trailguard_rep', 'priority': 200, 'priority_label': 'Amber',
             'attributes': {}, 'comment': None, 'title': 'Trailguard Trap', 'reported_by': None, 'state': 'active',
             'is_contained_in': [], 'sort_at': '2023-11-16T14:59:03.127510-06:00', 'patrol_segments': [],
             'geometry': None, 'updated_at': '2023-11-16T14:59:03.127510-06:00',
             'created_at': '2023-11-16T14:58:47.902391-06:00', 'icon_id': 'cameratrap_rep',
             'event_details': {'labels': ['adult', 'female'], 'species': 'coyote', 'animal_count': 1, 'updates': []},
             'files': [{'id': '7fb0279d-2e2e-4529-bbcc-7fc9e49a3714', 'comment': '',
                        'created_at': '2023-11-16T14:59:03.111316-06:00',
                        'updated_at': '2023-11-16T14:59:03.111335-06:00', 'updates': [
                     {'message': 'File Added: 739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                      'time': '2023-11-16T20:59:03.120967+00:00', 'text': '',
                      'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                               'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                      'type': 'add_eventfile'}],
                        'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/',
                        'images': {
                            'original': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/original/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                            'icon': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/icon/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                            'thumbnail': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/thumbnail/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                            'large': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/large/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                            'xlarge': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/xlarge/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg'},
                        'filename': '739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg', 'file_type': 'image',
                        'icon_url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/icon/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg'}],
             'related_subjects': [], 'event_category': 'monitoring',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5',
             'image_url': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
             'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-122.359, 47.686]},
                         'properties': {'message': '', 'datetime': '2023-11-16T20:58:38.497389+00:00',
                                        'image': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                        'icon': {'iconUrl': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                                 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                                 'className': 'dot'}}}, 'is_collection': False, 'updates': [
                {'message': 'Changed State: new → active', 'time': '2023-11-16T20:59:03.149747+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'read'}, {'message': 'File Added: 739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                                   'time': '2023-11-16T20:59:03.120967+00:00', 'text': '',
                                   'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi',
                                            'last_name': 'Service Account',
                                            'id': 'ddc888bb-d642-455a-a422-7393b4f172be',
                                            'content_type': 'accounts.user'}, 'type': 'add_eventfile'},
                {'message': 'Created', 'time': '2023-11-16T20:58:47.943938+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'add_event'}], 'patrols': []},
            {'id': '81c5ea7b-0c95-41ad-9764-d42a6ba0aa00', 'location': {'latitude': 47.686, 'longitude': -122.359},
             'time': '2023-11-16T14:34:11.664952-06:00', 'end_time': None, 'serial_number': 383, 'message': '',
             'provenance': '', 'event_type': 'trailguard_rep', 'priority': 200, 'priority_label': 'Amber',
             'attributes': {}, 'comment': None, 'title': 'Trailguard Trap', 'reported_by': None, 'state': 'active',
             'is_contained_in': [], 'sort_at': '2023-11-16T14:34:15.659956-06:00', 'patrol_segments': [],
             'geometry': None, 'updated_at': '2023-11-16T14:34:15.659956-06:00',
             'created_at': '2023-11-16T14:34:13.123044-06:00', 'icon_id': 'cameratrap_rep',
             'event_details': {'labels': ['adult', 'female'], 'species': 'coyote', 'animal_count': 1, 'updates': []},
             'files': [{'id': 'dbe74373-84a4-4020-86f8-79a6c4a4408e', 'comment': '',
                        'created_at': '2023-11-16T14:34:15.646361-06:00',
                        'updated_at': '2023-11-16T14:34:15.646383-06:00', 'updates': [
                     {'message': 'File Added: e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                      'time': '2023-11-16T20:34:15.653320+00:00', 'text': '',
                      'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                               'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                      'type': 'add_eventfile'}],
                        'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/',
                        'images': {
                            'original': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/original/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'icon': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/icon/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'thumbnail': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/thumbnail/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'large': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/large/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'xlarge': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/xlarge/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg'},
                        'filename': 'e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg', 'file_type': 'image',
                        'icon_url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/icon/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg'}],
             'related_subjects': [], 'event_category': 'monitoring',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00',
             'image_url': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
             'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-122.359, 47.686]},
                         'properties': {'message': '', 'datetime': '2023-11-16T20:34:11.664952+00:00',
                                        'image': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                        'icon': {'iconUrl': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                                 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                                 'className': 'dot'}}}, 'is_collection': False, 'updates': [
                {'message': 'Changed State: new → active', 'time': '2023-11-16T20:34:15.671163+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'read'}, {'message': 'File Added: e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                                   'time': '2023-11-16T20:34:15.653320+00:00', 'text': '',
                                   'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi',
                                            'last_name': 'Service Account',
                                            'id': 'ddc888bb-d642-455a-a422-7393b4f172be',
                                            'content_type': 'accounts.user'}, 'type': 'add_eventfile'},
                {'message': 'Created', 'time': '2023-11-16T20:34:13.135632+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'add_event'}], 'patrols': []},
            {'id': '5cd12145-4490-4324-91ac-6865943fd26f', 'location': {'latitude': 47.686, 'longitude': -122.359},
             'time': '2023-11-16T14:32:15.109547-06:00', 'end_time': None, 'serial_number': 382, 'message': '',
             'provenance': '', 'event_type': 'trailguard_rep', 'priority': 200, 'priority_label': 'Amber',
             'attributes': {}, 'comment': None, 'title': 'Trailguard Trap', 'reported_by': None, 'state': 'active',
             'is_contained_in': [], 'sort_at': '2023-11-16T14:32:36.117190-06:00', 'patrol_segments': [],
             'geometry': None, 'updated_at': '2023-11-16T14:32:36.117190-06:00',
             'created_at': '2023-11-16T14:32:22.951909-06:00', 'icon_id': 'cameratrap_rep',
             'event_details': {'labels': ['adult', 'female'], 'species': 'coyote', 'animal_count': 1, 'updates': []},
             'files': [{'id': '6c258455-b3de-4613-bc00-cf6c5f4f1c0d', 'comment': '',
                        'created_at': '2023-11-16T14:32:36.098189-06:00',
                        'updated_at': '2023-11-16T14:32:36.098208-06:00', 'updates': [
                     {'message': 'File Added: 22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                      'time': '2023-11-16T20:32:36.109299+00:00', 'text': '',
                      'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                               'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                      'type': 'add_eventfile'}],
                        'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/',
                        'images': {
                            'original': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/original/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'icon': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/icon/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'thumbnail': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/thumbnail/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'large': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/large/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'xlarge': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/xlarge/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg'},
                        'filename': '22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg', 'file_type': 'image',
                        'icon_url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/icon/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg'}],
             'related_subjects': [], 'event_category': 'monitoring',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f',
             'image_url': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
             'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-122.359, 47.686]},
                         'properties': {'message': '', 'datetime': '2023-11-16T20:32:15.109547+00:00',
                                        'image': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                        'icon': {'iconUrl': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                                 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                                 'className': 'dot'}}}, 'is_collection': False, 'updates': [
                {'message': 'Changed State: new → active', 'time': '2023-11-16T20:32:36.128796+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'read'}, {'message': 'File Added: 22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                                   'time': '2023-11-16T20:32:36.109299+00:00', 'text': '',
                                   'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi',
                                            'last_name': 'Service Account',
                                            'id': 'ddc888bb-d642-455a-a422-7393b4f172be',
                                            'content_type': 'accounts.user'}, 'type': 'add_eventfile'},
                {'message': 'Created', 'time': '2023-11-16T20:32:23.000575+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'add_event'}], 'patrols': []}
        ]
    }


@pytest.fixture
def get_events_response_page_one():
    return {
        'count': 9,
        'next': 'https://gundi-er.pamdas.org/api/v1.0/activity/events?filter=%7B%22date_range%22%3A+%7B%22lower%22%3A+%222023-11-10T00%3A00%3A00-06%3A00%22%7D%7D&page=2&page_size=5&use_cursor=true',
        'previous': None,
        'results': [
            {'id': '5b3bf4ec-64be-427a-bdb6-60e6894ba5ed', 'location': None, 'time': '2023-11-16T15:14:35.066020-06:00',
             'end_time': None, 'serial_number': 386, 'message': '', 'provenance': '',
             'event_type': 'silence_source_provider_rep', 'priority': 0, 'priority_label': 'Gray', 'attributes': {},
             'comment': None, 'title': '265de4c0-07b8-4e30-b136-5d5a75ff5912 integration disrupted',
             'reported_by': None, 'state': 'new', 'is_contained_in': [], 'sort_at': '2023-11-16T15:14:35.067904-06:00',
             'patrol_segments': [], 'geometry': None, 'updated_at': '2023-11-16T15:14:35.067904-06:00',
             'created_at': '2023-11-16T15:14:35.068127-06:00', 'icon_id': 'silence_source_provider_rep',
             'event_details': {'report_time': '2023-11-16 21:14:34', 'silence_threshold': '00:00',
                               'last_device_reported_at': '2023-10-26 21:24:02', 'updates': []}, 'files': [],
             'related_subjects': [], 'event_category': 'analyzer_event',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5b3bf4ec-64be-427a-bdb6-60e6894ba5ed',
             'image_url': 'https://gundi-er.pamdas.org/static/generic-gray.svg', 'geojson': None,
             'is_collection': False, 'updates': [{'message': 'Created', 'time': '2023-11-16T21:14:35.072819+00:00',
                                                  'user': {'first_name': '', 'last_name': '', 'username': ''},
                                                  'type': 'add_event'}], 'patrols': []},
            {'id': '76bd95d1-de8c-44e5-834f-35e6f1bbd9f7', 'location': None, 'time': '2023-11-16T15:14:34.484414-06:00',
             'end_time': None, 'serial_number': 385, 'message': '', 'provenance': '',
             'event_type': 'silence_source_provider_rep', 'priority': 0, 'priority_label': 'Gray', 'attributes': {},
             'comment': None, 'title': 'A7a9e1ab-44e2-4585-8d4f-7770ca0b36e2 integration disrupted',
             'reported_by': None, 'state': 'new', 'is_contained_in': [], 'sort_at': '2023-11-16T15:14:34.486739-06:00',
             'patrol_segments': [], 'geometry': None, 'updated_at': '2023-11-16T15:14:34.486739-06:00',
             'created_at': '2023-11-16T15:14:34.487028-06:00', 'icon_id': 'silence_source_provider_rep',
             'event_details': {'report_time': '2023-11-16 21:14:34', 'silence_threshold': '00:01',
                               'last_device_reported_at': '2023-10-23 00:44:32', 'updates': []}, 'files': [],
             'related_subjects': [], 'event_category': 'analyzer_event',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/76bd95d1-de8c-44e5-834f-35e6f1bbd9f7',
             'image_url': 'https://gundi-er.pamdas.org/static/generic-gray.svg', 'geojson': None,
             'is_collection': False, 'updates': [{'message': 'Created', 'time': '2023-11-16T21:14:34.522653+00:00',
                                                  'user': {'first_name': '', 'last_name': '', 'username': ''},
                                                  'type': 'add_event'}], 'patrols': []},
            {'id': 'e87ccabd-7b7a-446d-bfcc-c52424dc97b5', 'location': {'latitude': 47.686, 'longitude': -122.359},
             'time': '2023-11-16T14:58:38.497389-06:00', 'end_time': None, 'serial_number': 384, 'message': '',
             'provenance': '', 'event_type': 'trailguard_rep', 'priority': 200, 'priority_label': 'Amber',
             'attributes': {}, 'comment': None, 'title': 'Trailguard Trap', 'reported_by': None, 'state': 'active',
             'is_contained_in': [], 'sort_at': '2023-11-16T14:59:03.127510-06:00', 'patrol_segments': [],
             'geometry': None, 'updated_at': '2023-11-16T14:59:03.127510-06:00',
             'created_at': '2023-11-16T14:58:47.902391-06:00', 'icon_id': 'cameratrap_rep',
             'event_details': {'labels': ['adult', 'female'], 'species': 'coyote', 'animal_count': 1, 'updates': []},
             'files': [{'id': '7fb0279d-2e2e-4529-bbcc-7fc9e49a3714', 'comment': '',
                        'created_at': '2023-11-16T14:59:03.111316-06:00',
                        'updated_at': '2023-11-16T14:59:03.111335-06:00', 'updates': [
                     {'message': 'File Added: 739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                      'time': '2023-11-16T20:59:03.120967+00:00', 'text': '',
                      'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                               'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                      'type': 'add_eventfile'}],
                        'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/',
                        'images': {
                            'original': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/original/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                            'icon': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/icon/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                            'thumbnail': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/thumbnail/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                            'large': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/large/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                            'xlarge': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/xlarge/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg'},
                        'filename': '739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg', 'file_type': 'image',
                        'icon_url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5/file/7fb0279d-2e2e-4529-bbcc-7fc9e49a3714/icon/739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg'}],
             'related_subjects': [], 'event_category': 'monitoring',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/e87ccabd-7b7a-446d-bfcc-c52424dc97b5',
             'image_url': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
             'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-122.359, 47.686]},
                         'properties': {'message': '', 'datetime': '2023-11-16T20:58:38.497389+00:00',
                                        'image': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                        'icon': {'iconUrl': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                                 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                                 'className': 'dot'}}}, 'is_collection': False, 'updates': [
                {'message': 'Changed State: new → active', 'time': '2023-11-16T20:59:03.149747+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'read'}, {'message': 'File Added: 739b53ff-af34-458d-bcc6-897cc18a253e_godzilla.jpg',
                                   'time': '2023-11-16T20:59:03.120967+00:00', 'text': '',
                                   'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi',
                                            'last_name': 'Service Account',
                                            'id': 'ddc888bb-d642-455a-a422-7393b4f172be',
                                            'content_type': 'accounts.user'}, 'type': 'add_eventfile'},
                {'message': 'Created', 'time': '2023-11-16T20:58:47.943938+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'add_event'}], 'patrols': []},
            {'id': '81c5ea7b-0c95-41ad-9764-d42a6ba0aa00', 'location': {'latitude': 47.686, 'longitude': -122.359},
             'time': '2023-11-16T14:34:11.664952-06:00', 'end_time': None, 'serial_number': 383, 'message': '',
             'provenance': '', 'event_type': 'trailguard_rep', 'priority': 200, 'priority_label': 'Amber',
             'attributes': {}, 'comment': None, 'title': 'Trailguard Trap', 'reported_by': None, 'state': 'active',
             'is_contained_in': [], 'sort_at': '2023-11-16T14:34:15.659956-06:00', 'patrol_segments': [],
             'geometry': None, 'updated_at': '2023-11-16T14:34:15.659956-06:00',
             'created_at': '2023-11-16T14:34:13.123044-06:00', 'icon_id': 'cameratrap_rep',
             'event_details': {'labels': ['adult', 'female'], 'species': 'coyote', 'animal_count': 1, 'updates': []},
             'files': [{'id': 'dbe74373-84a4-4020-86f8-79a6c4a4408e', 'comment': '',
                        'created_at': '2023-11-16T14:34:15.646361-06:00',
                        'updated_at': '2023-11-16T14:34:15.646383-06:00', 'updates': [
                     {'message': 'File Added: e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                      'time': '2023-11-16T20:34:15.653320+00:00', 'text': '',
                      'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                               'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                      'type': 'add_eventfile'}],
                        'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/',
                        'images': {
                            'original': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/original/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'icon': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/icon/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'thumbnail': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/thumbnail/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'large': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/large/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'xlarge': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/xlarge/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg'},
                        'filename': 'e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg', 'file_type': 'image',
                        'icon_url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/icon/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg'}],
             'related_subjects': [], 'event_category': 'monitoring',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00',
             'image_url': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
             'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-122.359, 47.686]},
                         'properties': {'message': '', 'datetime': '2023-11-16T20:34:11.664952+00:00',
                                        'image': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                        'icon': {'iconUrl': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                                 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                                 'className': 'dot'}}}, 'is_collection': False, 'updates': [
                {'message': 'Changed State: new → active', 'time': '2023-11-16T20:34:15.671163+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'read'}, {'message': 'File Added: e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                                   'time': '2023-11-16T20:34:15.653320+00:00', 'text': '',
                                   'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi',
                                            'last_name': 'Service Account',
                                            'id': 'ddc888bb-d642-455a-a422-7393b4f172be',
                                            'content_type': 'accounts.user'}, 'type': 'add_eventfile'},
                {'message': 'Created', 'time': '2023-11-16T20:34:13.135632+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'add_event'}], 'patrols': []},
            {'id': '5cd12145-4490-4324-91ac-6865943fd26f', 'location': {'latitude': 47.686, 'longitude': -122.359},
             'time': '2023-11-16T14:32:15.109547-06:00', 'end_time': None, 'serial_number': 382, 'message': '',
             'provenance': '', 'event_type': 'trailguard_rep', 'priority': 200, 'priority_label': 'Amber',
             'attributes': {}, 'comment': None, 'title': 'Trailguard Trap', 'reported_by': None, 'state': 'active',
             'is_contained_in': [], 'sort_at': '2023-11-16T14:32:36.117190-06:00', 'patrol_segments': [],
             'geometry': None, 'updated_at': '2023-11-16T14:32:36.117190-06:00',
             'created_at': '2023-11-16T14:32:22.951909-06:00', 'icon_id': 'cameratrap_rep',
             'event_details': {'labels': ['adult', 'female'], 'species': 'coyote', 'animal_count': 1, 'updates': []},
             'files': [{'id': '6c258455-b3de-4613-bc00-cf6c5f4f1c0d', 'comment': '',
                        'created_at': '2023-11-16T14:32:36.098189-06:00',
                        'updated_at': '2023-11-16T14:32:36.098208-06:00', 'updates': [
                     {'message': 'File Added: 22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                      'time': '2023-11-16T20:32:36.109299+00:00', 'text': '',
                      'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                               'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                      'type': 'add_eventfile'}],
                        'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/',
                        'images': {
                            'original': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/original/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'icon': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/icon/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'thumbnail': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/thumbnail/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'large': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/large/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'xlarge': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/xlarge/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg'},
                        'filename': '22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg', 'file_type': 'image',
                        'icon_url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/icon/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg'}],
             'related_subjects': [], 'event_category': 'monitoring',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f',
             'image_url': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
             'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-122.359, 47.686]},
                         'properties': {'message': '', 'datetime': '2023-11-16T20:32:15.109547+00:00',
                                        'image': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                        'icon': {'iconUrl': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                                 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                                 'className': 'dot'}}}, 'is_collection': False, 'updates': [
                {'message': 'Changed State: new → active', 'time': '2023-11-16T20:32:36.128796+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'read'}, {'message': 'File Added: 22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                                   'time': '2023-11-16T20:32:36.109299+00:00', 'text': '',
                                   'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi',
                                            'last_name': 'Service Account',
                                            'id': 'ddc888bb-d642-455a-a422-7393b4f172be',
                                            'content_type': 'accounts.user'}, 'type': 'add_eventfile'},
                {'message': 'Created', 'time': '2023-11-16T20:32:23.000575+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'add_event'}], 'patrols': []}
        ]
    }


@pytest.fixture
def get_events_response_page_two():
    return {
        'count': 9,
        'next': None,
        'previous': 'https://gundi-er.pamdas.org/api/v1.0/activity/events?filter=%7B%22date_range%22%3A+%7B%22lower%22%3A+%222023-11-10T00%3A00%3A00-06%3A00%22%7D%7D&page_size=5&use_cursor=true',
        'results': [
            {'id': '81c5ea7b-0c95-41ad-9764-d42a6ba0aa00', 'location': {'latitude': 47.686, 'longitude': -122.359},
             'time': '2023-11-16T14:34:11.664952-06:00', 'end_time': None, 'serial_number': 383, 'message': '',
             'provenance': '', 'event_type': 'trailguard_rep', 'priority': 200, 'priority_label': 'Amber',
             'attributes': {}, 'comment': None, 'title': 'Trailguard Trap', 'reported_by': None, 'state': 'active',
             'is_contained_in': [], 'sort_at': '2023-11-16T14:34:15.659956-06:00', 'patrol_segments': [],
             'geometry': None, 'updated_at': '2023-11-16T14:34:15.659956-06:00',
             'created_at': '2023-11-16T14:34:13.123044-06:00', 'icon_id': 'cameratrap_rep',
             'event_details': {'labels': ['adult', 'female'], 'species': 'coyote', 'animal_count': 1, 'updates': []},
             'files': [{'id': 'dbe74373-84a4-4020-86f8-79a6c4a4408e', 'comment': '',
                        'created_at': '2023-11-16T14:34:15.646361-06:00',
                        'updated_at': '2023-11-16T14:34:15.646383-06:00', 'updates': [
                     {'message': 'File Added: e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                      'time': '2023-11-16T20:34:15.653320+00:00', 'text': '',
                      'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                               'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                      'type': 'add_eventfile'}],
                        'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/',
                        'images': {
                            'original': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/original/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'icon': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/icon/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'thumbnail': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/thumbnail/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'large': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/large/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                            'xlarge': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/xlarge/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg'},
                        'filename': 'e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg', 'file_type': 'image',
                        'icon_url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00/file/dbe74373-84a4-4020-86f8-79a6c4a4408e/icon/e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg'}],
             'related_subjects': [], 'event_category': 'monitoring',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/81c5ea7b-0c95-41ad-9764-d42a6ba0aa00',
             'image_url': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
             'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-122.359, 47.686]},
                         'properties': {'message': '', 'datetime': '2023-11-16T20:34:11.664952+00:00',
                                        'image': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                        'icon': {'iconUrl': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                                 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                                 'className': 'dot'}}}, 'is_collection': False, 'updates': [
                {'message': 'Changed State: new → active', 'time': '2023-11-16T20:34:15.671163+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'read'}, {'message': 'File Added: e3a9fbec-9a5d-4e66-b524-3ab44d8aaefb_coyote.jpg',
                                   'time': '2023-11-16T20:34:15.653320+00:00', 'text': '',
                                   'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi',
                                            'last_name': 'Service Account',
                                            'id': 'ddc888bb-d642-455a-a422-7393b4f172be',
                                            'content_type': 'accounts.user'}, 'type': 'add_eventfile'},
                {'message': 'Created', 'time': '2023-11-16T20:34:13.135632+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'add_event'}], 'patrols': []},
            {'id': '5cd12145-4490-4324-91ac-6865943fd26f', 'location': {'latitude': 47.686, 'longitude': -122.359},
             'time': '2023-11-16T14:32:15.109547-06:00', 'end_time': None, 'serial_number': 382, 'message': '',
             'provenance': '', 'event_type': 'trailguard_rep', 'priority': 200, 'priority_label': 'Amber',
             'attributes': {}, 'comment': None, 'title': 'Trailguard Trap', 'reported_by': None, 'state': 'active',
             'is_contained_in': [], 'sort_at': '2023-11-16T14:32:36.117190-06:00', 'patrol_segments': [],
             'geometry': None, 'updated_at': '2023-11-16T14:32:36.117190-06:00',
             'created_at': '2023-11-16T14:32:22.951909-06:00', 'icon_id': 'cameratrap_rep',
             'event_details': {'labels': ['adult', 'female'], 'species': 'coyote', 'animal_count': 1, 'updates': []},
             'files': [{'id': '6c258455-b3de-4613-bc00-cf6c5f4f1c0d', 'comment': '',
                        'created_at': '2023-11-16T14:32:36.098189-06:00',
                        'updated_at': '2023-11-16T14:32:36.098208-06:00', 'updates': [
                     {'message': 'File Added: 22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                      'time': '2023-11-16T20:32:36.109299+00:00', 'text': '',
                      'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                               'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                      'type': 'add_eventfile'}],
                        'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/',
                        'images': {
                            'original': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/original/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'icon': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/icon/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'thumbnail': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/thumbnail/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'large': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/large/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                            'xlarge': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/xlarge/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg'},
                        'filename': '22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg', 'file_type': 'image',
                        'icon_url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f/file/6c258455-b3de-4613-bc00-cf6c5f4f1c0d/icon/22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg'}],
             'related_subjects': [], 'event_category': 'monitoring',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/5cd12145-4490-4324-91ac-6865943fd26f',
             'image_url': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
             'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-122.359, 47.686]},
                         'properties': {'message': '', 'datetime': '2023-11-16T20:32:15.109547+00:00',
                                        'image': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                        'icon': {'iconUrl': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                                 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                                 'className': 'dot'}}}, 'is_collection': False, 'updates': [
                {'message': 'Changed State: new → active', 'time': '2023-11-16T20:32:36.128796+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'read'}, {'message': 'File Added: 22c2a51d-111c-4a1c-92dc-14df73c283e3_coyote.jpg',
                                   'time': '2023-11-16T20:32:36.109299+00:00', 'text': '',
                                   'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi',
                                            'last_name': 'Service Account',
                                            'id': 'ddc888bb-d642-455a-a422-7393b4f172be',
                                            'content_type': 'accounts.user'}, 'type': 'add_eventfile'},
                {'message': 'Created', 'time': '2023-11-16T20:32:23.000575+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'add_event'}], 'patrols': []},
            {'id': '30bae994-a57d-4113-a77e-9c96bf383919', 'location': None, 'time': '2023-11-16T14:14:34.954025-06:00',
             'end_time': None, 'serial_number': 381, 'message': '', 'provenance': '',
             'event_type': 'silence_source_provider_rep', 'priority': 0, 'priority_label': 'Gray', 'attributes': {},
             'comment': None, 'title': '265de4c0-07b8-4e30-b136-5d5a75ff5912 integration disrupted',
             'reported_by': None, 'state': 'new', 'is_contained_in': [], 'sort_at': '2023-11-16T14:14:34.955911-06:00',
             'patrol_segments': [], 'geometry': None, 'updated_at': '2023-11-16T14:14:34.955911-06:00',
             'created_at': '2023-11-16T14:14:34.956134-06:00', 'icon_id': 'silence_source_provider_rep',
             'event_details': {'report_time': '2023-11-16 20:14:34', 'silence_threshold': '00:00',
                               'last_device_reported_at': '2023-10-26 21:24:02', 'updates': []}, 'files': [],
             'related_subjects': [], 'event_category': 'analyzer_event',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/30bae994-a57d-4113-a77e-9c96bf383919',
             'image_url': 'https://gundi-er.pamdas.org/static/generic-gray.svg', 'geojson': None,
             'is_collection': False, 'updates': [{'message': 'Created', 'time': '2023-11-16T20:14:34.960679+00:00',
                                                  'user': {'first_name': '', 'last_name': '', 'username': ''},
                                                  'type': 'add_event'}], 'patrols': []},
            {'id': '97727f8d-d098-4c54-bbb9-d28987cd9d69', 'location': None, 'time': '2023-11-16T14:14:34.813692-06:00',
             'end_time': None, 'serial_number': 380, 'message': '', 'provenance': '',
             'event_type': 'silence_source_provider_rep', 'priority': 0, 'priority_label': 'Gray', 'attributes': {},
             'comment': None, 'title': 'A7a9e1ab-44e2-4585-8d4f-7770ca0b36e2 integration disrupted',
             'reported_by': None, 'state': 'new', 'is_contained_in': [], 'sort_at': '2023-11-16T14:14:34.815760-06:00',
             'patrol_segments': [], 'geometry': None, 'updated_at': '2023-11-16T14:14:34.815760-06:00',
             'created_at': '2023-11-16T14:14:34.816040-06:00', 'icon_id': 'silence_source_provider_rep',
             'event_details': {'report_time': '2023-11-16 20:14:34', 'silence_threshold': '00:01',
                               'last_device_reported_at': '2023-10-23 00:44:32', 'updates': []}, 'files': [],
             'related_subjects': [], 'event_category': 'analyzer_event',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/97727f8d-d098-4c54-bbb9-d28987cd9d69',
             'image_url': 'https://gundi-er.pamdas.org/static/generic-gray.svg', 'geojson': None,
             'is_collection': False, 'updates': [{'message': 'Created', 'time': '2023-11-16T20:14:34.828215+00:00',
                                                  'user': {'first_name': '', 'last_name': '', 'username': ''},
                                                  'type': 'add_event'}], 'patrols': []},
            {'id': 'dbb2dd78-e7ac-48d0-ba3f-007bb2cd1159', 'location': {'latitude': 47.686, 'longitude': -122.359},
             'time': '2023-11-16T14:12:34.751715-06:00', 'end_time': None, 'serial_number': 379, 'message': '',
             'provenance': '', 'event_type': 'trailguard_rep', 'priority': 200, 'priority_label': 'Amber',
             'attributes': {}, 'comment': None, 'title': 'Trailguard Trap', 'reported_by': None, 'state': 'active',
             'is_contained_in': [], 'sort_at': '2023-11-16T14:12:53.318186-06:00', 'patrol_segments': [],
             'geometry': None, 'updated_at': '2023-11-16T14:12:53.318186-06:00',
             'created_at': '2023-11-16T14:12:37.380087-06:00', 'icon_id': 'cameratrap_rep',
             'event_details': {'labels': ['adult', 'female'], 'species': 'coyote', 'numberAnimals': 1, 'updates': []},
             'files': [{'id': '7fb1ce8b-e18f-47dd-a5d1-8a978b19dda9', 'comment': '',
                        'created_at': '2023-11-16T14:12:53.305013-06:00',
                        'updated_at': '2023-11-16T14:12:53.305032-06:00', 'updates': [
                     {'message': 'File Added: 3b5bacfa-df78-47d2-872d-093e2c7e3b0c_coyote.jpg',
                      'time': '2023-11-16T20:12:53.311389+00:00', 'text': '',
                      'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                               'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                      'type': 'add_eventfile'}],
                        'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/dbb2dd78-e7ac-48d0-ba3f-007bb2cd1159/file/7fb1ce8b-e18f-47dd-a5d1-8a978b19dda9/',
                        'images': {
                            'original': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/dbb2dd78-e7ac-48d0-ba3f-007bb2cd1159/file/7fb1ce8b-e18f-47dd-a5d1-8a978b19dda9/original/3b5bacfa-df78-47d2-872d-093e2c7e3b0c_coyote.jpg',
                            'icon': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/dbb2dd78-e7ac-48d0-ba3f-007bb2cd1159/file/7fb1ce8b-e18f-47dd-a5d1-8a978b19dda9/icon/3b5bacfa-df78-47d2-872d-093e2c7e3b0c_coyote.jpg',
                            'thumbnail': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/dbb2dd78-e7ac-48d0-ba3f-007bb2cd1159/file/7fb1ce8b-e18f-47dd-a5d1-8a978b19dda9/thumbnail/3b5bacfa-df78-47d2-872d-093e2c7e3b0c_coyote.jpg',
                            'large': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/dbb2dd78-e7ac-48d0-ba3f-007bb2cd1159/file/7fb1ce8b-e18f-47dd-a5d1-8a978b19dda9/large/3b5bacfa-df78-47d2-872d-093e2c7e3b0c_coyote.jpg',
                            'xlarge': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/dbb2dd78-e7ac-48d0-ba3f-007bb2cd1159/file/7fb1ce8b-e18f-47dd-a5d1-8a978b19dda9/xlarge/3b5bacfa-df78-47d2-872d-093e2c7e3b0c_coyote.jpg'},
                        'filename': '3b5bacfa-df78-47d2-872d-093e2c7e3b0c_coyote.jpg', 'file_type': 'image',
                        'icon_url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/dbb2dd78-e7ac-48d0-ba3f-007bb2cd1159/file/7fb1ce8b-e18f-47dd-a5d1-8a978b19dda9/icon/3b5bacfa-df78-47d2-872d-093e2c7e3b0c_coyote.jpg'}],
             'related_subjects': [], 'event_category': 'monitoring',
             'url': 'https://gundi-er.pamdas.org/api/v1.0/activity/event/dbb2dd78-e7ac-48d0-ba3f-007bb2cd1159',
             'image_url': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
             'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-122.359, 47.686]},
                         'properties': {'message': '', 'datetime': '2023-11-16T20:12:34.751715+00:00',
                                        'image': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                        'icon': {'iconUrl': 'https://gundi-er.pamdas.org/static/cameratrap-black.svg',
                                                 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13],
                                                 'className': 'dot'}}}, 'is_collection': False, 'updates': [
                {'message': 'Changed State: new → active', 'time': '2023-11-16T20:12:53.330995+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'read'}, {'message': 'File Added: 3b5bacfa-df78-47d2-872d-093e2c7e3b0c_coyote.jpg',
                                   'time': '2023-11-16T20:12:53.311389+00:00', 'text': '',
                                   'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi',
                                            'last_name': 'Service Account',
                                            'id': 'ddc888bb-d642-455a-a422-7393b4f172be',
                                            'content_type': 'accounts.user'}, 'type': 'add_eventfile'},
                {'message': 'Created', 'time': '2023-11-16T20:12:37.389466+00:00',
                 'user': {'username': 'gundi_serviceaccout', 'first_name': 'Gundi', 'last_name': 'Service Account',
                          'id': 'ddc888bb-d642-455a-a422-7393b4f172be', 'content_type': 'accounts.user'},
                 'type': 'add_event'}], 'patrols': []}
        ]
    }


@pytest.fixture
def get_observations_response_single_page():
    return {
        'next': None,
        'previous': None,
        'results': [
            {'id': 'e083f777-eb6c-494c-9079-46f81b3300ca',
             'location': {'longitude': 36.7922397, 'latitude': -1.2932121}, 'recorded_at': '2023-11-10T06:01:06+00:00',
             'created_at': '2023-11-10T06:01:09+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': '13908ea9-f037-432a-841a-6b279dcefcbd',
             'location': {'longitude': 36.7921529, 'latitude': -1.2931406}, 'recorded_at': '2023-11-10T06:02:08+00:00',
             'created_at': '2023-11-10T06:02:10+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': 'e93e791f-12e2-46a2-84ec-6ecec7923879',
             'location': {'longitude': 36.7919254, 'latitude': -1.2931796}, 'recorded_at': '2023-11-10T06:02:30+00:00',
             'created_at': '2023-11-10T06:02:31+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': 'be1b73ab-0db1-45d3-a349-619fa7968116',
             'location': {'longitude': 36.7917022, 'latitude': -1.2931531}, 'recorded_at': '2023-11-10T06:02:50+00:00',
             'created_at': '2023-11-10T06:02:51+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': 'b65d8258-e765-4bbf-a7fa-075494fb4678',
             'location': {'longitude': 36.7914986, 'latitude': -1.2930534}, 'recorded_at': '2023-11-10T06:03:13+00:00',
             'created_at': '2023-11-10T06:03:14+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}}
        ]
    }


@pytest.fixture
def get_observations_response_page_one():
    return {
        'next': 'https://gundi-er.pamdas.org/api/v1.0/observations?cursor=cD0yMDIzLTExLTEwKzA2JTNBMDMlM0ExMy42NDAwMDAlMkIwMCUzQTAw&filter=null&include_details=true&page_size=5&since=2023-11-10T00%3A00%3A00-06%3A00&use_cursor=true',
        'previous': None,
        'results': [
            {'id': 'e083f777-eb6c-494c-9079-46f81b3300ca',
             'location': {'longitude': 36.7922397, 'latitude': -1.2932121}, 'recorded_at': '2023-11-10T06:01:06+00:00',
             'created_at': '2023-11-10T06:01:09+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': '13908ea9-f037-432a-841a-6b279dcefcbd',
             'location': {'longitude': 36.7921529, 'latitude': -1.2931406}, 'recorded_at': '2023-11-10T06:02:08+00:00',
             'created_at': '2023-11-10T06:02:10+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': 'e93e791f-12e2-46a2-84ec-6ecec7923879',
             'location': {'longitude': 36.7919254, 'latitude': -1.2931796}, 'recorded_at': '2023-11-10T06:02:30+00:00',
             'created_at': '2023-11-10T06:02:31+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': 'be1b73ab-0db1-45d3-a349-619fa7968116',
             'location': {'longitude': 36.7917022, 'latitude': -1.2931531}, 'recorded_at': '2023-11-10T06:02:50+00:00',
             'created_at': '2023-11-10T06:02:51+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': 'b65d8258-e765-4bbf-a7fa-075494fb4678',
             'location': {'longitude': 36.7914986, 'latitude': -1.2930534}, 'recorded_at': '2023-11-10T06:03:13+00:00',
             'created_at': '2023-11-10T06:03:14+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}}
        ]
    }


@pytest.fixture
def get_observations_response_page_two():
    return {
        'next': None,
        'previous': 'https://gundi-er.pamdas.org/api/v1.0/observations?cursor=cj0xJnA9MjAyMy0xMS0xMCswNiUzQTAzJTNBMzMuMTg3MDAwJTJCMDAlM0EwMA%3D%3D&filter=null&include_details=true&page_size=5&since=2023-11-10T00%3A00%3A00-06%3A00&use_cursor=true',
        'results': [
            {'id': '225984cc-b195-4853-b366-1e53f4e772e5',
             'location': {'longitude': 36.7912758, 'latitude': -1.2930861}, 'recorded_at': '2023-11-10T06:03:33+00:00',
             'created_at': '2023-11-10T06:03:34+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': '2c166c41-df53-4520-a42c-2aa7a8f8b6e3',
             'location': {'longitude': 36.7910665, 'latitude': -1.2929826}, 'recorded_at': '2023-11-10T06:03:54+00:00',
             'created_at': '2023-11-10T06:03:55+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': '42017465-ae88-400e-8afe-d6ff5051b8ac',
             'location': {'longitude': 36.7908843, 'latitude': -1.2928466}, 'recorded_at': '2023-11-10T06:04:18+00:00',
             'created_at': '2023-11-10T06:04:19+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': '8c6a5e1d-bf78-42c2-b22d-dd443d281cc1', 'location': {'longitude': 36.790857, 'latitude': -1.2926173},
             'recorded_at': '2023-11-10T06:04:38+00:00', 'created_at': '2023-11-10T06:04:39+00:00',
             'exclusion_flags': 0, 'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}},
            {'id': 'a61b38cc-bcac-4db1-96c4-ee277175977f',
             'location': {'longitude': 36.7908162, 'latitude': -1.2923946}, 'recorded_at': '2023-11-10T06:04:57+00:00',
             'created_at': '2023-11-10T06:04:58+00:00', 'exclusion_flags': 0,
             'source': '192b457f-fa25-4674-ae3e-8fae8d775d61', 'observation_details': {}}
        ]
    }
