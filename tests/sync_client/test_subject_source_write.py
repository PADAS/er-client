import json
from unittest.mock import MagicMock, patch

import pytest

from erclient import ERClientException, ERClientNotFound, ERClientPermissionDenied


# ---- Fixtures ----

@pytest.fixture
def subject_updated_response():
    return {
        "data": {
            "content_type": "observations.subject",
            "id": "d8ad9955-8301-43c4-9000-9a02f1cba675",
            "name": "MMVessel",
            "subject_type": "vehicle",
            "subject_subtype": "vessel",
            "is_active": False,
            "additional": {},
            "created_at": "2026-01-12T03:36:26.383023-08:00",
            "updated_at": "2026-01-12T04:30:12.289513-08:00",
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def subject_created_response():
    return {
        "data": {
            "content_type": "observations.subject",
            "id": "aabbccdd-1234-5678-9012-abcdefabcdef",
            "name": "Test Elephant",
            "subject_type": "wildlife",
            "subject_subtype": "elephant",
            "is_active": True,
            "additional": {},
            "created_at": "2026-02-10T12:00:00.000000-08:00",
            "updated_at": "2026-02-10T12:00:00.000000-08:00",
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def source_created_response():
    return {
        "data": {
            "id": "ee112233-4455-6677-8899-aabbccddeeff",
            "manufacturer_id": "collar-9999",
            "source_type": "tracking-device",
            "model_name": "Test Collar",
            "additional": {},
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def source_assignments_response():
    return {
        "data": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "subject": "123e4567-e89b-12d3-a456-426614174001",
                "source": "123e4567-e89b-12d3-a456-426614174002",
                "assigned_range": {
                    "lower": "2023-06-01T01:41:00+02:00",
                    "upper": "2024-01-11T19:41:00+02:00",
                    "bounds": "[)",
                },
            }
        ],
        "status": {"code": 200, "message": "OK"},
    }


def _mock_response(status_code=200, json_data=None, ok=True, text=None):
    mock = MagicMock()
    mock.ok = ok
    mock.status_code = status_code
    mock.text = text or json.dumps(json_data or {})
    mock.json.return_value = json_data or {}
    return mock


# ---- patch_subject tests ----

class TestPatchSubject:
    def test_patch_subject_success(self, er_client, subject_updated_response):
        with patch.object(er_client._http_session, 'patch') as mock_patch:
            mock_patch.return_value = _mock_response(
                200, subject_updated_response
            )
            result = er_client.patch_subject(
                "d8ad9955-8301-43c4-9000-9a02f1cba675",
                {"is_active": False},
            )
            assert result == subject_updated_response["data"]
            assert mock_patch.called

    def test_patch_subject_not_found(self, er_client):
        with patch.object(er_client._http_session, 'patch') as mock_patch:
            mock_patch.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.patch_subject("nonexistent-id", {"is_active": False})

    def test_patch_subject_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'patch') as mock_patch:
            mock_patch.return_value = _mock_response(
                403,
                ok=False,
                text='{"status":{"detail":"forbidden"}}',
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.patch_subject(
                    "d8ad9955-8301-43c4-9000-9a02f1cba675",
                    {"is_active": False},
                )


# ---- get_source_subjects tests ----

class TestGetSourceSubjects:
    def test_get_source_subjects_success(self, er_client):
        source_subjects_response = {
            "data": [
                {
                    "content_type": "observations.subject",
                    "id": "d8ad9955-8301-43c4-9000-9a02f1cba675",
                    "name": "MMVessel",
                    "subject_type": "vehicle",
                    "subject_subtype": "vessel",
                    "is_active": True,
                }
            ],
            "status": {"code": 200, "message": "OK"},
        }
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, source_subjects_response)
            source_id = "119feb94-a6cc-4485-8614-06fb0abc2a9c"
            result = er_client.get_source_subjects(source_id)
            assert result == source_subjects_response["data"]
            assert mock_get.called
            url = mock_get.call_args[0][0]
            assert f"source/{source_id}/subjects" in url

    def test_get_source_subjects_empty(self, er_client):
        empty_response = {
            "data": [],
            "status": {"code": 200, "message": "OK"},
        }
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, empty_response)
            result = er_client.get_source_subjects("119feb94-a6cc-4485-8614-06fb0abc2a9c")
            assert result == []

    def test_get_source_subjects_not_found(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.get_source_subjects("nonexistent-id")

    def test_get_source_subjects_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_source_subjects("119feb94-a6cc-4485-8614-06fb0abc2a9c")


# ---- get_source_subjects tests ----

class TestGetSourceSubjects:
    def test_get_source_subjects_success(self, er_client):
        source_subjects_response = {
            "data": [
                {
                    "content_type": "observations.subject",
                    "id": "d8ad9955-8301-43c4-9000-9a02f1cba675",
                    "name": "MMVessel",
                    "subject_type": "vehicle",
                    "subject_subtype": "vessel",
                    "is_active": True,
                }
            ],
            "status": {"code": 200, "message": "OK"},
        }
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, source_subjects_response)
            source_id = "119feb94-a6cc-4485-8614-06fb0abc2a9c"
            result = er_client.get_source_subjects(source_id)
            assert result == source_subjects_response["data"]
            assert mock_get.called
            url = mock_get.call_args[0][0]
            assert f"source/{source_id}/subjects" in url

    def test_get_source_subjects_empty(self, er_client):
        empty_response = {
            "data": [],
            "status": {"code": 200, "message": "OK"},
        }
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(200, empty_response)
            result = er_client.get_source_subjects("119feb94-a6cc-4485-8614-06fb0abc2a9c")
            assert result == []

    def test_get_source_subjects_not_found(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.get_source_subjects("nonexistent-id")

    def test_get_source_subjects_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.get_source_subjects("119feb94-a6cc-4485-8614-06fb0abc2a9c")


# ---- get_source_assignments tests ----

class TestGetSourceAssignments:
    def test_get_source_assignments_success(self, er_client, source_assignments_response):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                200, source_assignments_response
            )
            result = er_client.get_source_assignments()
            assert result == source_assignments_response["data"]
            assert mock_get.called

    def test_get_source_assignments_with_subject_ids(self, er_client, source_assignments_response):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                200, source_assignments_response
            )
            result = er_client.get_source_assignments(
                subject_ids=["123e4567-e89b-12d3-a456-426614174001"]
            )
            assert result == source_assignments_response["data"]
            # Verify that params were passed
            call_kwargs = mock_get.call_args
            assert 'params' in call_kwargs.kwargs or len(call_kwargs.args) > 1

    def test_get_source_assignments_with_source_ids(self, er_client, source_assignments_response):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                200, source_assignments_response
            )
            result = er_client.get_source_assignments(
                source_ids=["123e4567-e89b-12d3-a456-426614174002"]
            )
            assert result == source_assignments_response["data"]

    def test_get_source_assignments_with_both_filters(self, er_client, source_assignments_response):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                200, source_assignments_response
            )
            result = er_client.get_source_assignments(
                subject_ids=["123e4567-e89b-12d3-a456-426614174001"],
                source_ids=["123e4567-e89b-12d3-a456-426614174002"],
            )
            assert result == source_assignments_response["data"]

    def test_get_source_assignments_not_found(self, er_client):
        with patch.object(er_client._http_session, 'get') as mock_get:
            mock_get.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.get_source_assignments()


