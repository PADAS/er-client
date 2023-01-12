from pathlib import Path

import pytest

from erclient.client import AsyncERClient


@pytest.fixture
def er_server_info():
    return {
        'service_root': 'https://fake-site.erdomain.org/api/v1.0',
        'username': 'test',
        'password': 'test',
        'token': '1110c87681cd1d12ad07c2d0f57d15d6079ae5d8',
        'token_url': 'https://fake-auth.erdomain.org/oauth2/token',
        'client_id': 'das_web_client',
        'provider_key': 'testintegration'
    }


@pytest.fixture
def er_client(er_server_info):
    return AsyncERClient(**er_server_info)


# ToDo: Use factories?
@pytest.fixture
def position():
    return {
        'manufacturer_id': '018910980',
        'source_type': 'tracking-device',
        'subject_name': 'Test Truck',
        'recorded_at': '2023-01-11 19:41:00+02:00',
        'location': {'lon': 35.43903, 'lat': -1.59083},
        'additional': {'voltage': '7.4', 'fuel_level': 71, 'speed': '41 kph'}
    }


@pytest.fixture
def report():
    return {
        'title': 'Rainfall',
        'event_type': 'rainfall_rep',
        'event_details': {'amount_mm': 6, 'height_m': 3},
        'time': '2023-01-11 17:28:02-03:00',
        'location': {'longitude': -55.784992, 'latitude': 20.806785}
    }


@pytest.fixture
def camera_trap_payload():
    return {
        'file': 'cameratrap.jpg',
        'camera_name': 'Test camera',
        'camera_description': 'Camera Trap',
        'time': '2023-01-11 17:05:00-03:00',
        'location': '{"longitude": -122.5, "latitude": 48.65}'
    }


@pytest.fixture
def camera_trap_conflict_response():
    return {}


@pytest.fixture
def position_created_response():
    return {
        'data': {},
        'status': {'code': 201, 'message': 'Created'}
    }


@pytest.fixture
def bad_request_response():
    # ToDo. Get some real examples
    return {
        'data': 'invalid device id',
        'status': {'code': 400, 'message': 'Bad Request'}
    }


@pytest.fixture
def forbidden_response():
    # ToDo. Get some real examples
    return {
        'status': {'code': 403, 'detail': 'you do not have enough permissions'}
    }


@pytest.fixture
def not_found_response():
    # ToDo. Get some real examples
    return {
        'status': {'code': 404, 'detail': 'a provider with the given key does not exist'}
    }


@pytest.fixture
def report_created_response():
    return {
        'data': {
            'id': '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f',
            'location': {'latitude': 20.806785, 'longitude': -55.784995},
            'time': '2023-01-11T12:30:02-08:00',
            'end_time': None,
            'serial_number': 76819,
            'message': '', 'provenance': '',
            'event_type': 'rainfall_rep',
            'priority': 0,
            'priority_label': 'Gray',
            'attributes': {},
            'comment': None,
            'title': 'Rainfall',
            'notes': [],
            'reported_by': None,
            'state': 'new',
            'event_details': {'height_m': 5, 'amount_mm': 8},
            'contains': [],
            'is_linked_to': [],
            'is_contained_in': [],
            'files': [],
            'related_subjects': [],
            'sort_at': '2023-01-12T04:18:25.573925-08:00',
            'patrol_segments': [], 'geometry': None,
            'updated_at': '2023-01-12T04:18:25.573925-08:00',
            'created_at': '2023-01-12T04:18:25.574854-08:00',
            'icon_id': 'rainfall_rep',
            'event_category': 'monitoring',
            'url': 'https://fake-site.erdomain.org/api/v1.0/activity/event/9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f',
            'image_url': 'https://fake-site.erdomain.org/static/sprite-src/rainfall_rep.svg',
            'geojson': {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-55.784995, 20.806785]}, 'properties': {'message': '', 'datetime': '2023-01-11T20:30:02+00:00', 'image': 'https://fake-site.erdomain.org/static/sprite-src/rainfall_rep.svg', 'icon': {'iconUrl': 'https://fake-site.erdomain.org/static/sprite-src/rainfall_rep.svg', 'iconSize': [25, 25], 'iconAncor': [12, 12], 'popupAncor': [0, -13], 'className': 'dot'}}},
            'is_collection': False,
            'updates': [{'message': 'Added', 'time': '2023-01-12T12:18:25.585183+00:00', 'user': {'username': 'gundi_serviceaccount', 'first_name': 'Gundi', 'last_name': 'Service Account', 'id': 'c925e69e-51cf-43d0-b659-2000ae023664', 'content_type': 'accounts.user'}, 'type': 'add_event'}],
            'patrols': []
        },
        'status': {'code': 201, 'message': 'Created'}
    }


@pytest.fixture
def camera_trap_report_created_response():
    return {
        'data': {'group_id': 'f14f241f-ad51-4c06-85ca-0aca8c5965a0'},
        'status': {'code': 201, 'message': 'Created'}
    }


@pytest.fixture
def camera_trap_file():
    file_path = Path(__file__).resolve().parent.parent.joinpath(
        'images/cameratrap.jpg')
    # ToDo: open the files using async (aiofiles)
    return open(file_path, 'rb')
