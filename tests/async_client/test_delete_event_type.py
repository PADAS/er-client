import httpx
import pytest
import respx

from erclient.er_errors import ERClientException, ERClientNotFound, ERClientPermissionDenied


@pytest.mark.asyncio
async def test_delete_event_type_success_v2(er_client):
    """delete_event_type() defaults to v2.0 and returns True on 204."""
    slug = "rainfall_rep"
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(base_url=api_root_v2, assert_all_called=False) as respx_mock:
        route = respx_mock.delete(f"activity/eventtypes/{slug}")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        result = await er_client.delete_event_type(slug)

        assert route.called
        await er_client.close()
        assert result is True


@pytest.mark.asyncio
async def test_delete_event_type_explicit_v2(er_client):
    """delete_event_type(version="v2.0") uses .../api/v2.0/activity/eventtypes/{slug}."""
    slug = "immobility_rep"
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(base_url=api_root_v2, assert_all_called=False) as respx_mock:
        route = respx_mock.delete(f"activity/eventtypes/{slug}")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        result = await er_client.delete_event_type(slug, version="v2.0")

        assert route.called
        await er_client.close()
        assert result is True


@pytest.mark.asyncio
async def test_delete_event_type_v1_uses_v1_path(er_client):
    """delete_event_type(version="v1.0") uses the v1.0 path."""
    slug = "some_event_type"
    api_root_v1 = er_client._api_root("v1.0")
    async with respx.mock(base_url=api_root_v1, assert_all_called=False) as respx_mock:
        route = respx_mock.delete(f"activity/events/eventtypes/{slug}")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        result = await er_client.delete_event_type(slug, version="v1.0")

        assert route.called
        await er_client.close()
        assert result is True


@pytest.mark.asyncio
async def test_delete_event_type_version_alias_v2(er_client):
    """delete_event_type(version="v2") alias is normalized to v2.0."""
    slug = "test_type"
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(base_url=api_root_v2, assert_all_called=False) as respx_mock:
        route = respx_mock.delete(f"activity/eventtypes/{slug}")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        result = await er_client.delete_event_type(slug, version="v2")

        assert route.called
        await er_client.close()
        assert result is True


@pytest.mark.asyncio
async def test_delete_event_type_not_found_raises(er_client):
    """delete_event_type() raises ERClientNotFound on 404."""
    slug = "nonexistent_type"
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(base_url=api_root_v2, assert_all_called=False) as respx_mock:
        route = respx_mock.delete(f"activity/eventtypes/{slug}")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"detail": "Not found."}
        )

        with pytest.raises(ERClientNotFound):
            await er_client.delete_event_type(slug)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_event_type_forbidden_raises(er_client):
    """delete_event_type() raises ERClientPermissionDenied on 403."""
    slug = "protected_type"
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(base_url=api_root_v2, assert_all_called=False) as respx_mock:
        route = respx_mock.delete(f"activity/eventtypes/{slug}")
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN,
            json={"status": {"detail": "You do not have permission to perform this action."}}
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.delete_event_type(slug)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_event_type_conflict_raises(er_client):
    """delete_event_type() raises ERClientException with detail on 409 Conflict."""
    slug = "in_use_type"
    conflict_detail = (
        "Cannot delete Event Type 'In Use Type' because it is associated "
        "with existing Events, and it is associated with existing Alert Rules."
    )
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(base_url=api_root_v2, assert_all_called=False) as respx_mock:
        route = respx_mock.delete(f"activity/eventtypes/{slug}")
        route.return_value = httpx.Response(
            httpx.codes.CONFLICT,
            json={"detail": conflict_detail}
        )

        with pytest.raises(ERClientException, match="Cannot delete"):
            await er_client.delete_event_type(slug)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_event_type_conflict_has_events_only(er_client):
    """409 with only events dependency surfaces the correct detail."""
    slug = "events_only_type"
    conflict_detail = (
        "Cannot delete Event Type 'Events Only' because it is associated "
        "with existing Events."
    )
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(base_url=api_root_v2, assert_all_called=False) as respx_mock:
        route = respx_mock.delete(f"activity/eventtypes/{slug}")
        route.return_value = httpx.Response(
            httpx.codes.CONFLICT,
            json={"detail": conflict_detail}
        )

        with pytest.raises(ERClientException, match="existing Events"):
            await er_client.delete_event_type(slug)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_event_type_server_error_raises(er_client):
    """delete_event_type() raises ERClientException on 500."""
    slug = "server_error_type"
    api_root_v2 = er_client._api_root("v2.0")
    async with respx.mock(base_url=api_root_v2, assert_all_called=False) as respx_mock:
        route = respx_mock.delete(f"activity/eventtypes/{slug}")
        route.return_value = httpx.Response(
            httpx.codes.INTERNAL_SERVER_ERROR,
            text="Internal Server Error"
        )

        with pytest.raises(ERClientException, match="Internal Server Error"):
            await er_client.delete_event_type(slug)

        assert route.called
        await er_client.close()
