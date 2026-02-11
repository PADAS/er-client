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


# -- Read-only endpoint tests --


def test_get_features(er_client):
    expected = [{"type": "Feature", "properties": {"name": "Post A"}}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_features()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_feature(er_client):
    expected = {"type": "Feature", "properties": {"name": "Post A", "id": "fp-001"}}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_feature("fp-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_feature_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_feature("nonexistent")


def test_get_featuresets(er_client):
    expected = [{"id": "fs-001", "name": "Ranger Posts"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_featuresets()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_featureset(er_client):
    expected = {"id": "fs-001", "name": "Ranger Posts"}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_featureset("fs-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_maps(er_client):
    expected = [{"id": "map-001", "title": "Park Overview"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_maps()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_layers(er_client):
    expected = [{"id": "layer-001", "title": "Roads"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_layers()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_layer(er_client):
    expected = {"id": "layer-001", "title": "Roads"}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_layer("layer-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_featureclasses(er_client):
    expected = [{"id": "fc-001", "name": "boundary"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_featureclasses()
    er_client._http_session.get.assert_called_once()
    assert result == expected


# -- Spatial Feature Group CRUD tests --


def test_get_spatialfeaturegroups(er_client):
    expected = [{"id": "sfg-001", "name": "Protected Areas"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_spatialfeaturegroups()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_spatialfeaturegroup(er_client):
    expected = {"id": "sfg-001", "name": "Protected Areas"}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_spatialfeaturegroup("sfg-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_spatialfeaturegroup_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_spatialfeaturegroup("nonexistent")


def test_post_spatialfeaturegroup(er_client):
    payload = {"name": "Protected Areas"}
    created = {"data": {"id": "sfg-001", "name": "Protected Areas"}, "status": {"code": 201}}
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(201, created)
    )
    result = er_client.post_spatialfeaturegroup(payload)
    er_client._http_session.post.assert_called_once()
    assert result == created["data"]


def test_post_spatialfeaturegroup_forbidden(er_client):
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(403, {"status": {"detail": "Forbidden"}})
    )
    with pytest.raises(ERClientPermissionDenied):
        er_client.post_spatialfeaturegroup({"name": "Test"})


def test_patch_spatialfeaturegroup(er_client):
    updated = {"data": {"id": "sfg-001", "name": "Renamed"}, "status": {"code": 200}}
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(200, updated)
    )
    result = er_client.patch_spatialfeaturegroup("sfg-001", {"name": "Renamed"})
    er_client._http_session.patch.assert_called_once()
    assert result["name"] == "Renamed"


def test_patch_spatialfeaturegroup_not_found(er_client):
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.patch_spatialfeaturegroup("nonexistent", {"name": "X"})


def test_delete_spatialfeaturegroup(er_client):
    er_client._http_session.delete = MagicMock(
        return_value=_mock_response(204)
    )
    result = er_client.delete_spatialfeaturegroup("sfg-001")
    er_client._http_session.delete.assert_called_once()
    assert result is True


def test_delete_spatialfeaturegroup_not_found(er_client):
    er_client._http_session.delete = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.delete_spatialfeaturegroup("nonexistent")


# -- Spatial Feature CRUD tests --


def test_get_spatialfeatures(er_client):
    expected = [{"id": "sf-001", "name": "Nairobi NP"}]
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_spatialfeatures()
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_spatialfeature(er_client):
    expected = {"id": "sf-001", "name": "Nairobi NP"}
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(200, {"data": expected})
    )
    result = er_client.get_spatialfeature("sf-001")
    er_client._http_session.get.assert_called_once()
    assert result == expected


def test_get_spatialfeature_not_found(er_client):
    er_client._http_session.get = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.get_spatialfeature("nonexistent")


def test_post_spatialfeature(er_client):
    payload = {"name": "Nairobi NP"}
    created = {"data": {"id": "sf-001", "name": "Nairobi NP"}, "status": {"code": 201}}
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(201, created)
    )
    result = er_client.post_spatialfeature(payload)
    er_client._http_session.post.assert_called_once()
    assert result == created["data"]


def test_post_spatialfeature_forbidden(er_client):
    er_client._http_session.post = MagicMock(
        return_value=_mock_response(403, {"status": {"detail": "Forbidden"}})
    )
    with pytest.raises(ERClientPermissionDenied):
        er_client.post_spatialfeature({"name": "Test"})


def test_patch_spatialfeature(er_client):
    updated = {"data": {"id": "sf-001", "name": "Updated Park"}, "status": {"code": 200}}
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(200, updated)
    )
    result = er_client.patch_spatialfeature("sf-001", {"name": "Updated Park"})
    er_client._http_session.patch.assert_called_once()
    assert result["name"] == "Updated Park"


def test_patch_spatialfeature_not_found(er_client):
    er_client._http_session.patch = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.patch_spatialfeature("nonexistent", {"name": "X"})


def test_delete_spatialfeature(er_client):
    er_client._http_session.delete = MagicMock(
        return_value=_mock_response(204)
    )
    result = er_client.delete_spatialfeature("sf-001")
    er_client._http_session.delete.assert_called_once()
    assert result is True


def test_delete_spatialfeature_not_found(er_client):
    er_client._http_session.delete = MagicMock(
        return_value=_mock_response(404, {"status": {"code": 404}})
    )
    with pytest.raises(ERClientNotFound):
        er_client.delete_spatialfeature("nonexistent")
