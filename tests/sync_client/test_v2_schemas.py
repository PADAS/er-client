import json
from unittest.mock import MagicMock

import pytest

from erclient import ERClientNotFound, ERClientPermissionDenied


def _mock_response(status_code=200, json_data=None):
    """Helper to create a mock response object."""
    response = MagicMock()
    response.ok = 200 <= status_code < 400
    response.status_code = status_code
    response.text = json.dumps(json_data) if json_data else ""
    response.json.return_value = json_data
    response.url = "https://fake-site.erdomain.org/api/v2.0/schemas/test"
    return response


@pytest.fixture
def sample_schema():
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Users",
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "username": {"type": "string"},
            "email": {"type": "string", "format": "email"},
        },
        "required": ["username"],
    }


# -- service_root_v2 property --


def test_service_root_v2(er_client):
    """Verify the v2 root is derived correctly."""
    assert er_client.service_root_v2 == "https://fake-site.erdomain.org/api/v2.0"


# -- Generic get_schema --


def test_get_schema_generic(er_client, sample_schema):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": sample_schema})
    )
    result = er_client.get_schema("users")
    er_client._http_session.get.assert_called_once()
    # Verify the URL used the v2 root
    call_args = er_client._http_session.get.call_args
    assert "/api/v2.0/schemas/users.json" in call_args[0][0]
    assert result == sample_schema


def test_get_schema_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_schema("nonexistent")


def test_get_schema_forbidden(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(403, {"status": {"detail": "Forbidden"}})
    )
    with pytest.raises(ERClientPermissionDenied):
        er_client.get_schema("users")


# -- Individual schema convenience methods --


def test_get_users_schema(er_client, sample_schema):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": sample_schema})
    )
    result = er_client.get_users_schema()
    call_url = er_client._http_session.get.call_args[0][0]
    assert "/api/v2.0/schemas/users.json" in call_url
    assert result == sample_schema


def test_get_sources_schema(er_client, sample_schema):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": sample_schema})
    )
    result = er_client.get_sources_schema()
    call_url = er_client._http_session.get.call_args[0][0]
    assert "/api/v2.0/schemas/sources.json" in call_url
    assert result == sample_schema


def test_get_subjects_schema(er_client, sample_schema):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": sample_schema})
    )
    result = er_client.get_subjects_schema()
    call_url = er_client._http_session.get.call_args[0][0]
    assert "/api/v2.0/schemas/subjects.json" in call_url
    assert result == sample_schema


def test_get_choices_schema(er_client, sample_schema):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": sample_schema})
    )
    result = er_client.get_choices_schema()
    call_url = er_client._http_session.get.call_args[0][0]
    assert "/api/v2.0/schemas/choices.json" in call_url
    assert result == sample_schema


def test_get_spatial_features_schema(er_client, sample_schema):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": sample_schema})
    )
    result = er_client.get_spatial_features_schema()
    call_url = er_client._http_session.get.call_args[0][0]
    assert "/api/v2.0/schemas/spatial_features.json" in call_url
    assert result == sample_schema


def test_get_event_types_schema(er_client, sample_schema):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": sample_schema})
    )
    result = er_client.get_event_types_schema()
    call_url = er_client._http_session.get.call_args[0][0]
    assert "/api/v2.0/schemas/event_types.json" in call_url
    assert result == sample_schema
