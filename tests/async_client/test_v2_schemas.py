import httpx
import pytest
import respx

from erclient import ERClientNotFound, ERClientPermissionDenied


SCHEMA_NAMES = ['users', 'sources', 'subjects', 'choices', 'spatial_features', 'event_types']


@pytest.fixture
def sample_schema():
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Users",
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "username": {"type": "string"},
            "email": {"type": "string", "format": "email"},
        },
        "required": ["username"],
    }


@pytest.mark.asyncio
async def test_get_schema_generic(er_client, sample_schema):
    """Test the generic get_schema() method with an arbitrary schema name."""
    v2_root = er_client.service_root.replace('/api/v1.0', '/api/v2.0')
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"{v2_root}/schemas/users.json")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": sample_schema})
        result = await er_client.get_schema('users')
        assert route.called
        assert result == sample_schema
        await er_client.close()


@pytest.mark.asyncio
async def test_get_schema_not_found(er_client):
    """Test that a 404 for a non-existent schema raises ERClientNotFound."""
    v2_root = er_client.service_root.replace('/api/v1.0', '/api/v2.0')
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"{v2_root}/schemas/nonexistent.json")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.get_schema('nonexistent')
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_schema_forbidden(er_client):
    """Test that a 403 for a schema endpoint raises ERClientPermissionDenied."""
    v2_root = er_client.service_root.replace('/api/v1.0', '/api/v2.0')
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"{v2_root}/schemas/users.json")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={"status": {"code": 403}})
        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_schema('users')
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_users_schema(er_client, sample_schema):
    v2_root = er_client.service_root.replace('/api/v1.0', '/api/v2.0')
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"{v2_root}/schemas/users.json")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": sample_schema})
        result = await er_client.get_users_schema()
        assert route.called
        assert result == sample_schema
        await er_client.close()


@pytest.mark.asyncio
async def test_get_sources_schema(er_client, sample_schema):
    v2_root = er_client.service_root.replace('/api/v1.0', '/api/v2.0')
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"{v2_root}/schemas/sources.json")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": sample_schema})
        result = await er_client.get_sources_schema()
        assert route.called
        assert result == sample_schema
        await er_client.close()


@pytest.mark.asyncio
async def test_get_subjects_schema(er_client, sample_schema):
    v2_root = er_client.service_root.replace('/api/v1.0', '/api/v2.0')
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"{v2_root}/schemas/subjects.json")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": sample_schema})
        result = await er_client.get_subjects_schema()
        assert route.called
        assert result == sample_schema
        await er_client.close()


@pytest.mark.asyncio
async def test_get_choices_schema(er_client, sample_schema):
    v2_root = er_client.service_root.replace('/api/v1.0', '/api/v2.0')
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"{v2_root}/schemas/choices.json")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": sample_schema})
        result = await er_client.get_choices_schema()
        assert route.called
        assert result == sample_schema
        await er_client.close()


@pytest.mark.asyncio
async def test_get_spatial_features_schema(er_client, sample_schema):
    v2_root = er_client.service_root.replace('/api/v1.0', '/api/v2.0')
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"{v2_root}/schemas/spatial_features.json")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": sample_schema})
        result = await er_client.get_spatial_features_schema()
        assert route.called
        assert result == sample_schema
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_types_schema(er_client, sample_schema):
    v2_root = er_client.service_root.replace('/api/v1.0', '/api/v2.0')
    async with respx.mock(assert_all_called=False) as respx_mock:
        route = respx_mock.get(f"{v2_root}/schemas/event_types.json")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": sample_schema})
        result = await er_client.get_event_types_schema()
        assert route.called
        assert result == sample_schema
        await er_client.close()