# ---- sync post_subject tests (already existed, verify it works) ----

class TestPostSubject:
    def test_post_subject_success(self, er_client, subject_created_response):
        with patch.object(er_client._http_session, 'post') as mock_post:
            mock_post.return_value = _mock_response(
                201, subject_created_response
            )
            result = er_client.post_subject({
                "name": "Test Elephant",
                "subject_type": "wildlife",
                "subject_subtype": "elephant",
            })
            assert result == subject_created_response["data"]
            assert mock_post.called

    def test_post_subject_forbidden(self, er_client):
        with patch.object(er_client._http_session, 'post') as mock_post:
            mock_post.return_value = _mock_response(
                403, ok=False, text='{"status":{"detail":"forbidden"}}'
            )
            with pytest.raises(ERClientPermissionDenied):
                er_client.post_subject({"name": "Test"})


# ---- sync post_source tests (already existed, verify it works) ----

class TestPostSource:
    def test_post_source_success(self, er_client, source_created_response):
        with patch.object(er_client._http_session, 'post') as mock_post:
            mock_post.return_value = _mock_response(
                201, source_created_response
            )
            result = er_client.post_source({
                "manufacturer_id": "collar-9999",
                "source_type": "tracking-device",
            })
            assert result == source_created_response["data"]
            assert mock_post.called


# ---- sync delete_subject tests (already existed, verify it works) ----

class TestDeleteSubject:
    def test_delete_subject_success(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(204, ok=True)
            # delete_subject doesn't return a value; just verify no exception
            er_client.delete_subject("aabbccdd-1234-5678-9012-abcdefabcdef")
            assert mock_delete.called

    def test_delete_subject_not_found(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.delete_subject("nonexistent-id")


# ---- sync delete_source tests (already existed, verify it works) ----

class TestDeleteSource:
    def test_delete_source_success(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(204, ok=True)
            # delete_source doesn't return a value; just verify no exception
            er_client.delete_source("ee112233-4455-6677-8899-aabbccddeeff")
            assert mock_delete.called

    def test_delete_source_not_found(self, er_client):
        with patch.object(er_client._http_session, 'delete') as mock_delete:
            mock_delete.return_value = _mock_response(
                404, ok=False, text='{"status":{"detail":"not found"}}'
            )
            with pytest.raises(ERClientNotFound):
                er_client.delete_source("nonexistent-source-id")
