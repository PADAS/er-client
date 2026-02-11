import json
from unittest.mock import MagicMock

import pytest
import requests

from erclient.client import ERClient


def _mock_response(status_code, json_data=None, text=None, ok=None, url="https://fake-site.erdomain.org/api/v1.0/mock"):
    """Create a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.url = url
    if json_data is not None:
        resp.text = json.dumps(json_data)
        resp.json.return_value = json_data
    elif text is not None:
        resp.text = text
    else:
        resp.text = ""
    if ok is not None:
        resp.ok = ok
    else:
        resp.ok = 200 <= status_code < 300
    return resp


@pytest.fixture
def er_client():
    return ERClient(
        service_root="https://fake-site.erdomain.org/api/v1.0",
        username="test",
        password="test",
        token="1110c87681cd1d12ad07c2d0f57d15d6079ae5d8",
        token_url="https://fake-auth.erdomain.org/oauth2/token",
        client_id="das_web_client",
        provider_key="testintegration",
    )
