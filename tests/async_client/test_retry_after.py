from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
import respx

from erclient import ERClientRateLimitExceeded, ERClientServiceUnreachable


@pytest.mark.asyncio
async def test_retry_after_seconds_on_429(er_client, report):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('activity/events')
        route.return_value = httpx.Response(
            httpx.codes.TOO_MANY_REQUESTS, headers={"Retry-After": "60"}, json={})

        with pytest.raises(ERClientRateLimitExceeded) as exc_info:
            await er_client.post_report(report)

        assert route.called
        assert exc_info.value.retry_after == 60
        await er_client.close()


@pytest.mark.asyncio
async def test_retry_after_http_date_on_503(er_client, report):
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=120)
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('activity/events')
        route.return_value = httpx.Response(
            httpx.codes.SERVICE_UNAVAILABLE,
            headers={"Retry-After": format_datetime(retry_at, usegmt=True)},
            json={}
        )

        with pytest.raises(ERClientServiceUnreachable) as exc_info:
            await er_client.post_report(report)

        assert route.called
        assert exc_info.value.retry_after is not None
        assert 100 <= exc_info.value.retry_after <= 120
        await er_client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [{}, {"Retry-After": "soonish"}, {"Retry-After": "-5"}])
async def test_retry_after_absent_or_unparseable_is_none(er_client, report, headers):
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('activity/events')
        route.return_value = httpx.Response(
            httpx.codes.TOO_MANY_REQUESTS, headers=headers, json={})

        with pytest.raises(ERClientRateLimitExceeded) as exc_info:
            await er_client.post_report(report)

        assert route.called
        assert exc_info.value.retry_after is None
        await er_client.close()
