import json
from unittest.mock import patch, MagicMock

import pytest

from erclient import ERClientNotFound, ERClientPermissionDenied


def test_post_message_success(er_client, message, message_created_response):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = message_created_response
    mock_response.text = json.dumps(message_created_response)

    with patch.object(er_client._http_session, "post", return_value=mock_response):
        result = er_client.post_message(message)

    assert result == message_created_response["data"]


def test_post_message_returns_full_response_when_no_data_key(er_client, message):
    """When the response has no 'data' key, the full response is returned."""
    raw_response = {
        "id": "da783214-0d79-4d8c-ba6c-687688e3f6e7",
        "text": "A test message!",
    }
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = raw_response
    mock_response.text = json.dumps(raw_response)

    with patch.object(er_client._http_session, "post", return_value=mock_response):
        result = er_client.post_message(message)

    assert result == raw_response


def test_post_message_not_found(er_client, message):
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.text = json.dumps({"status": {"detail": "not found"}})

    with patch.object(er_client._http_session, "post", return_value=mock_response):
        with pytest.raises(ERClientNotFound):
            er_client.post_message(message)


def test_post_message_forbidden(er_client, message):
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 403
    mock_response.text = json.dumps(
        {"status": {"detail": "You do not have permission to perform this action."}}
    )

    with patch.object(er_client._http_session, "post", return_value=mock_response):
        with pytest.raises(ERClientPermissionDenied):
            er_client.post_message(message)
