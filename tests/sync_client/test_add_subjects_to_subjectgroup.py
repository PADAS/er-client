import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from erclient import (ERClientException, ERClientNotFound,
                      ERClientPermissionDenied)
from erclient.client import ERClient

GROUP_ID = "ac1413b9-8177-4a81-85d6-a46fc95bdd70"
SUBJECT_ID = "1fed139e-070d-464c-9652-e9420437b068"
SUBJECTS_PAYLOAD = [{"id": SUBJECT_ID}]


def _mock_response(status_code, json_data=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    if json_data is not None:
        resp.json.return_value = json_data
        resp.text = json.dumps(json_data)
    else:
        resp.json.return_value = {}
        resp.text = ""
    return resp


def test_add_subjects_to_subjectgroup_success(er_server_info):
    """Test successful subject assignment to a subject group."""
    response_data = [{"id": SUBJECT_ID, "name": "MMVessel"}]
    with patch("erclient.client.requests.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = _mock_response(
            200, response_data)
        mock_session.return_value = mock_session_instance

        client = ERClient(**er_server_info)
        result = client.add_subjects_to_subjectgroup(
            group_id=GROUP_ID,
            subjects=SUBJECTS_PAYLOAD,
        )

        mock_session_instance.post.assert_called_once()
        call_url = mock_session_instance.post.call_args[0][0]
        assert f"subjectgroup/{GROUP_ID}/subjects/" in call_url
        assert result == response_data


def test_add_subjects_to_subjectgroup_not_found(er_server_info):
    """Test 404 raises ERClientNotFound."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = _mock_response(404)
        mock_session.return_value = mock_session_instance

        client = ERClient(**er_server_info)
        with pytest.raises(ERClientNotFound):
            client.add_subjects_to_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        mock_session_instance.post.assert_called_once()


def test_add_subjects_to_subjectgroup_permission_denied(er_server_info):
    """Test 403 raises ERClientPermissionDenied."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = _mock_response(403)
        mock_session.return_value = mock_session_instance

        client = ERClient(**er_server_info)
        with pytest.raises(ERClientPermissionDenied):
            client.add_subjects_to_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        mock_session_instance.post.assert_called_once()


def test_add_subjects_to_subjectgroup_server_error(er_server_info):
    """Test 500 raises ERClientException."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = _mock_response(500)
        mock_session.return_value = mock_session_instance

        client = ERClient(**er_server_info)
        with pytest.raises(ERClientException):
            client.add_subjects_to_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        mock_session_instance.post.assert_called_once()


def test_remove_subjects_from_subjectgroup_success(er_server_info):
    """Test successful removal of subjects from a subject group."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = _mock_response(200)
        mock_session.return_value = mock_session_instance

        client = ERClient(**er_server_info)
        result = client.remove_subjects_from_subjectgroup(
            group_id=GROUP_ID,
            subjects=SUBJECTS_PAYLOAD,
        )

        mock_session_instance.delete.assert_called_once()
        call_args = mock_session_instance.delete.call_args
        assert f"subjectgroup/{GROUP_ID}/subjects/" in call_args[0][0]
        assert call_args[1]["json"] == SUBJECTS_PAYLOAD
        assert result is True


def test_remove_subjects_from_subjectgroup_not_found(er_server_info):
    """Test 404 raises ERClientNotFound."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = _mock_response(404)
        mock_session.return_value = mock_session_instance

        client = ERClient(**er_server_info)
        with pytest.raises(ERClientNotFound):
            client.remove_subjects_from_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        mock_session_instance.delete.assert_called_once()


def test_remove_subjects_from_subjectgroup_permission_denied(er_server_info):
    """Test 403 raises ERClientPermissionDenied."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = _mock_response(403)
        mock_session.return_value = mock_session_instance

        client = ERClient(**er_server_info)
        with pytest.raises(ERClientPermissionDenied):
            client.remove_subjects_from_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        mock_session_instance.delete.assert_called_once()


def test_remove_subjects_from_subjectgroup_server_error(er_server_info):
    """Test 500 raises ERClientException."""
    with patch("erclient.client.requests.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.delete.return_value = _mock_response(500)
        mock_session.return_value = mock_session_instance

        client = ERClient(**er_server_info)
        with pytest.raises(ERClientException):
            client.remove_subjects_from_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        mock_session_instance.delete.assert_called_once()
