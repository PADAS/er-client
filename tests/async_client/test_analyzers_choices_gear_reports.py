import httpx
import pytest
import respx

from erclient import ERClientNotFound, ERClientPermissionDenied


# -- Fixtures --

@pytest.fixture
def spatial_analyzers_response():
    return [{"id": "sa-001", "name": "Geofence Analyzer", "type": "spatial"}]


@pytest.fixture
def subject_analyzers_response():
    return [{"id": "sub-001", "name": "Immobility Analyzer", "type": "subject"}]


@pytest.fixture
def choices_list_response():
    return [
        {"id": "ch-001", "name": "Species", "values": ["Lion", "Elephant"]},
        {"id": "ch-002", "name": "Status", "values": ["Active", "Inactive"]},
    ]


@pytest.fixture
def choice_detail_response():
    return {"id": "ch-001", "name": "Species", "values": ["Lion", "Elephant"]}


@pytest.fixture
def gear_list_response():
    return [
        {"id": "gear-001", "name": "Buoy Alpha", "status": "deployed"},
        {"id": "gear-002", "name": "Buoy Beta", "status": "stored"},
    ]


@pytest.fixture
def gear_detail_response():
    return {"id": "gear-001", "name": "Buoy Alpha", "status": "deployed"}


@pytest.fixture
def gear_payload():
    return {"name": "New Buoy", "status": "stored"}


@pytest.fixture
def gear_created_response():
    return {"id": "gear-003", "name": "New Buoy", "status": "stored"}


@pytest.fixture
def tableau_views_list_response():
    return [
        {"id": "tv-001", "title": "Wildlife Overview"},
        {"id": "tv-002", "title": "Patrol Coverage"},
    ]


@pytest.fixture
def tableau_view_detail_response():
    return {"id": "tv-001", "title": "Wildlife Overview", "url": "https://tableau.example.com/view1"}


# -- Analyzer tests --

@pytest.mark.asyncio
async def test_get_analyzers_spatial(er_client, spatial_analyzers_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("analyzers/spatial")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": spatial_analyzers_response})
        result = await er_client.get_analyzers_spatial()
        assert route.called
        assert result == spatial_analyzers_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_analyzers_subject(er_client, subject_analyzers_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("analyzers/subject")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": subject_analyzers_response})
        result = await er_client.get_analyzers_subject()
        assert route.called
        assert result == subject_analyzers_response
        await er_client.close()


# -- Choices tests --

@pytest.mark.asyncio
async def test_get_choices(er_client, choices_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("choices")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": choices_list_response})
        result = await er_client.get_choices()
        assert route.called
        assert result == choices_list_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_choice(er_client, choice_detail_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("choices/ch-001")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": choice_detail_response})
        result = await er_client.get_choice("ch-001")
        assert route.called
        assert result == choice_detail_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_choice_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("choices/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.get_choice("nonexistent")
        assert route.called
        await er_client.close()


# -- Gear CRUD tests --

@pytest.mark.asyncio
async def test_get_gear(er_client, gear_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("buoy/gear")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": gear_list_response})
        result = await er_client.get_gear()
        assert route.called
        assert result == gear_list_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_gear_item(er_client, gear_detail_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("buoy/gear/gear-001")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": gear_detail_response})
        result = await er_client.get_gear_item("gear-001")
        assert route.called
        assert result == gear_detail_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_gear_item_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("buoy/gear/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.get_gear_item("nonexistent")
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_gear(er_client, gear_payload, gear_created_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.post("buoy/gear")
        route.return_value = httpx.Response(httpx.codes.CREATED, json={"data": gear_created_response})
        result = await er_client.post_gear(gear_payload)
        assert route.called
        assert result == gear_created_response
        await er_client.close()


@pytest.mark.asyncio
async def test_post_gear_forbidden(er_client, gear_payload):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.post("buoy/gear")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={"status": {"code": 403}})
        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_gear(gear_payload)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_gear(er_client, gear_detail_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.patch("buoy/gear/gear-001")
        updated = {**gear_detail_response, "name": "Updated Buoy"}
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": updated})
        result = await er_client.patch_gear("gear-001", {"name": "Updated Buoy"})
        assert route.called
        assert result["name"] == "Updated Buoy"
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_gear_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.patch("buoy/gear/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.patch_gear("nonexistent", {"name": "x"})
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_gear(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.delete("buoy/gear/gear-001/")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)
        result = await er_client.delete_gear("gear-001")
        assert route.called
        assert result is None
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_gear_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.delete("buoy/gear/nonexistent/")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.delete_gear("nonexistent")
        assert route.called
        await er_client.close()


# -- Reports / Tableau tests --

@pytest.mark.asyncio
async def test_get_tableau_views(er_client, tableau_views_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("reports/tableau-views")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": tableau_views_list_response})
        result = await er_client.get_tableau_views()
        assert route.called
        assert result == tableau_views_list_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_tableau_view(er_client, tableau_view_detail_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("reports/tableau-views/tv-001")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": tableau_view_detail_response})
        result = await er_client.get_tableau_view("tv-001")
        assert route.called
        assert result == tableau_view_detail_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_tableau_view_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("reports/tableau-views/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.get_tableau_view("nonexistent")
        assert route.called
        await er_client.close()
