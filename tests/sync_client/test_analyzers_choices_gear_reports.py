"""Tests for analyzers, choices, buoy/gear, and reports endpoints (sync client)."""

import json
from unittest.mock import MagicMock, patch

import pytest


GEAR_ID = "aabb1122-3344-5566-7788-99aabbccddee"
CHOICE_ID = "ccdd1122-3344-5566-7788-99aabbccddee"
VIEW_ID = "eeff1122-3344-5566-7788-99aabbccddee"


def _mock_response(json_body, status_code=200):
    mock_resp = MagicMock()
    mock_resp.ok = status_code < 400
    mock_resp.status_code = status_code
    mock_resp.text = json.dumps(json_body)
    mock_resp.json.return_value = json_body
    return mock_resp


# ── Analyzers ─────────────────────────────────────────────────────

def test_get_analyzers_spatial(er_client):
    response = {"data": [{"id": "1", "name": "Geofence"}]}
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(response)
        result = er_client.get_analyzers_spatial()

        assert mock_get.called
        assert "analyzers/spatial" in mock_get.call_args[0][0]
        assert result == response["data"]


def test_get_analyzers_subject(er_client):
    response = {"data": [{"id": "2", "name": "Immobility"}]}
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(response)
        result = er_client.get_analyzers_subject()

        assert mock_get.called
        assert "analyzers/subject" in mock_get.call_args[0][0]
        assert result == response["data"]


# ── Choices ───────────────────────────────────────────────────────

def test_get_choices(er_client):
    response = {"data": [{"id": CHOICE_ID, "field_name": "species"}]}
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(response)
        result = er_client.get_choices()

        assert "choices" in mock_get.call_args[0][0]
        assert result == response["data"]


def test_get_choice(er_client):
    response = {"data": {"id": CHOICE_ID, "field_name": "species"}}
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(response)
        result = er_client.get_choice(CHOICE_ID)

        assert f"choices/{CHOICE_ID}" in mock_get.call_args[0][0]
        assert result == response["data"]


def test_download_choice_icons(er_client):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = '{"data": "zip"}'
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = mock_resp
        result = er_client.download_choice_icons()

        assert "choices/icons/download" in mock_get.call_args[0][0]
        # return_response=True means we get the raw response back
        assert result == mock_resp


# ── Gear CRUD ─────────────────────────────────────────────────────

def test_get_gear_list(er_client):
    response = {"data": [{"id": GEAR_ID, "name": "Buoy"}]}
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(response)
        result = er_client.get_gear_list()

        assert "buoy/gear" in mock_get.call_args[0][0]
        assert result == response["data"]


def test_get_gear(er_client):
    response = {"data": {"id": GEAR_ID, "name": "Buoy"}}
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(response)
        result = er_client.get_gear(GEAR_ID)

        assert f"buoy/gear/{GEAR_ID}" in mock_get.call_args[0][0]
        assert result == response["data"]


def test_post_gear(er_client):
    response = {"data": {"id": GEAR_ID, "name": "New"}}
    with patch.object(er_client._http_session, "post") as mock_post:
        mock_post.return_value = _mock_response(response, 201)
        result = er_client.post_gear({"name": "New", "gear_type": "buoy"})

        assert mock_post.called
        assert "buoy/gear" in mock_post.call_args[0][0]
        assert result == response["data"]


def test_patch_gear(er_client):
    response = {"data": {"id": GEAR_ID, "name": "Updated"}}
    with patch.object(er_client._http_session, "patch") as mock_patch:
        mock_patch.return_value = _mock_response(response)
        result = er_client.patch_gear(GEAR_ID, {"name": "Updated"})

        assert f"buoy/gear/{GEAR_ID}" in mock_patch.call_args[0][0]
        assert result == response["data"]


def test_delete_gear(er_client):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 204
    with patch.object(er_client._http_session, "delete") as mock_delete:
        mock_delete.return_value = mock_resp
        result = er_client.delete_gear(GEAR_ID)

        assert f"buoy/gear/{GEAR_ID}" in mock_delete.call_args[0][0]
        assert result is True


# ── Reports / Tableau ─────────────────────────────────────────────

def test_get_sitrep(er_client):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = b"binary-docx-content"
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = mock_resp
        result = er_client.get_sitrep()

        assert "reports/sitrep.docx" in mock_get.call_args[0][0]
        # return_response=True => raw response
        assert result == mock_resp


def test_get_tableau_views(er_client):
    response = {"data": [{"id": VIEW_ID, "title": "Dashboard"}]}
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(response)
        result = er_client.get_tableau_views()

        assert "reports/tableau-views" in mock_get.call_args[0][0]
        assert result == response["data"]


def test_get_tableau_view(er_client):
    response = {"data": {"id": VIEW_ID, "title": "Dashboard"}}
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(response)
        result = er_client.get_tableau_view(VIEW_ID)

        assert f"reports/tableau-views/{VIEW_ID}" in mock_get.call_args[0][0]
        assert result == response["data"]
