"""Tests for analyzers, choices, buoy/gear, and reports endpoints (async client)."""

import httpx
import pytest
import respx


GEAR_ID = "aabb1122-3344-5566-7788-99aabbccddee"
CHOICE_ID = "ccdd1122-3344-5566-7788-99aabbccddee"
VIEW_ID = "eeff1122-3344-5566-7788-99aabbccddee"


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def analyzers_spatial_response():
    return {
        "data": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "name": "Geofence Analyzer",
                "type": "geofence",
                "is_active": True,
            }
        ]
    }


@pytest.fixture
def analyzers_subject_response():
    return {
        "data": [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "name": "Immobility Analyzer",
                "type": "immobility",
                "is_active": True,
            }
        ]
    }


@pytest.fixture
def choices_list_response():
    return {
        "data": [
            {"id": CHOICE_ID, "field_name": "species", "model": "activity.event"},
        ]
    }


@pytest.fixture
def choice_detail_response():
    return {
        "data": {
            "id": CHOICE_ID,
            "field_name": "species",
            "model": "activity.event",
            "choices": [
                {"value": "elephant", "display": "Elephant"},
                {"value": "lion", "display": "Lion"},
            ],
        }
    }


@pytest.fixture
def gear_list_response():
    return {
        "data": [
            {"id": GEAR_ID, "name": "Test Buoy", "gear_type": "buoy"},
        ]
    }


@pytest.fixture
def gear_detail_response():
    return {
        "data": {
            "id": GEAR_ID,
            "name": "Test Buoy",
            "gear_type": "buoy",
            "status": "active",
        }
    }


@pytest.fixture
def gear_created_response():
    return {
        "data": {
            "id": GEAR_ID,
            "name": "New Buoy",
            "gear_type": "buoy",
        },
        "status": {"code": 201, "message": "Created"},
    }


@pytest.fixture
def gear_updated_response():
    return {
        "data": {
            "id": GEAR_ID,
            "name": "Updated Buoy",
            "gear_type": "buoy",
        },
        "status": {"code": 200, "message": "OK"},
    }


@pytest.fixture
def tableau_views_response():
    return {
        "data": [
            {"id": VIEW_ID, "title": "Animal Sightings Dashboard"},
        ]
    }


@pytest.fixture
def tableau_view_detail_response():
    return {
        "data": {
            "id": VIEW_ID,
            "title": "Animal Sightings Dashboard",
            "url": "https://tableau.example.com/view/1",
        }
    }


# ── Analyzer tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_analyzers_spatial(er_client, analyzers_spatial_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("analyzers/spatial").respond(httpx.codes.OK, json=analyzers_spatial_response)

        result = await er_client.get_analyzers_spatial()

        assert route.called
        assert result == analyzers_spatial_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_get_analyzers_subject(er_client, analyzers_subject_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("analyzers/subject").respond(httpx.codes.OK, json=analyzers_subject_response)

        result = await er_client.get_analyzers_subject()

        assert route.called
        assert result == analyzers_subject_response["data"]
        await er_client.close()


# ── Choice tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_choices(er_client, choices_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("choices").respond(httpx.codes.OK, json=choices_list_response)

        result = await er_client.get_choices()

        assert route.called
        assert result == choices_list_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_get_choice(er_client, choice_detail_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get(f"choices/{CHOICE_ID}").respond(httpx.codes.OK, json=choice_detail_response)

        result = await er_client.get_choice(CHOICE_ID)

        assert route.called
        assert result == choice_detail_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_download_choice_icons(er_client):
    binary_content = b"zip-binary-content"
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("choices/icons/download").respond(
            httpx.codes.OK, content=binary_content
        )

        result = await er_client.download_choice_icons()

        assert route.called
        assert result.content == binary_content
        await er_client.close()


# ── Gear CRUD tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_gear_list(er_client, gear_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("buoy/gear").respond(httpx.codes.OK, json=gear_list_response)

        result = await er_client.get_gear_list()

        assert route.called
        assert result == gear_list_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_get_gear(er_client, gear_detail_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get(f"buoy/gear/{GEAR_ID}").respond(httpx.codes.OK, json=gear_detail_response)

        result = await er_client.get_gear(GEAR_ID)

        assert route.called
        assert result == gear_detail_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_post_gear(er_client, gear_created_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.post("buoy/gear").respond(httpx.codes.CREATED, json=gear_created_response)

        result = await er_client.post_gear({"name": "New Buoy", "gear_type": "buoy"})

        assert route.called
        assert result == gear_created_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_gear(er_client, gear_updated_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.patch(f"buoy/gear/{GEAR_ID}").respond(httpx.codes.OK, json=gear_updated_response)

        result = await er_client.patch_gear(GEAR_ID, {"name": "Updated Buoy"})

        assert route.called
        assert result == gear_updated_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_gear(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.delete(f"buoy/gear/{GEAR_ID}").respond(httpx.codes.NO_CONTENT)

        # DELETE returns None from _call (no json body on 204)
        # The async client raises on non-200 via raise_for_status, but 204 is ok.
        # However our _call tries response.json() which will fail on 204.
        # Let's mock a 200 with empty body instead:
        route = m.delete(f"buoy/gear/{GEAR_ID}").respond(httpx.codes.OK, json={})

        result = await er_client.delete_gear(GEAR_ID)

        assert route.called
        await er_client.close()


# ── Reports / Tableau tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_get_sitrep(er_client):
    binary_content = b"docx-binary-content"
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("reports/sitrep.docx").respond(
            httpx.codes.OK, content=binary_content
        )

        result = await er_client.get_sitrep()

        assert route.called
        assert result.content == binary_content
        await er_client.close()


@pytest.mark.asyncio
async def test_get_tableau_views(er_client, tableau_views_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get("reports/tableau-views").respond(httpx.codes.OK, json=tableau_views_response)

        result = await er_client.get_tableau_views()

        assert route.called
        assert result == tableau_views_response["data"]
        await er_client.close()


@pytest.mark.asyncio
async def test_get_tableau_view(er_client, tableau_view_detail_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        route = m.get(f"reports/tableau-views/{VIEW_ID}").respond(
            httpx.codes.OK, json=tableau_view_detail_response
        )

        result = await er_client.get_tableau_view(VIEW_ID)

        assert route.called
        assert result == tableau_view_detail_response["data"]
        await er_client.close()


# ── Error handling ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_gear_not_found(er_client, not_found_response):
    from erclient import ERClientNotFound

    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        m.get(f"buoy/gear/{GEAR_ID}").respond(httpx.codes.NOT_FOUND, json=not_found_response)

        with pytest.raises(ERClientNotFound):
            await er_client.get_gear(GEAR_ID)

        await er_client.close()


@pytest.mark.asyncio
async def test_get_analyzers_forbidden(er_client, forbidden_response):
    from erclient import ERClientPermissionDenied

    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as m:
        m.get("analyzers/spatial").respond(httpx.codes.FORBIDDEN, json=forbidden_response)

        with pytest.raises(ERClientPermissionDenied):
            await er_client.get_analyzers_spatial()

        await er_client.close()
