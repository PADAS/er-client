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


def test_retry_after_http_date_rounds_up_fractional_seconds():
    # A fractional delta must round up (never retry earlier than requested).
    # HTTP-dates have whole-second resolution, so the fraction comes from
    # "now" being mid-second — pin the clock to make this deterministic.
    from unittest import mock

    from erclient.client import parse_retry_after_header

    fixed_now = datetime(2026, 7, 6, 12, 0, 0, 500000, tzinfo=timezone.utc)
    retry_at = datetime(2026, 7, 6, 12, 2, 0,
                        tzinfo=timezone.utc)  # 119.5s later
    with mock.patch("erclient.client.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_now
        assert parse_retry_after_header(
            format_datetime(retry_at, usegmt=True)) == 120


def test_retry_after_http_date_in_past_is_none():
    from unittest import mock

    from erclient.client import parse_retry_after_header

    fixed_now = datetime(2026, 7, 6, 12, 0, 0, 500000, tzinfo=timezone.utc)
    retry_at = datetime(2026, 7, 6, 11, 59, 59,
                        tzinfo=timezone.utc)  # in the past
    with mock.patch("erclient.client.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_now
        assert parse_retry_after_header(
            format_datetime(retry_at, usegmt=True)) is None
