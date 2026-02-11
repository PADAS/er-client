import json
from unittest.mock import MagicMock

import pytest

from erclient.client import ERClient
from erclient import ERClientNotFound, ERClientPermissionDenied


EVENTPROVIDER_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
EVENTSOURCE_ID = "f0e1d2c3-b4a5-6789-0fed-cba987654321"


@pytest.fixture
def eventprovider_payload():
    return {
        "display": "My Test Provider",
        "owner": {"id": "user-id-123"},
    }


@pytest.fixture
def eventprovider_created_response():
    return {
        "data": {
            "id": EVENTPROVIDER_ID,
            "display": "My Test Provider",
            "is_active": True,
            "owner": {"id": "user-id-123"},
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def eventproviders_list_response():
    return {
        "data": [
            {
                "id": EVENTPROVIDER_ID,
                "display": "My Test Provider",
                "is_active": True,
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "display": "Another Provider",
                "is_active": False,
            },
        ],
    }


@pytest.fixture
def eventprovider_detail_response():
    return {
        "data": {
            "id": EVENTPROVIDER_ID,
            "display": "My Test Provider",
            "is_active": True,
        },
    }


@pytest.fixture
def eventprovider_patched_response():
    return {
        "data": {
            "id": EVENTPROVIDER_ID,
            "display": "Updated Provider Name",
            "is_active": True,
        },
    }


@pytest.fixture
def eventsource_payload():
    return {
        "display": "Test Event Source",
    }


@pytest.fixture
def eventsource_created_response():
    return {
        "data": {
            "id": EVENTSOURCE_ID,
            "display": "Test Event Source",
            "eventprovider": EVENTPROVIDER_ID,
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def eventsources_list_response():
    return {
        "data": [
            {
                "id": EVENTSOURCE_ID,
                "display": "Test Event Source",
                "eventprovider": EVENTPROVIDER_ID,
            },
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "display": "Second Source",
                "eventprovider": EVENTPROVIDER_ID,
            },
        ],
    }


@pytest.fixture
def eventsource_detail_response():
    return {
        "data": {
            "id": EVENTSOURCE_ID,
            "display": "Test Event Source",
            "eventprovider": EVENTPROVIDER_ID,
        },
    }


@pytest.fixture
def eventsource_patched_response():
    return {
        "data": {
            "id": EVENTSOURCE_ID,
            "display": "Renamed Source",
            "eventprovider": EVENTPROVIDER_ID,
        },
    }


def _mock_response(status_code=200, json_data=None):
    """Helper to create a mock response object."""
    response = MagicMock()
    response.ok = 200 <= status_code < 400
    response.status_code = status_code
    response.text = json.dumps(json_data) if json_data else ""
    response.json.return_value = json_data
    response.url = "https://fake-site.erdomain.org/api/v1.0/test"
    return response


# -- Sync Event Provider POST Tests --


def test_post_eventprovider_success(er_client, eventprovider_payload, eventprovider_created_response):
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(201, eventprovider_created_response)
    )
    result = er_client.post_eventprovider(eventprovider_payload)
    er_client._http_session.post.assert_called_once()
    assert result == eventprovider_created_response["data"]


def test_post_eventprovider_forbidden(er_client, eventprovider_payload):
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(403, {
            "status": {"detail": "You do not have permission to perform this action."}
        })
    )
    with pytest.raises(ERClientPermissionDenied):
        er_client.post_eventprovider(eventprovider_payload)


# -- Sync Event Provider GET List Tests --


def test_get_eventproviders_success(er_client, eventproviders_list_response):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, eventproviders_list_response)
    )
    result = er_client.get_eventproviders()
    er_client._http_session.get.assert_called_once()
    assert result == eventproviders_list_response["data"]
    assert len(result) == 2


# -- Sync Event Provider GET Detail Tests --


def test_get_eventprovider_success(er_client, eventprovider_detail_response):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, eventprovider_detail_response)
    )
    result = er_client.get_eventprovider(EVENTPROVIDER_ID)
    er_client._http_session.get.assert_called_once()
    assert result == eventprovider_detail_response["data"]


def test_get_eventprovider_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {
            "status": {"code": 404, "detail": "Not found"}
        })
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_eventprovider(EVENTPROVIDER_ID)


# -- Sync Event Provider PATCH Tests --


def test_patch_eventprovider_success(er_client, eventprovider_patched_response):
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(200, eventprovider_patched_response)
    )
    result = er_client.patch_eventprovider(
        EVENTPROVIDER_ID, {"display": "Updated Provider Name"}
    )
    er_client._http_session.patch.assert_called_once()
    assert result == eventprovider_patched_response["data"]
    assert result["display"] == "Updated Provider Name"


def test_patch_eventprovider_not_found(er_client):
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(404, {
            "status": {"code": 404, "detail": "Not found"}
        })
    )
    with pytest.raises(ERClientNotFound):
        er_client.patch_eventprovider(EVENTPROVIDER_ID, {"display": "X"})


# -- Sync Event Source POST Tests --


def test_post_eventsource_success(er_client, eventsource_payload, eventsource_created_response):
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(201, eventsource_created_response)
    )
    result = er_client.post_eventsource(EVENTPROVIDER_ID, eventsource_payload)
    er_client._http_session.post.assert_called_once()
    assert result == eventsource_created_response["data"]


def test_post_eventsource_not_found(er_client, eventsource_payload):
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(404, {
            "status": {"code": 404, "detail": "Provider not found"}
        })
    )
    with pytest.raises(ERClientNotFound):
        er_client.post_eventsource(EVENTPROVIDER_ID, eventsource_payload)


# -- Sync Event Source GET List Tests --


def test_get_eventsources_success(er_client, eventsources_list_response):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, eventsources_list_response)
    )
    result = er_client.get_eventsources(EVENTPROVIDER_ID)
    er_client._http_session.get.assert_called_once()
    assert result == eventsources_list_response["data"]
    assert len(result) == 2


# -- Sync Event Source GET Detail Tests --


def test_get_eventsource_success(er_client, eventsource_detail_response):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, eventsource_detail_response)
    )
    result = er_client.get_eventsource(EVENTSOURCE_ID)
    er_client._http_session.get.assert_called_once()
    assert result == eventsource_detail_response["data"]


def test_get_eventsource_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {
            "status": {"code": 404, "detail": "Not found"}
        })
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_eventsource(EVENTSOURCE_ID)


# -- Sync Event Source PATCH Tests --


def test_patch_eventsource_success(er_client, eventsource_patched_response):
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(200, eventsource_patched_response)
    )
    result = er_client.patch_eventsource(
        EVENTSOURCE_ID, {"display": "Renamed Source"}
    )
    er_client._http_session.patch.assert_called_once()
    assert result == eventsource_patched_response["data"]
    assert result["display"] == "Renamed Source"


def test_patch_eventsource_not_found(er_client):
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(404, {
            "status": {"code": 404, "detail": "Not found"}
        })
    )
    with pytest.raises(ERClientNotFound):
        er_client.patch_eventsource(EVENTSOURCE_ID, {"display": "X"})
