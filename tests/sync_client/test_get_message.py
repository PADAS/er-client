import json
from unittest.mock import patch, MagicMock

import pytest

from erclient import ERClientNotFound


def test_get_message_success(er_client, message_detail_response):
    message_id = "da783214-0d79-4d8c-ba6c-687688e3f6e7"
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.text = json.dumps(message_detail_response)

    with patch.object(er_client._http_session, "get", return_value=mock_response):
        result = er_client.get_message(message_id)

    assert result == message_detail_response["data"]


def test_get_message_not_found(er_client):
    message_id = "nonexistent-id"
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.text = json.dumps({"status": {"detail": "not found"}})

    with patch.object(er_client._http_session, "get", return_value=mock_response):
        with pytest.raises(ERClientNotFound):
            er_client.get_message(message_id)
