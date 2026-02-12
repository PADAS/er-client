import json

import httpx
import pytest
import respx

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


# -- Success cases -----------------------------------------------------------

@pytest.mark.asyncio
async def test_get_events_export_returns_raw_response(er_client):
    """The method must return the raw httpx.Response so callers can stream
    or save the CSV body."""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/events/export/")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            content=CSV_BODY.encode(),
            headers={"Content-Type": "text/csv"},
        )

        response = await er_client.get_events_export()

        assert isinstance(response, httpx.Response)
        assert response.status_code == 200
        assert response.text == CSV_BODY
        assert route.called
    await er_client.close()


@pytest.mark.asyncio
async def test_get_events_export_with_filter(er_client):
    """When a filter is supplied it should be forwarded as a query parameter."""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/events/export/")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            content=CSV_BODY.encode(),
            headers={"Content-Type": "text/csv"},
        )

        event_filter = json.dumps(
            {"date_range": {"lower": "2024-01-01T00:00:00-06:00"}}
        )
        response = await er_client.get_events_export(filter=event_filter)

        assert response.status_code == 200
        # Verify the filter was passed as a param
        request = route.calls.last.request
        assert "filter" in str(request.url)
        assert route.called
    await er_client.close()


@pytest.mark.asyncio
async def test_get_events_export_without_filter(er_client):
    """Without a filter no 'filter' query param should be present."""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/events/export/")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            content=b"",
            headers={"Content-Type": "text/csv"},
        )

        response = await er_client.get_events_export()

        request = route.calls.last.request
        assert "filter" not in str(request.url)
        assert response.status_code == 200
    await er_client.close()


@pytest.mark.asyncio
async def test_get_events_export_content_type_is_csv(er_client):
    """Confirm the response preserves the Content-Type header."""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/events/export/")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            content=CSV_BODY.encode(),
            headers={
                "Content-Type": "text/csv",
                "Content-Disposition": "attachment; filename=events_export.csv",
            },
        )

        response = await er_client.get_events_export()

        assert "text/csv" in response.headers["content-type"]
        assert "events_export.csv" in response.headers["content-disposition"]
    await er_client.close()


# -- Error cases --------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_events_export_not_found(er_client):
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/events/export/")
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND,
            json={"status": {"code": 404, "detail": "Not found"}},
        )

        with pytest.raises(ERClientNotFound):
            await er_client.get_events_export()
    await er_client.close()


@pytest.mark.asyncio
async def test_get_events_export_forbidden(er_client):
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/events/export/")
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN,
            json={
                "status": {
                    "code": 403,
                    "detail": "You do not have permission to perform this action.",
                }
            },
        )

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_events_export()
    await er_client.close()


@pytest.mark.asyncio
async def test_get_events_export_bad_credentials(er_client):
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/events/export/")
        route.return_value = httpx.Response(
            httpx.codes.UNAUTHORIZED,
            json={
                "status": {
                    "code": 401,
                    "detail": "Authentication credentials were not provided.",
                }
            },
        )

        with pytest.raises(ERClientBadCredentials):
            await er_client.get_events_export()
    await er_client.close()


@pytest.mark.asyncio
async def test_get_events_export_server_error(er_client):
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/events/export/")
        route.return_value = httpx.Response(
            httpx.codes.INTERNAL_SERVER_ERROR,
            json={"detail": "Internal server error"},
        )

        with pytest.raises(ERClientException):
            await er_client.get_events_export()
    await er_client.close()


@pytest.mark.asyncio
async def test_get_events_export_url_construction(er_client):
    """The request should target the versioned API path activity/events/export/."""
    async with respx.mock(
        base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.get("activity/events/export/")
        route.return_value = httpx.Response(
            httpx.codes.OK,
            content=CSV_BODY.encode(),
            headers={"Content-Type": "text/csv"},
        )

        await er_client.get_events_export()

        request = route.calls.last.request
        assert "activity/events/export/" in str(request.url)
    await er_client.close()
