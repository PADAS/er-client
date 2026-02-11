import httpx
import pytest
import respx


@pytest.mark.asyncio
async def test_get_event_basic(er_client, report_created_response):
    """get_event returns event data for a valid event_id."""
    event_id = "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f"

    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f'activity/event/{event_id}')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=report_created_response
        )

        result = await er_client.get_event(event_id=event_id)

        assert result is not None
        assert result["id"] == event_id
        assert result["event_type"] == "rainfall_rep"
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_with_all_includes(er_client, report_created_response):
    """get_event passes all include flags as query params."""
    event_id = "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f"

    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f'activity/event/{event_id}')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=report_created_response
        )

        result = await er_client.get_event(
            event_id=event_id,
            include_details=True,
            include_updates=True,
            include_notes=True,
            include_related_events=True,
            include_files=True,
        )

        assert result is not None
        # Verify the request was made with query params
        request = route.calls[0].request
        assert "include_details" in str(request.url)
        assert "include_updates" in str(request.url)
        assert "include_notes" in str(request.url)
        assert "include_related_events" in str(request.url)
        assert "include_files" in str(request.url)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_default_params(er_client, report_created_response):
    """get_event sends correct default query parameters."""
    event_id = "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f"

    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f'activity/event/{event_id}')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=report_created_response
        )

        await er_client.get_event(event_id=event_id)

        request = route.calls[0].request
        url_str = str(request.url)
        # include_details defaults to True
        assert "include_details=True" in url_str or "include_details=true" in url_str
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_not_found(er_client, not_found_response):
    """get_event raises ERClientNotFound for 404 responses."""
    from erclient.er_errors import ERClientNotFound

    event_id = "00000000-0000-0000-0000-000000000000"

    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f'activity/event/{event_id}')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json=not_found_response
        )

        with pytest.raises(ERClientNotFound):
            await er_client.get_event(event_id=event_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_unauthorized(er_client, bad_credentials_response):
    """get_event raises ERClientBadCredentials for 401 responses."""
    from erclient.er_errors import ERClientBadCredentials

    event_id = "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f"

    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f'activity/event/{event_id}')
        route.return_value = httpx.Response(
            httpx.codes.UNAUTHORIZED,
            json=bad_credentials_response
        )

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_event(event_id=event_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_forbidden(er_client, forbidden_response):
    """get_event raises ERClientPermissionDenied for 403 responses."""
    from erclient.er_errors import ERClientPermissionDenied

    event_id = "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f"

    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f'activity/event/{event_id}')
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN,
            json=forbidden_response
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_event(event_id=event_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_event_includes_event_details(er_client, report_created_response):
    """get_event response includes event_details."""
    event_id = "9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f"

    async with respx.mock(
            base_url=er_client.service_root, assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get(f'activity/event/{event_id}')
        route.return_value = httpx.Response(
            httpx.codes.OK,
            json=report_created_response
        )

        result = await er_client.get_event(event_id=event_id, include_details=True)

        assert "event_details" in result
        assert result["event_details"]["height_m"] == 5
        assert route.called
        await er_client.close()
