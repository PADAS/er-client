import pytest

from erclient.client import ERClient


@pytest.fixture
def er_server_info():
    return {
        "service_root": "https://fake-site.erdomain.org/api/v1.0",
        "username": "test",
        "password": "test",
        "token": "1110c87681cd1d12ad07c2d0f57d15d6079ae5d8",
        "token_url": "https://fake-auth.erdomain.org/oauth2/token",
        "client_id": "das_web_client",
        "provider_key": "testintegration",
    }


@pytest.fixture
def er_client(er_server_info):
    return ERClient(**er_server_info)
