import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from erclient.client import ERClient


SUBJECT_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SOURCE_ID = "bbbb1111-2222-3333-4444-555566667777"


@pytest.fixture
def v1_tracks_response():
    return {
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [36.7922, -1.2932],
                            [36.7921, -1.2931],
                            [36.7919, -1.2931],
                        ],
                    },
                    "properties": {"title": "Test Subject"},
                }
            ],
        }
    }


@pytest.fixture
def v2_tracks_response():
    return {
        "data": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [36.7922, -1.2932],
                            [36.7921, -1.2931],
                        ],
                    },
                    "properties": {
                        "count": 2,
                        "start_time": "2025-01-01T00:00:00Z",
                        "end_time": "2025-01-01T01:00:00Z",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [36.7919, -1.2931],
                            [36.7917, -1.2931],
                        ],
                    },
                    "properties": {
                        "count": 2,
                        "start_time": "2025-01-01T02:00:00Z",
                        "end_time": "2025-01-01T03:00:00Z",
                    },
                },
            ],
        }
    }


def _mock_response(json_body, status_code=200):
    """Create a mock requests.Response with the given JSON body."""
    mock_resp = MagicMock()
    mock_resp.ok = status_code < 400
    mock_resp.status_code = status_code
    mock_resp.text = json.dumps(json_body)
    mock_resp.json.return_value = json_body
    return mock_resp


# ── v1 (default) tracks ──────────────────────────────────────────

def test_get_subject_tracks_v1_default(er_client, v1_tracks_response):
    """get_subject_tracks() with default version hits the v1 endpoint."""
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(v1_tracks_response)

        result = er_client.get_subject_tracks(subject_id=SUBJECT_ID)

        assert mock_get.called
        call_args = mock_get.call_args
        assert f"subject/{SUBJECT_ID}/tracks" in call_args[0][0]
        assert "v1.0" in call_args[0][0]
        assert result == v1_tracks_response["data"]


def test_get_subject_tracks_v1_with_dates(er_client, v1_tracks_response):
    """v1 tracks pass since/until params when start/end are given."""
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(v1_tracks_response)

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        er_client.get_subject_tracks(subject_id=SUBJECT_ID, start=start, end=end)

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert "since" in params
        assert "until" in params


# ── v2 segmented tracks ──────────────────────────────────────────

def test_get_subject_tracks_v2(er_client, v2_tracks_response):
    """get_subject_tracks(version='2.0') hits the v2 segmented endpoint."""
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(v2_tracks_response)

        result = er_client.get_subject_tracks(
            subject_id=SUBJECT_ID, version="2.0"
        )

        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert "v2.0" in call_url
        assert f"subject/{SUBJECT_ID}/tracks/" in call_url
        assert result == v2_tracks_response["data"]


def test_get_subject_tracks_v2_with_dates(er_client, v2_tracks_response):
    """v2 tracks pass since/until when start/end are given."""
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(v2_tracks_response)

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        er_client.get_subject_tracks(
            subject_id=SUBJECT_ID, start=start, end=end, version="2.0"
        )

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert "since" in params
        assert "until" in params


def test_get_subject_tracks_v2_extra_params(er_client, v2_tracks_response):
    """v2 tracks forward additional filter params."""
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(v2_tracks_response)

        er_client.get_subject_tracks(
            subject_id=SUBJECT_ID,
            version="2.0",
            show_excluded="true",
            max_speed_kmh=120.0,
            max_gap_minutes=30,
        )

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert params.get("show_excluded") == "true"
        assert params.get("max_speed_kmh") == 120.0
        assert params.get("max_gap_minutes") == 30


def test_get_subject_tracks_v2_ignores_unknown_kwargs(er_client, v2_tracks_response):
    """Unknown kwargs are not forwarded as query params."""
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(v2_tracks_response)

        er_client.get_subject_tracks(
            subject_id=SUBJECT_ID,
            version="2.0",
            unknown_param="should_not_appear",
        )

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert "unknown_param" not in params


# ── _er_url_versioned helper ──────────────────────────────────────

def test_er_url_versioned_v1(er_client):
    """_er_url_versioned('path', '1.0') returns the normal v1 URL."""
    url = er_client._er_url_versioned("subject/abc/tracks", version="1.0")
    assert url == "https://fake-site.erdomain.org/api/v1.0/subject/abc/tracks"


def test_er_url_versioned_v2(er_client):
    """_er_url_versioned('path', '2.0') swaps the version in the URL."""
    url = er_client._er_url_versioned("subject/abc/tracks/", version="2.0")
    assert url == "https://fake-site.erdomain.org/api/v2.0/subject/abc/tracks/"


# ── get_subject_source_tracks ─────────────────────────────────────

def test_get_subject_source_tracks(er_client, v1_tracks_response):
    """get_subject_source_tracks() hits the correct endpoint."""
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(v1_tracks_response)

        result = er_client.get_subject_source_tracks(
            subject_id=SUBJECT_ID, src_id=SOURCE_ID
        )

        call_url = mock_get.call_args[0][0]
        assert f"subject/{SUBJECT_ID}/source/{SOURCE_ID}/tracks" in call_url
        assert result == v1_tracks_response["data"]


def test_get_subject_source_tracks_with_since(er_client, v1_tracks_response):
    """get_subject_source_tracks() passes since param."""
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(v1_tracks_response)

        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        er_client.get_subject_source_tracks(
            subject_id=SUBJECT_ID, src_id=SOURCE_ID, start=start
        )

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
        assert "since" in params
