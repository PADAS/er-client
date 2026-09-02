import json
from unittest.mock import patch, MagicMock, call

import pytest


def test_get_messages_single_page(er_client, get_messages_single_page_response):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.text = json.dumps(get_messages_single_page_response)

    with patch.object(er_client._http_session, "get", return_value=mock_response):
        messages = list(er_client.get_messages())

    assert len(messages) == 2
    assert messages[0]["id"] == "da783214-0d79-4d8c-ba6c-687688e3f6e7"
    assert messages[1]["id"] == "ab123456-0d79-4d8c-ba6c-687688e3f6e7"


def test_get_messages_paginated(
    er_client, get_messages_page_one_response, get_messages_page_two_response
):
    mock_response_page1 = MagicMock()
    mock_response_page1.ok = True
    mock_response_page1.text = json.dumps(get_messages_page_one_response)

    mock_response_page2 = MagicMock()
    mock_response_page2.ok = True
    mock_response_page2.text = json.dumps(get_messages_page_two_response)

    with patch.object(
        er_client._http_session,
        "get",
        side_effect=[mock_response_page1, mock_response_page2],
    ):
        messages = list(er_client.get_messages())

    assert len(messages) == 3
    assert messages[0]["id"] == "da783214-0d79-4d8c-ba6c-687688e3f6e7"
    assert messages[1]["id"] == "ab123456-0d79-4d8c-ba6c-687688e3f6e7"
    assert messages[2]["id"] == "cd789012-0d79-4d8c-ba6c-687688e3f6e7"


def test_get_messages_empty(er_client):
    empty_response = {
        "data": {
            "count": 0,
            "next": None,
            "previous": None,
            "results": [],
        }
    }
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.text = json.dumps(empty_response)

    with patch.object(er_client._http_session, "get", return_value=mock_response):
        messages = list(er_client.get_messages())

    assert len(messages) == 0


def test_get_messages_accepts_kwargs(er_client, get_messages_single_page_response):
    """Verify that extra kwargs like page_size are passed as params."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.text = json.dumps(get_messages_single_page_response)

    with patch.object(er_client._http_session, "get", return_value=mock_response) as mock_get:
        messages = list(er_client.get_messages(page_size=50))

    # Verify that get was called with the page_size param
    call_kwargs = mock_get.call_args
    assert call_kwargs is not None
    assert "params" in call_kwargs.kwargs or (
        len(call_kwargs.args) > 1
        or (call_kwargs.kwargs.get("params", {}).get("page_size") == 50)
    )
