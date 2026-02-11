import httpx
import pytest
import respx

from erclient import ERClientNotFound, ERClientPermissionDenied


# -- Fixtures --

@pytest.fixture
def user_response():
    return {
        "id": "c925e69e-51cf-43d0-b659-2000ae023664",
        "username": "ranger01",
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.org",
        "is_active": True,
    }


@pytest.fixture
def users_list_response(user_response):
    return [user_response]


@pytest.fixture
def user_profiles_response():
    return [
        {
            "id": "prof-001",
            "user": "c925e69e-51cf-43d0-b659-2000ae023664",
            "role": "ranger",
        }
    ]


@pytest.fixture
def eula_response():
    return {
        "id": "eula-001",
        "version": "2.0",
        "eula_url": "https://example.org/eula",
        "active": True,
    }


@pytest.fixture
def eula_accept_response():
    return {
        "accepted": True,
        "eula": "eula-001",
    }


# -- get_users --

@pytest.mark.asyncio
async def test_get_users(er_client, users_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("users")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": users_list_response})
        result = await er_client.get_users()
        assert route.called
        assert result == users_list_response
        await er_client.close()


# -- get_user --

@pytest.mark.asyncio
async def test_get_user(er_client, user_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("user/c925e69e-51cf-43d0-b659-2000ae023664")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": user_response})
        result = await er_client.get_user("c925e69e-51cf-43d0-b659-2000ae023664")
        assert route.called
        assert result == user_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_user_me(er_client, user_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("user/me")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": user_response})
        result = await er_client.get_user("me")
        assert route.called
        assert result == user_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_user_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("user/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.get_user("nonexistent")
        await er_client.close()


# -- patch_user --

@pytest.mark.asyncio
async def test_patch_user(er_client, user_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.patch("user/c925e69e-51cf-43d0-b659-2000ae023664")
        updated = {**user_response, "first_name": "Updated"}
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": updated})
        result = await er_client.patch_user("c925e69e-51cf-43d0-b659-2000ae023664", {"first_name": "Updated"})
        assert route.called
        assert result["first_name"] == "Updated"
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_user_forbidden(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.patch("user/c925e69e-51cf-43d0-b659-2000ae023664")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={"status": {"code": 403}})
        with pytest.raises(ERClientPermissionDenied):
            await er_client.patch_user("c925e69e-51cf-43d0-b659-2000ae023664", {"first_name": "x"})
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_user_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.patch("user/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.patch_user("nonexistent", {"first_name": "x"})
        await er_client.close()


# -- get_user_profiles --

@pytest.mark.asyncio
async def test_get_user_profiles(er_client, user_profiles_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("user/c925e69e-51cf-43d0-b659-2000ae023664/profiles")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": user_profiles_response})
        result = await er_client.get_user_profiles("c925e69e-51cf-43d0-b659-2000ae023664")
        assert route.called
        assert result == user_profiles_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_user_profiles_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("user/nonexistent/profiles")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.get_user_profiles("nonexistent")
        await er_client.close()


# -- get_eula --

@pytest.mark.asyncio
async def test_get_eula(er_client, eula_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("user/eula")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": eula_response})
        result = await er_client.get_eula()
        assert route.called
        assert result == eula_response
        await er_client.close()


# -- accept_eula --

@pytest.mark.asyncio
async def test_accept_eula(er_client, eula_accept_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.post("user/eula/accept")
        route.return_value = httpx.Response(httpx.codes.CREATED, json={"data": eula_accept_response})
        result = await er_client.accept_eula()
        assert route.called
        assert result == eula_accept_response
        await er_client.close()


@pytest.mark.asyncio
async def test_accept_eula_forbidden(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.post("user/eula/accept")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={"status": {"code": 403}})
        with pytest.raises(ERClientPermissionDenied):
            await er_client.accept_eula()
        await er_client.close()
