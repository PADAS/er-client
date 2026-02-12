import json
from unittest.mock import patch, MagicMock

import pytest

from erclient import ERClientNotFound, ERClientPermissionDenied


def test_delete_message_success(er_client):
    message_id = "da783214-0d79-4d8c-ba6c-687688e3f6e7"
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 204

    with patch.object(er_client._http_session, "delete", return_value=mock_response) as mock_delete:
        # Sync delete_message calls _delete which returns True but delete_message itself doesn't return
        er_client.delete_message(message_id)

    # Verify the delete endpoint was called correctly
    mock_delete.assert_called_once()
    call_url = mock_delete.call_args[0][0]
    assert "messages/" + message_id + "/" in call_url


def test_delete_message_not_found(er_client):
    message_id = "nonexistent-id"
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.text = json.dumps({"status": {"detail": "not found"}})

    with patch.object(er_client._http_session, "delete", return_value=mock_response):
        with pytest.raises(ERClientNotFound):
            er_client.delete_message(message_id)


def test_delete_message_forbidden(er_client):
    message_id = "da783214-0d79-4d8c-ba6c-687688e3f6e7"
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 403
    mock_response.text = json.dumps(
        {"status": {"detail": "You do not have permission to perform this action."}}
    )

    with patch.object(er_client._http_session, "delete", return_value=mock_response):
        with pytest.raises(ERClientPermissionDenied):
            er_client.delete_message(message_id)
