import httpx
import pytest
import respx

from erclient import (ERClientBadCredentials, ERClientException,
                      ERClientNotFound, ERClientPermissionDenied)


@pytest.fixture
def subjects_list_response():
    """Sample response for subjects list"""
    return {
        "data": [
            {
                "id": "d8ad9955-8301-43c4-9000-9a02f1cba675",
                "name": "Elephant Alpha",
                "subject_type": "wildlife",
                "subject_subtype": "elephant",
                "is_active": True,
                "additional": {},
                "created_at": "2025-01-10T03:36:26.383023-08:00",
                "updated_at": "2025-01-10T04:07:31.700216-08:00",
                "tracks_available": True,
                "image_url": "/static/elephant-black.svg",
                "url": "https://fake-site.erdomain.org/api/v1.0/subject/d8ad9955-8301-43c4-9000-9a02f1cba675",
            },
            {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "name": "Rhino Beta",
                "subject_type": "wildlife",
                "subject_subtype": "rhino",
                "is_active": True,
                "additional": {},
                "created_at": "2025-02-15T10:00:00-08:00",
                "updated_at": "2025-02-15T10:00:00-08:00",
                "tracks_available": False,
                "image_url": "/static/rhino-black.svg",
                "url": "https://fake-site.erdomain.org/api/v1.0/subject/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            },
        ],
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def empty_subjects_response():
    return {
        "data": [],
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def subject_detail_response():
    """Sample response for a single subject"""
    return {
        "data": {
            "id": "d8ad9955-8301-43c4-9000-9a02f1cba675",
            "name": "Elephant Alpha",
            "subject_type": "wildlife",
            "subject_subtype": "elephant",
            "is_active": True,
            "additional": {},
            "created_at": "2025-01-10T03:36:26.383023-08:00",
            "updated_at": "2025-01-10T04:07:31.700216-08:00",
            "tracks_available": True,
            "image_url": "/static/elephant-black.svg",
            "last_position_date": "2025-03-01T12:00:00+00:00",
            "last_position": {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [36.8, -1.3]},
                "properties": {
                    "title": "Elephant Alpha",
                    "subject_type": "wildlife",
                    "subject_subtype": "elephant",
                    "id": "d8ad9955-8301-43c4-9000-9a02f1cba675",
                },
            },
            "url": "https://fake-site.erdomain.org/api/v1.0/subject/d8ad9955-8301-43c4-9000-9a02f1cba675",
        },
        "status": {"code": 200, "message": "OK"},
    }


# ---- get_subjects() tests ----


@pytest.mark.asyncio
async def test_get_subjects_success(er_client, subjects_list_response):
    """Test get_subjects returns list of subjects"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("subjects")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subjects_list_response
        )

        result = await er_client.get_subjects()

        assert result == subjects_list_response["data"]
        assert len(result) == 2
        assert result[0]["name"] == "Elephant Alpha"
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_empty(er_client, empty_subjects_response):
    """Test get_subjects returns empty list"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("subjects")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=empty_subjects_response
        )

        result = await er_client.get_subjects()

        assert result == []
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_with_params(er_client, subjects_list_response):
    """Test get_subjects passes query params correctly"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("subjects")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subjects_list_response
        )

        result = await er_client.get_subjects(
            subject_group="abc-123", include_inactive=True
        )

        assert result == subjects_list_response["data"]
        assert route.called
        # Verify params were passed
        request = route.calls.last.request
        assert b"subject_group=abc-123" in request.url.query
        assert b"include_inactive=true" in request.url.query
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_ignores_unknown_params(er_client, subjects_list_response):
    """Test get_subjects ignores params not in the allowed set"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("subjects")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subjects_list_response
        )

        result = await er_client.get_subjects(bogus_param="should_be_ignored")

        assert result == subjects_list_response["data"]
        assert route.called
        request = route.calls.last.request
        assert b"bogus_param" not in request.url.query
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_unauthorized(er_client):
    """Test get_subjects raises ERClientBadCredentials on 401"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("subjects")
        route.return_value = httpx.Response(httpx.codes.UNAUTHORIZED, json={})

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_subjects()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_forbidden(er_client):
    """Test get_subjects raises ERClientPermissionDenied on 403"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("subjects")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_subjects()

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_network_error(er_client):
    """Test get_subjects raises ERClientException on network error"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("subjects")
        route.side_effect = httpx.ConnectTimeout

        with pytest.raises(ERClientException):
            await er_client.get_subjects()

        assert route.called
        await er_client.close()


# ---- get_subject() tests ----


@pytest.mark.asyncio
async def test_get_subject_success(er_client, subject_detail_response):
    """Test get_subject returns a single subject"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}")
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subject_detail_response
        )

        result = await er_client.get_subject(subject_id)

        assert result == subject_detail_response["data"]
        assert result["id"] == subject_id
        assert result["name"] == "Elephant Alpha"
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_not_found(er_client):
    """Test get_subject raises ERClientNotFound on 404"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        subject_id = "nonexistent-id"
        route = respx_mock.get(f"subject/{subject_id}")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.get_subject(subject_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_unauthorized(er_client):
    """Test get_subject raises ERClientBadCredentials on 401"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}")
        route.return_value = httpx.Response(httpx.codes.UNAUTHORIZED, json={})

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_subject(subject_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_forbidden(er_client):
    """Test get_subject raises ERClientPermissionDenied on 403"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_subject(subject_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subject_network_error(er_client):
    """Test get_subject raises ERClientException on network error"""
    async with respx.mock(
        base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        subject_id = "d8ad9955-8301-43c4-9000-9a02f1cba675"
        route = respx_mock.get(f"subject/{subject_id}")
        route.side_effect = httpx.ReadTimeout

        with pytest.raises(ERClientException):
            await er_client.get_subject(subject_id)

        assert route.called
        await er_client.close()
