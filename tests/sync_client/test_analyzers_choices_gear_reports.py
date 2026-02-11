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


# -- Analyzer tests --


def test_get_analyzers_spatial(er_client):
    expected = [{"id": "sa-001", "name": "Geofence Analyzer"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_analyzers_spatial()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_analyzers_subject(er_client):
    expected = [{"id": "sub-001", "name": "Immobility Analyzer"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_analyzers_subject()
    er_client._http_session.get.assert_called_once()
    assert result == expected


# -- Choices tests --


def test_get_choices(er_client):
    expected = [{"id": "ch-001", "name": "Species"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_choices()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_choice(er_client):
    expected = {"id": "ch-001", "name": "Species"}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_choice("ch-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_choice_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_choice("nonexistent")


def test_download_choice_icons(er_client):
    """download_choice_icons returns the raw response object."""
    mock_resp = _mock_response(200)
    mock_resp.content = b"PK\x03\x04..."  # zip file header
    er_client._http_session.get = MagicMock(return_value=mock_resp)
    result = er_client.download_choice_icons()
    er_client._http_session.get.assert_called_once()
    # return_response=True means we get the raw response
    assert result == mock_resp


# -- Gear CRUD tests --


def test_get_gear(er_client):
    expected = [{"id": "gear-001", "name": "Buoy Alpha"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_gear()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_gear_item(er_client):
    expected = {"id": "gear-001", "name": "Buoy Alpha"}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_gear_item("gear-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_gear_item_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_gear_item("nonexistent")


def test_post_gear(er_client):
    payload = {"name": "New Buoy"}
    created = {"data": {"id": "gear-003", "name": "New Buoy"}, "status": {"code": 201}}
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(201, created)
    )
    result = er_client.post_gear(payload)
    er_client._http_session.post.assert_called_once()
    assert result == created["data"]


def test_post_gear_forbidden(er_client):
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(403, {"status": {"detail": "Forbidden"}})
    )
    with pytest.raises(ERClientPermissionDenied):
        er_client.post_gear({"name": "Test"})


def test_patch_gear(er_client):
    updated = {"data": {"id": "gear-001", "name": "Updated Buoy"}}
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(200, updated)
    )
    result = er_client.patch_gear("gear-001", {"name": "Updated Buoy"})
    er_client._http_session.patch.assert_called_once()
    assert result["name"] == "Updated Buoy"


def test_patch_gear_not_found(er_client):
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.patch_gear("nonexistent", {"name": "x"})


def test_delete_gear(er_client):
    er_client._http_session.delete = MagicMock(
        return_value=_mock_response(204)
    )
    result = er_client.delete_gear("gear-001")
    er_client._http_session.delete.assert_called_once()
    assert result is True


def test_delete_gear_not_found(er_client):
    er_client._http_session.delete = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.delete_gear("nonexistent")


# -- Reports / Tableau tests --


def test_get_sitrep(er_client):
    """get_sitrep returns the raw response for file download."""
    mock_resp = _mock_response(200)
    mock_resp.content = b"\x50\x4b\x03\x04"  # docx file header
    er_client._http_session.get = MagicMock(return_value=mock_resp)
    result = er_client.get_sitrep()
    er_client._http_session.get.assert_called_once()
    assert result == mock_resp


def test_get_tableau_views(er_client):
    expected = [{"id": "tv-001", "title": "Wildlife Overview"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_tableau_views()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_tableau_view(er_client):
    expected = {"id": "tv-001", "title": "Wildlife Overview"}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_tableau_view("tv-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_tableau_view_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_tableau_view("nonexistent")
