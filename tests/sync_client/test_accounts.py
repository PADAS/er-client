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
    response.url = "https://fake-site.erdomain.org/api/v1.0/test"
    return response


# -- get_users --

def test_get_users(er_client):
    expected = [{"id": "user-001", "username": "ranger01"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_users()
    er_client._http_session.get.assert_called_once()
    assert result == expected


# -- get_user --

def test_get_user(er_client):
    expected = {"id": "user-001", "username": "ranger01", "first_name": "Jane"}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_user("user-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_user_me(er_client):
    expected = {"id": "user-001", "username": "ranger01"}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_user("me")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_user_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_user("nonexistent")


# -- patch_user --

def test_patch_user(er_client):
    updated = {"data": {"id": "user-001", "first_name": "Updated"}, "status": {"code": 200}}
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(200, updated)
    )
    result = er_client.patch_user("user-001", {"first_name": "Updated"})
    er_client._http_session.patch.assert_called_once()
    assert result["first_name"] == "Updated"


def test_patch_user_forbidden(er_client):
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(403, {"status": {"detail": "Forbidden"}})
    )
    with pytest.raises(ERClientPermissionDenied):
        er_client.patch_user("user-001", {"first_name": "x"})


def test_patch_user_not_found(er_client):
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.patch_user("nonexistent", {"first_name": "x"})


# -- get_user_profiles --

def test_get_user_profiles(er_client):
    expected = [{"id": "prof-001", "role": "ranger"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_user_profiles("user-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_user_profiles_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_user_profiles("nonexistent")


# -- get_eula --

def test_get_eula(er_client):
    expected = {"id": "eula-001", "version": "2.0", "active": True}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_eula()
    er_client._http_session.get.assert_called_once()
    assert result == expected


# -- accept_eula --

def test_accept_eula(er_client):
    accept_resp = {"data": {"accepted": True, "eula": "eula-001"}, "status": {"code": 201}}
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(201, accept_resp)
    )
    result = er_client.accept_eula()
    er_client._http_session.post.assert_called_once()
    assert result["accepted"] is True


def test_accept_eula_forbidden(er_client):
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(403, {"status": {"detail": "Forbidden"}})
    )
    with pytest.raises(ERClientPermissionDenied):
        er_client.accept_eula()
