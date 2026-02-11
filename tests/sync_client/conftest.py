import json
from unittest.mock import MagicMock

import pytest

from erclient.client import ERClient


def _mock_response(status_code, json_data=None, text=None, ok=None):
    """Create a mock requests.Response-like object."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = ok if ok is not None else (200 <= status_code < 300)
    if json_data is not None:
        mock.json.return_value = json_data
        mock.text = json.dumps(json_data)
    elif text is not None:
        mock.text = text
    else:
        mock.text = ""
    return mock


@pytest.fixture
def er_server_info():
    return {
        "service_root": "https://fake-site.erdomain.org/api/v1.0",
        "token": "1110c87681cd1d12ad07c2d0f57d15d6079ae5d8",
    }


@pytest.fixture
def er_client(er_server_info):
    return ERClient(**er_server_info)
