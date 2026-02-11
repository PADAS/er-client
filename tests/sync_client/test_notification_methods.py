import json
from unittest.mock import MagicMock, patch

import pytest

from erclient import (ERClientNotFound, ERClientPermissionDenied)


NM_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"


def _mock_response(status_code, json_data=None, ok=None, text=None):
    """Create a mock requests.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if ok is None:
        mock_resp.ok = 200 <= status_code < 300
    else:
        mock_resp.ok = ok
    if json_data is not None:
        mock_resp.text = json.dumps(json_data)
        mock_resp.json.return_value = json_data
    elif text is not None:
        mock_resp.text = text
    else:
        mock_resp.text = "{}"
    return mock_resp


@pytest.fixture
def nm_list_response():
    return {
        "data": {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": NM_ID,
                    "title": "Email Notification",
                    "contact": {"method": "email", "value": "test@example.com"},
                    "is_active": True,
                    "owner": {"username": "testuser"},
                },
                {
                    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "title": "SMS Notification",
                    "contact": {"method": "sms", "value": "+15551234567"},
                    "is_active": True,
                    "owner": {"username": "testuser"},
                },
            ],
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def nm_detail_response():
    return {
        "data": {
            "id": NM_ID,
            "title": "Email Notification",
            "contact": {"method": "email", "value": "test@example.com"},
            "is_active": True,
            "owner": {"username": "testuser"},
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def nm_created_response():
    return {
        "data": {
            "id": NM_ID,
            "title": "New Email Notification",
            "contact": {"method": "email", "value": "new@example.com"},
            "is_active": True,
            "owner": {"username": "testuser"},
        },
        "status": {"code": 201, "message": "Created"},
    }


# ---- get_notification_methods tests ----

class TestGetNotificationMethods:
    def test_get_notification_methods_success(self, er_client, nm_list_response):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, nm_list_response)
            result = er_client.get_notification_methods()
            assert result == nm_list_response["data"]
            assert mock_get.called
            url = mock_get.call_args[0][0]
            assert "activity/notificationmethods" in url

    def test_get_notification_methods_empty(self, er_client):
        empty_response = {
            "data": {"count": 0, "next": None, "previous": None, "results": []},
            "status": {"code": 200, "message": "OK"},
        }
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, empty_response)
            result = er_client.get_notification_methods()
            assert result == empty_response["data"]

    def test_get_notification_methods_not_found(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.get_notification_methods()

    def test_get_notification_methods_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_notification_methods()


# ---- get_notification_method tests ----

class TestGetNotificationMethod:
    def test_get_notification_method_success(self, er_client, nm_detail_response):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, nm_detail_response)
            result = er_client.get_notification_method(NM_ID)
            assert result == nm_detail_response["data"]
            assert mock_get.called
            url = mock_get.call_args[0][0]
            assert f"activity/notificationmethod/{NM_ID}" in url

    def test_get_notification_method_not_found(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.get_notification_method("nonexistent-id")

    def test_get_notification_method_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_notification_method(NM_ID)


# ---- post_notification_method tests ----

class TestPostNotificationMethod:
    def test_post_notification_method_success(self, er_client, nm_created_response):
        with patch.object(er_client._http_session, 'post') as mock_post:
            mock_post.return_value = _mock_response(201, nm_created_response)
            result = er_client.post_notification_method({
                "title": "New Email Notification",
                "contact": {"method": "email", "value": "new@example.com"},
            })
            assert result == nm_created_response["data"]
            assert mock_post.called

    def test_post_notification_method_not_found(self, er_client):
        with patch.object(er_client._http_session, 'post') as mock_post:
            mock_post.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.post_notification_method({"title": "test"})

    def test_post_notification_method_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'post') as mock_post:
            mock_post.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.post_notification_method({"title": "test"})


# ---- patch_notification_method tests ----

class TestPatchNotificationMethod:
    def test_patch_notification_method_success(self, er_client, nm_detail_response):
        with patch.object(er_client._http_session, 'patch') as mock_patch:
            mock_patch.return_value = _mock_response(200, nm_detail_response)
            result = er_client.patch_notification_method(NM_ID, {"is_active": False})
            assert result == nm_detail_response["data"]
            assert mock_patch.called

    def test_patch_notification_method_not_found(self, er_client):
        with patch.object(er_client._http_session, 'patch') as mock_patch:
            mock_patch.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.patch_notification_method(NM_ID, {"is_active": False})

    def test_patch_notification_method_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'patch') as mock_patch:
            mock_patch.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.patch_notification_method(NM_ID, {"is_active": False})


# ---- delete_notification_method tests ----

class TestDeleteNotificationMethod:
    def test_delete_notification_method_success(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(204)
            result = er_client.delete_notification_method(NM_ID)
            assert result is True
            assert mock_delete.called
            url = mock_delete.call_args[0][0]
            assert f"activity/notificationmethod/{NM_ID}/" in url

    def test_delete_notification_method_not_found(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.delete_notification_method(NM_ID)

    def test_delete_notification_method_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.delete_notification_method(NM_ID)
