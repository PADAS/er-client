import json
from unittest.mock import MagicMock, patch

import pytest

from erclient.er_errors import (
    ERClientBadCredentials,
    ERClientException,
    ERClientNotFound,
    ERClientPermissionDenied,
)

CSV_BODY = (
    "Report_Type,Report_Id,Title\n"
    "wildlife_sighting_rep,1001,Elephant Sighting\n"
    "wildlife_sighting_rep,1002,Lion Sighting\n"
)


def _mock_response(status_code=200, text=CSV_BODY, ok=True, headers=None):
    response = MagicMock()
    response.status_code = status_code
    response.ok = ok
    response.text = text
    response.headers = headers or {"Content-Type": "text/csv"}
    response.url = "https://fake-site.erdomain.org/api/v1.0/activity/events/export/"
    return response


# -- Success cases -----------------------------------------------------------

def test_get_events_export_returns_raw_response(er_client):
    """The sync method should return the raw requests.Response."""
    mock_resp = _mock_response()
    with patch.object(er_client._http_session, "get", return_value=mock_resp):
        result = er_client.get_events_export()

    assert result is mock_resp
    assert result.status_code == 200
    assert result.text == CSV_BODY


def test_get_events_export_with_filter(er_client):
    """When a filter is supplied it should be forwarded as a param."""
    mock_resp = _mock_response()
    event_filter = json.dumps(
        {"date_range": {"lower": "2024-01-01T00:00:00-06:00"}}
    )
    with patch.object(
        er_client._http_session, "get", return_value=mock_resp
    ) as mock_get:
        er_client.get_events_export(filter=event_filter)

    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"filter": event_filter}


def test_get_events_export_without_filter(er_client):
    """Without a filter no 'filter' param should be present."""
    mock_resp = _mock_response()
    with patch.object(
        er_client._http_session, "get", return_value=mock_resp
    ) as mock_get:
        er_client.get_events_export()

    _, kwargs = mock_get.call_args
    assert kwargs["params"] is None


def test_get_events_export_url_construction(er_client):
    """The request URL should end with activity/events/export/."""
    mock_resp = _mock_response()
    with patch.object(
        er_client._http_session, "get", return_value=mock_resp
    ) as mock_get:
        er_client.get_events_export()

    call_args = mock_get.call_args
    url = call_args[0][0]  # positional arg
    assert url.endswith("activity/events/export/")
    assert url.startswith(er_client.service_root)


# -- Error cases --------------------------------------------------------------

def test_get_events_export_not_found(er_client):
    mock_resp = _mock_response(status_code=404, ok=False, text='{"status":{"code":404}}')
    with patch.object(er_client._http_session, "get", return_value=mock_resp):
        with pytest.raises(ERClientNotFound):
            er_client.get_events_export()


def test_get_events_export_forbidden(er_client):
    mock_resp = _mock_response(
        status_code=403,
        ok=False,
        text='{"status":{"code":403,"detail":"You do not have permission"}}',
    )
    with patch.object(er_client._http_session, "get", return_value=mock_resp):
        with pytest.raises(ERClientPermissionDenied):
            er_client.get_events_export()


def test_get_events_export_bad_credentials(er_client):
    mock_resp = _mock_response(
        status_code=401,
        ok=False,
        text='{"status":{"code":401,"detail":"Authentication credentials were not provided."}}',
    )
    with patch.object(er_client._http_session, "get", return_value=mock_resp):
        with pytest.raises(ERClientBadCredentials):
            er_client.get_events_export()


def test_get_events_export_server_error(er_client):
    """Server errors should eventually raise ERClientException after retries."""
    mock_resp = _mock_response(
        status_code=500,
        ok=False,
        text='{"detail":"Internal server error"}',
    )
    with patch.object(er_client._http_session, "get", return_value=mock_resp):
        with pytest.raises(ERClientException):
            er_client.get_events_export()


def test_get_events_export_empty_csv(er_client):
    """An empty CSV body (headers only) should still return the raw response."""
    empty_csv = "Report_Type,Report_Id,Title\n"
    mock_resp = _mock_response(text=empty_csv)
    with patch.object(er_client._http_session, "get", return_value=mock_resp):
        result = er_client.get_events_export()

    assert result.text == empty_csv
    assert result.status_code == 200
