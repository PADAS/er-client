"""Tests for GeoJSON, KML, and vector tile endpoints in the sync ERClient."""
import json
from unittest.mock import patch, MagicMock

import pytest


SERVICE_ROOT = "https://fake-site.erdomain.org/api/v1.0"
SUBJECT_ID = "aaaa1111-2222-3333-4444-bbbbccccdddd"


def _mock_response(json_data=None, status_code=200, content=b"", ok=True):
    """Helper to build a mock requests.Response."""
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status_code
    resp.text = json.dumps(json_data) if json_data is not None else ""
    resp.content = content
    resp.json.return_value = json_data
    return resp


# --- Fixtures ---

@pytest.fixture
def events_geojson_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-122.359, 47.686]},
                "properties": {"event_type": "rainfall_rep", "title": "Rainfall"},
            }
        ],
    }


@pytest.fixture
def subjects_geojson_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [36.79, -1.29]},
                "properties": {"name": "Lion A", "subject_subtype": "lion"},
            }
        ],
    }


# --- GeoJSON tests ---

def test_get_events_geojson(er_client, events_geojson_response):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(events_geojson_response)
        result = er_client.get_events_geojson()

        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert "activity/events/geojson" in call_url
        assert result == events_geojson_response


def test_get_events_geojson_with_params(er_client, events_geojson_response):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(events_geojson_response)
        result = er_client.get_events_geojson(
            state="active", event_type="rainfall_rep", page_size=10
        )

        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params") or call_kwargs.kwargs.get("params")
        assert params["state"] == "active"
        assert params["event_type"] == "rainfall_rep"
        assert params["page_size"] == 10


def test_get_subjects_geojson(er_client, subjects_geojson_response):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(subjects_geojson_response)
        result = er_client.get_subjects_geojson()

        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert "subjects/geojson" in call_url
        assert result == subjects_geojson_response


def test_get_subjects_geojson_with_params(er_client, subjects_geojson_response):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(subjects_geojson_response)
        result = er_client.get_subjects_geojson(
            include_inactive=True, subject_group="abc"
        )

        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params") or call_kwargs.kwargs.get("params")
        assert params["include_inactive"] is True
        assert params["subject_group"] == "abc"


# --- KML tests ---

def test_get_subjects_kml(er_client):
    binary_content = b"PK\x03\x04..."  # mock KMZ bytes
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=binary_content, ok=True)
        # return_response=True means _get returns the raw response
        result = er_client.get_subjects_kml()

        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert "subjects/kml" in call_url
        # Returns the response object directly
        assert result.content == binary_content


def test_get_subjects_kml_with_dates(er_client):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=b"KMZ", ok=True)
        er_client.get_subjects_kml(start="2024-01-01", end="2024-06-01")

        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params") or call_kwargs.kwargs.get("params")
        assert params["start"] == "2024-01-01"
        assert params["end"] == "2024-06-01"


def test_get_subject_kml(er_client):
    binary_content = b"PK\x03\x04..."
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=binary_content, ok=True)
        result = er_client.get_subject_kml(subject_id=SUBJECT_ID)

        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert f"subject/{SUBJECT_ID}/kml" in call_url
        assert result.content == binary_content


def test_get_subject_kml_with_dates(er_client):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=b"KMZ", ok=True)
        er_client.get_subject_kml(
            subject_id=SUBJECT_ID, start="2024-03-01", end="2024-09-01"
        )

        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params") or call_kwargs.kwargs.get("params")
        assert params["start"] == "2024-03-01"
        assert params["end"] == "2024-09-01"


# --- Vector tile tests ---

def test_get_observation_segment_tiles(er_client):
    pbf_content = b"\x1a\x02\x00\x00"  # mock PBF bytes
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=pbf_content, ok=True)
        result = er_client.get_observation_segment_tiles(z=10, x=512, y=512)

        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert "observations/segments/tiles/10/512/512.pbf" in call_url
        assert result.content == pbf_content


def test_get_spatial_feature_tiles(er_client):
    pbf_content = b"\x1a\x02\x00\x00"
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=pbf_content, ok=True)
        result = er_client.get_spatial_feature_tiles(z=8, x=128, y=256)

        assert mock_get.called
        call_url = mock_get.call_args[0][0]
        assert "spatialfeatures/tiles/8/128/256.pbf" in call_url
        assert result.content == pbf_content


def test_get_observation_segment_tiles_with_params(er_client):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=b"PBF", ok=True)
        er_client.get_observation_segment_tiles(
            z=10, x=512, y=512, show_excluded="true"
        )

        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params") or call_kwargs.kwargs.get("params")
        assert params["show_excluded"] == "true"


# --- URL construction tests ---

def test_geojson_url_construction(er_client):
    """Verify the full URL is correctly assembled."""
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response({"type": "FeatureCollection", "features": []})
        er_client.get_events_geojson()

        call_url = mock_get.call_args[0][0]
        assert call_url == f"{SERVICE_ROOT}/activity/events/geojson"


def test_kml_url_construction(er_client):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=b"", ok=True)
        er_client.get_subjects_kml()

        call_url = mock_get.call_args[0][0]
        assert call_url == f"{SERVICE_ROOT}/subjects/kml"


def test_subject_kml_url_construction(er_client):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=b"", ok=True)
        er_client.get_subject_kml(subject_id=SUBJECT_ID)

        call_url = mock_get.call_args[0][0]
        assert call_url == f"{SERVICE_ROOT}/subject/{SUBJECT_ID}/kml"


def test_tiles_url_construction(er_client):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=b"", ok=True)
        er_client.get_observation_segment_tiles(z=10, x=512, y=512)

        call_url = mock_get.call_args[0][0]
        assert call_url == f"{SERVICE_ROOT}/observations/segments/tiles/10/512/512.pbf"


def test_spatial_tiles_url_construction(er_client):
    with patch.object(er_client._http_session, "get") as mock_get:
        mock_get.return_value = _mock_response(content=b"", ok=True)
        er_client.get_spatial_feature_tiles(z=8, x=128, y=256)

        call_url = mock_get.call_args[0][0]
        assert call_url == f"{SERVICE_ROOT}/spatialfeatures/tiles/8/128/256.pbf"
