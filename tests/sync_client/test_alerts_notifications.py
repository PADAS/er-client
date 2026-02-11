import json
from unittest.mock import MagicMock, patch

import pytest

from erclient.er_errors import (
    ERClientException,
    ERClientNotFound,
    ERClientPermissionDenied,
)

ALERT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
NOTIF_ID = "f0e1d2c3-b4a5-6789-abcd-0123456789ab"


def _ok_response(data, status_code=200):
    resp = MagicMock()
    resp.ok = True
    resp.status_code = status_code
    resp.text = json.dumps({"data": data})
    resp.url = "https://fake-site.erdomain.org/api/v1.0/test"
    return resp


def _error_response(status_code, detail="error"):
    resp = MagicMock()
    resp.ok = False
    resp.status_code = status_code
    resp.text = json.dumps({"status": {"code": status_code, "detail": detail}})
    resp.url = "https://fake-site.erdomain.org/api/v1.0/test"
    return resp


def _delete_ok():
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 204
    resp.text = ""
    return resp


# -- Alert rules: GET list ---------------------------------------------------

def test_get_alerts_success(er_client):
    data = [{"id": ALERT_ID, "title": "Geofence breach"}]
    with patch.object(
        er_client._http_session, "get", return_value=_ok_response(data)
    ) as mock_get:
        result = er_client.get_alerts()
    assert result == data
    url = mock_get.call_args[0][0]
    assert url.endswith("activity/alerts")


def test_get_alerts_forbidden(er_client):
    with patch.object(
        er_client._http_session, "get",
        return_value=_error_response(403, "Forbidden"),
    ):
        with pytest.raises(ERClientPermissionDenied):
            er_client.get_alerts()


# -- Alert rules: GET single -------------------------------------------------

def test_get_alert_success(er_client):
    data = {"id": ALERT_ID, "title": "Geofence breach"}
    with patch.object(
        er_client._http_session, "get", return_value=_ok_response(data)
    ) as mock_get:
        result = er_client.get_alert(ALERT_ID)
    assert result == data
    url = mock_get.call_args[0][0]
    assert f"activity/alert/{ALERT_ID}" in url


def test_get_alert_not_found(er_client):
    with patch.object(
        er_client._http_session, "get",
        return_value=_error_response(404),
    ):
        with pytest.raises(ERClientNotFound):
            er_client.get_alert(ALERT_ID)


# -- Alert rules: POST -------------------------------------------------------

def test_post_alert_success(er_client):
    payload = {"title": "New alert", "conditions": []}
    data = {"id": ALERT_ID, **payload}
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 201
    resp.json.return_value = {"data": data, "status": {"code": 201}}
    resp.text = json.dumps({"data": data, "status": {"code": 201}})
    with patch.object(
        er_client._http_session, "post", return_value=resp
    ) as mock_post:
        result = er_client.post_alert(payload)
    assert result == data


# -- Alert rules: PATCH ------------------------------------------------------

def test_patch_alert_success(er_client):
    payload = {"title": "Updated alert"}
    data = {"id": ALERT_ID, **payload}
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json.return_value = {"data": data}
    resp.text = json.dumps({"data": data})
    with patch.object(er_client._http_session, "patch", return_value=resp):
        result = er_client.patch_alert(ALERT_ID, payload)
    assert result == data


# -- Alert rules: DELETE -----------------------------------------------------

def test_delete_alert_success(er_client):
    with patch.object(
        er_client._http_session, "delete", return_value=_delete_ok()
    ):
        result = er_client.delete_alert(ALERT_ID)
    assert result is True


def test_delete_alert_not_found(er_client):
    with patch.object(
        er_client._http_session, "delete",
        return_value=_error_response(404),
    ):
        with pytest.raises(ERClientNotFound):
            er_client.delete_alert(ALERT_ID)


# -- Alert conditions --------------------------------------------------------

def test_get_alert_conditions_success(er_client):
    data = [{"type": "geofence"}, {"type": "proximity"}]
    with patch.object(
        er_client._http_session, "get", return_value=_ok_response(data)
    ) as mock_get:
        result = er_client.get_alert_conditions()
    assert result == data
    url = mock_get.call_args[0][0]
    assert url.endswith("activity/alerts/conditions")


# -- Notification methods: GET list ------------------------------------------

def test_get_notification_methods_success(er_client):
    data = [{"id": NOTIF_ID, "method_type": "email"}]
    with patch.object(
        er_client._http_session, "get", return_value=_ok_response(data)
    ) as mock_get:
        result = er_client.get_notification_methods()
    assert result == data
    url = mock_get.call_args[0][0]
    assert url.endswith("activity/notificationmethods")


# -- Notification methods: GET single ----------------------------------------

def test_get_notification_method_success(er_client):
    data = {"id": NOTIF_ID, "method_type": "email"}
    with patch.object(
        er_client._http_session, "get", return_value=_ok_response(data)
    ) as mock_get:
        result = er_client.get_notification_method(NOTIF_ID)
    assert result == data
    url = mock_get.call_args[0][0]
    assert f"activity/notificationmethod/{NOTIF_ID}" in url


def test_get_notification_method_not_found(er_client):
    with patch.object(
        er_client._http_session, "get",
        return_value=_error_response(404),
    ):
        with pytest.raises(ERClientNotFound):
            er_client.get_notification_method(NOTIF_ID)


# -- Notification methods: POST ----------------------------------------------

def test_post_notification_method_success(er_client):
    payload = {"method_type": "email", "value": "test@example.com"}
    data = {"id": NOTIF_ID, **payload}
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 201
    resp.json.return_value = {"data": data}
    resp.text = json.dumps({"data": data})
    with patch.object(er_client._http_session, "post", return_value=resp):
        result = er_client.post_notification_method(payload)
    assert result == data


# -- Notification methods: PATCH ---------------------------------------------

def test_patch_notification_method_success(er_client):
    payload = {"value": "updated@example.com"}
    data = {"id": NOTIF_ID, **payload}
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json.return_value = {"data": data}
    resp.text = json.dumps({"data": data})
    with patch.object(er_client._http_session, "patch", return_value=resp):
        result = er_client.patch_notification_method(NOTIF_ID, payload)
    assert result == data


# -- Notification methods: DELETE --------------------------------------------

def test_delete_notification_method_success(er_client):
    with patch.object(
        er_client._http_session, "delete", return_value=_delete_ok()
    ):
        result = er_client.delete_notification_method(NOTIF_ID)
    assert result is True


def test_delete_notification_method_not_found(er_client):
    with patch.object(
        er_client._http_session, "delete",
        return_value=_error_response(404),
    ):
        with pytest.raises(ERClientNotFound):
            er_client.delete_notification_method(NOTIF_ID)
