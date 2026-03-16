import json

import httpx
import pytest
import pytest_asyncio
import respx

from erclient import (ERClientBadCredentials, ERClientInternalError,
                      ERClientNotFound, ERClientPermissionDenied)

GROUP_ID = "ac1413b9-8177-4a81-85d6-a46fc95bdd70"
SUBJECT_ID = "1fed139e-070d-464c-9652-e9420437b068"
SUBJECTS_PAYLOAD = [{"id": SUBJECT_ID}]


@pytest.fixture
def subjectgroup_subjects_response():
    return [{"id": SUBJECT_ID, "name": "MMVessel"}]


@pytest_asyncio.fixture(autouse=True)
async def close_client(er_client):
    yield
    await er_client.close()


@pytest.mark.asyncio
async def test_add_subjects_to_subjectgroup_success(er_client, subjectgroup_subjects_response):
    """Test successful subject assignment to a subject group."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'subjectgroup/{GROUP_ID}/subjects/')
        route.return_value = httpx.Response(
            httpx.codes.OK, json=subjectgroup_subjects_response
        )

        result = await er_client.add_subjects_to_subjectgroup(
            group_id=GROUP_ID,
            subjects=SUBJECTS_PAYLOAD,
        )

        assert result == subjectgroup_subjects_response
        assert route.called


@pytest.mark.asyncio
async def test_add_subjects_to_subjectgroup_not_found(er_client):
    """Test 404 raises ERClientNotFound."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'subjectgroup/{GROUP_ID}/subjects/')
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.add_subjects_to_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        assert route.called


@pytest.mark.asyncio
async def test_add_subjects_to_subjectgroup_bad_credentials(er_client):
    """Test 401 raises ERClientBadCredentials."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'subjectgroup/{GROUP_ID}/subjects/')
        route.return_value = httpx.Response(httpx.codes.UNAUTHORIZED, json={})

        with pytest.raises(ERClientBadCredentials):
            await er_client.add_subjects_to_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        assert route.called


@pytest.mark.asyncio
async def test_add_subjects_to_subjectgroup_permission_denied(er_client):
    """Test 403 raises ERClientPermissionDenied."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'subjectgroup/{GROUP_ID}/subjects/')
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.add_subjects_to_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        assert route.called


@pytest.mark.asyncio
async def test_add_subjects_to_subjectgroup_internal_error(er_client):
    """Test 500 raises ERClientInternalError."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'subjectgroup/{GROUP_ID}/subjects/')
        route.return_value = httpx.Response(
            httpx.codes.INTERNAL_SERVER_ERROR, json={})

        with pytest.raises(ERClientInternalError):
            await er_client.add_subjects_to_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        assert route.called


@pytest.mark.asyncio
async def test_remove_subjects_from_subjectgroup_success(er_client):
    """Test successful removal of subjects from a subject group."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'subjectgroup/{GROUP_ID}/subjects/')
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        result = await er_client.remove_subjects_from_subjectgroup(
            group_id=GROUP_ID,
            subjects=SUBJECTS_PAYLOAD,
        )

        assert result is True
        assert route.called
        assert json.loads(route.calls.last.request.content) == SUBJECTS_PAYLOAD


@pytest.mark.asyncio
async def test_remove_subjects_from_subjectgroup_not_found(er_client):
    """Test 404 raises ERClientNotFound."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'subjectgroup/{GROUP_ID}/subjects/')
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={})

        with pytest.raises(ERClientNotFound):
            await er_client.remove_subjects_from_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        assert route.called


@pytest.mark.asyncio
async def test_remove_subjects_from_subjectgroup_permission_denied(er_client):
    """Test 403 raises ERClientPermissionDenied."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'subjectgroup/{GROUP_ID}/subjects/')
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={})

        with pytest.raises(ERClientPermissionDenied):
            await er_client.remove_subjects_from_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        assert route.called


@pytest.mark.asyncio
async def test_remove_subjects_from_subjectgroup_internal_error(er_client):
    """Test 500 raises ERClientInternalError."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'subjectgroup/{GROUP_ID}/subjects/')
        route.return_value = httpx.Response(
            httpx.codes.INTERNAL_SERVER_ERROR, json={})

        with pytest.raises(ERClientInternalError):
            await er_client.remove_subjects_from_subjectgroup(
                group_id=GROUP_ID,
                subjects=SUBJECTS_PAYLOAD,
            )

        assert route.called
