import json
from unittest.mock import MagicMock, patch

import pytest

from erclient import (ERClientNotFound, ERClientPermissionDenied)


ALERT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


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
def alert_list_response():
    return {
        "data": [
            {
                "id": ALERT_ID,
                "title": "Poaching Alert",
                "is_active": True,
                "ordernum": 0,
                "conditions": {"all": [{"name": "state_is_new", "value": True}]},
                "schedule": {"periods": {}},
                "reportTypes": ["poaching_rep"],
                "notification_method_ids": [],
            }
        ],
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def alert_detail_response():
    return {
        "data": {
            "id": ALERT_ID,
            "title": "Poaching Alert",
            "is_active": True,
            "ordernum": 0,
            "conditions": {"all": [{"name": "state_is_new", "value": True}]},
            "schedule": {"periods": {}},
            "reportTypes": ["poaching_rep"],
            "notification_method_ids": [],
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def alert_created_response():
    return {
        "data": {
            "id": ALERT_ID,
            "title": "New Alert",
            "is_active": True,
            "ordernum": 0,
            "conditions": {},
            "schedule": {"periods": {}},
            "reportTypes": ["fire_rep"],
            "notification_method_ids": [],
        },
        "status": {"code": 201, "message": "Created"},
    }


# ---- get_alerts tests ----

class TestGetAlerts:
    def test_get_alerts_success(self, er_client, alert_list_response):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, alert_list_response)
            result = er_client.get_alerts()
            assert result == alert_list_response["data"]
            assert mock_get.called
            url = mock_get.call_args[0][0]
            assert "activity/alerts" in url

    def test_get_alerts_empty(self, er_client):
        empty_response = {"data": [], "status": {"code": 200, "message": "OK"}}
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, empty_response)
            result = er_client.get_alerts()
            assert result == []

    def test_get_alerts_not_found(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.get_alerts()

    def test_get_alerts_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_alerts()


# ---- get_alert tests ----

class TestGetAlert:
    def test_get_alert_success(self, er_client, alert_detail_response):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, alert_detail_response)
            result = er_client.get_alert(ALERT_ID)
            assert result == alert_detail_response["data"]
            assert mock_get.called
            url = mock_get.call_args[0][0]
            assert f"activity/alert/{ALERT_ID}" in url

    def test_get_alert_not_found(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.get_alert("nonexistent-id")

    def test_get_alert_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_alert(ALERT_ID)


# ---- post_alert tests ----

class TestPostAlert:
    def test_post_alert_success(self, er_client, alert_created_response):
        with patch.object(er_client._http_session, 'post') as mock_post:
            mock_post.return_value = _mock_response(201, alert_created_response)
            result = er_client.post_alert({
                "title": "New Alert",
                "reportTypes": ["fire_rep"],
            })
            assert result == alert_created_response["data"]
            assert mock_post.called

    def test_post_alert_not_found(self, er_client):
        with patch.object(er_client._http_session, 'post') as mock_post:
            mock_post.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.post_alert({"title": "test"})

    def test_post_alert_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'post') as mock_post:
            mock_post.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.post_alert({"title": "test"})


# ---- patch_alert tests ----

class TestPatchAlert:
    def test_patch_alert_success(self, er_client, alert_detail_response):
        with patch.object(er_client._http_session, 'patch') as mock_patch:
            mock_patch.return_value = _mock_response(200, alert_detail_response)
            result = er_client.patch_alert(ALERT_ID, {"is_active": False})
            assert result == alert_detail_response["data"]
            assert mock_patch.called

    def test_patch_alert_not_found(self, er_client):
        with patch.object(er_client._http_session, 'patch') as mock_patch:
            mock_patch.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.patch_alert(ALERT_ID, {"is_active": False})

    def test_patch_alert_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'patch') as mock_patch:
            mock_patch.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.patch_alert(ALERT_ID, {"is_active": False})


# ---- delete_alert tests ----

class TestDeleteAlert:
    def test_delete_alert_success(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(204)
            result = er_client.delete_alert(ALERT_ID)
            assert result is True
            assert mock_delete.called
            url = mock_delete.call_args[0][0]
            assert f"activity/alert/{ALERT_ID}/" in url

    def test_delete_alert_not_found(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.delete_alert(ALERT_ID)

    def test_delete_alert_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.delete_alert(ALERT_ID)


# ---- get_alert_conditions tests ----

class TestGetAlertConditions:
    def test_get_alert_conditions_success(self, er_client):
        conditions_response = {
            "data": [
                {"value": "poaching_rep", "display": "Poaching Report", "factors": []},
                {"value": "fire_rep", "display": "Fire Report", "factors": []},
            ],
            "status": {"code": 200, "message": "OK"},
        }
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, conditions_response)
            result = er_client.get_alert_conditions()
            assert result == conditions_response["data"]
            assert mock_get.called
            url = mock_get.call_args[0][0]
            assert "activity/alerts/conditions" in url

    def test_get_alert_conditions_empty(self, er_client):
        empty_response = {"data": [], "status": {"code": 200, "message": "OK"}}
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, empty_response)
            result = er_client.get_alert_conditions()
            assert result == []

    def test_get_alert_conditions_with_params(self, er_client):
        conditions_response = {
            "data": [{"value": "fire_rep", "display": "Fire Report", "factors": []}],
            "status": {"code": 200, "message": "OK"},
        }
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, conditions_response)
            result = er_client.get_alert_conditions(
                event_type="fire_rep", only_common_factors=True
            )
            assert result == conditions_response["data"]
            assert mock_get.called
            # Verify params were passed
            call_kwargs = mock_get.call_args
            params = call_kwargs[1].get('params') or call_kwargs.kwargs.get('params')
            assert params is not None
            assert params.get('event_type') == 'fire_rep'
            assert params.get('only_common_factors') is True

    def test_get_alert_conditions_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_alert_conditions()
