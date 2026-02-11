import httpx
import pytest
import respx

from erclient import ERClientNotFound, ERClientPermissionDenied


# -- Fixtures --

@pytest.fixture
def feature_response():
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [36.79, -1.29]},
        "properties": {"name": "Ranger Post Alpha", "id": "fp-001"},
    }


@pytest.fixture
def features_list_response(feature_response):
    return [feature_response]


@pytest.fixture
def featureset_response():
    return {
        "id": "fs-001",
        "name": "Ranger Posts",
        "type": "FeatureCollection",
        "features": [],
    }


@pytest.fixture
def featuresets_list_response(featureset_response):
    return [featureset_response]


@pytest.fixture
def map_response():
    return {
        "id": "map-001",
        "title": "Park Overview",
        "layers": [],
    }


@pytest.fixture
def maps_list_response(map_response):
    return [map_response]


@pytest.fixture
def layer_response():
    return {
        "id": "layer-001",
        "title": "Roads",
        "type": "geojson",
    }


@pytest.fixture
def layers_list_response(layer_response):
    return [layer_response]


@pytest.fixture
def featureclass_response():
    return {
        "id": "fc-001",
        "name": "boundary",
        "display": "Boundary",
    }


@pytest.fixture
def featureclasses_list_response(featureclass_response):
    return [featureclass_response]


@pytest.fixture
def spatialfeaturegroup_payload():
    return {"name": "Protected Areas", "description": "All protected areas"}


@pytest.fixture
def spatialfeaturegroup_response():
    return {
        "id": "sfg-001",
        "name": "Protected Areas",
        "description": "All protected areas",
        "is_visible": True,
    }


@pytest.fixture
def spatialfeaturegroups_list_response(spatialfeaturegroup_response):
    return [spatialfeaturegroup_response]


@pytest.fixture
def spatialfeature_payload():
    return {
        "name": "Nairobi National Park",
        "type": "Polygon",
        "geojson": {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[36.8, -1.3], [36.9, -1.3], [36.9, -1.4], [36.8, -1.4], [36.8, -1.3]]],
            },
        },
    }


@pytest.fixture
def spatialfeature_response():
    return {
        "id": "sf-001",
        "name": "Nairobi National Park",
        "type": "Polygon",
        "geojson": {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[36.8, -1.3], [36.9, -1.3], [36.9, -1.4], [36.8, -1.4], [36.8, -1.3]]],
            },
        },
    }


@pytest.fixture
def spatialfeatures_list_response(spatialfeature_response):
    return [spatialfeature_response]


# -- Read-only endpoint tests --

@pytest.mark.asyncio
async def test_get_features(er_client, features_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("features")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": features_list_response})
        result = await er_client.get_features()
        assert route.called
        assert result == features_list_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_feature(er_client, feature_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("feature/fp-001")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": feature_response})
        result = await er_client.get_feature("fp-001")
        assert route.called
        assert result == feature_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_feature_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("feature/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.get_feature("nonexistent")
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_featuresets(er_client, featuresets_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("featureset")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": featuresets_list_response})
        result = await er_client.get_featuresets()
        assert route.called
        assert result == featuresets_list_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_featureset(er_client, featureset_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("featureset/fs-001")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": featureset_response})
        result = await er_client.get_featureset("fs-001")
        assert route.called
        assert result == featureset_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_maps(er_client, maps_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("maps")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": maps_list_response})
        result = await er_client.get_maps()
        assert route.called
        assert result == maps_list_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_layers(er_client, layers_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("layers")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": layers_list_response})
        result = await er_client.get_layers()
        assert route.called
        assert result == layers_list_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_layer(er_client, layer_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("layer/layer-001")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": layer_response})
        result = await er_client.get_layer("layer-001")
        assert route.called
        assert result == layer_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_featureclasses(er_client, featureclasses_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("featureclass")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": featureclasses_list_response})
        result = await er_client.get_featureclasses()
        assert route.called
        assert result == featureclasses_list_response
        await er_client.close()


# -- Spatial Feature Group CRUD tests --

@pytest.mark.asyncio
async def test_get_spatialfeaturegroups(er_client, spatialfeaturegroups_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("spatialfeaturegroup")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": spatialfeaturegroups_list_response})
        result = await er_client.get_spatialfeaturegroups()
        assert route.called
        assert result == spatialfeaturegroups_list_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_spatialfeaturegroup(er_client, spatialfeaturegroup_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("spatialfeaturegroup/sfg-001")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": spatialfeaturegroup_response})
        result = await er_client.get_spatialfeaturegroup("sfg-001")
        assert route.called
        assert result == spatialfeaturegroup_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_spatialfeaturegroup_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("spatialfeaturegroup/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.get_spatialfeaturegroup("nonexistent")
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_get_feature_group_deprecated_delegates_to_get_spatialfeaturegroup(
    er_client, spatialfeaturegroup_response
):
    """get_feature_group is deprecated and delegates to get_spatialfeaturegroup."""
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("spatialfeaturegroup/sfg-001")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": spatialfeaturegroup_response})
        with pytest.warns(DeprecationWarning, match="get_feature_group.*get_spatialfeaturegroup"):
            result = await er_client.get_feature_group("sfg-001")
        assert route.called
        assert result == spatialfeaturegroup_response
        await er_client.close()


@pytest.mark.asyncio
async def test_post_spatialfeaturegroup(er_client, spatialfeaturegroup_payload, spatialfeaturegroup_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.post("spatialfeaturegroup")
        route.return_value = httpx.Response(httpx.codes.CREATED, json={"data": spatialfeaturegroup_response})
        result = await er_client.post_spatialfeaturegroup(spatialfeaturegroup_payload)
        assert route.called
        assert result == spatialfeaturegroup_response
        await er_client.close()


@pytest.mark.asyncio
async def test_post_spatialfeaturegroup_forbidden(er_client, spatialfeaturegroup_payload):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.post("spatialfeaturegroup")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={"status": {"code": 403}})
        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_spatialfeaturegroup(spatialfeaturegroup_payload)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_spatialfeaturegroup(er_client, spatialfeaturegroup_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.patch("spatialfeaturegroup/sfg-001")
        updated = {**spatialfeaturegroup_response, "name": "Updated Name"}
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": updated})
        result = await er_client.patch_spatialfeaturegroup("sfg-001", {"name": "Updated Name"})
        assert route.called
        assert result["name"] == "Updated Name"
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_spatialfeaturegroup_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.patch("spatialfeaturegroup/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.patch_spatialfeaturegroup("nonexistent", {"name": "x"})
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_spatialfeaturegroup(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.delete("spatialfeaturegroup/sfg-001/")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)
        result = await er_client.delete_spatialfeaturegroup("sfg-001")
        assert route.called
        assert result is None
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_spatialfeaturegroup_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.delete("spatialfeaturegroup/nonexistent/")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.delete_spatialfeaturegroup("nonexistent")
        assert route.called
        await er_client.close()


# -- Spatial Feature CRUD tests --

@pytest.mark.asyncio
async def test_get_spatialfeatures(er_client, spatialfeatures_list_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("spatialfeature")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": spatialfeatures_list_response})
        result = await er_client.get_spatialfeatures()
        assert route.called
        assert result == spatialfeatures_list_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_spatialfeature(er_client, spatialfeature_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("spatialfeature/sf-001")
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": spatialfeature_response})
        result = await er_client.get_spatialfeature("sf-001")
        assert route.called
        assert result == spatialfeature_response
        await er_client.close()


@pytest.mark.asyncio
async def test_get_spatialfeature_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.get("spatialfeature/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.get_spatialfeature("nonexistent")
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_post_spatialfeature(er_client, spatialfeature_payload, spatialfeature_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.post("spatialfeature")
        route.return_value = httpx.Response(httpx.codes.CREATED, json={"data": spatialfeature_response})
        result = await er_client.post_spatialfeature(spatialfeature_payload)
        assert route.called
        assert result == spatialfeature_response
        await er_client.close()


@pytest.mark.asyncio
async def test_post_spatialfeature_forbidden(er_client, spatialfeature_payload):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.post("spatialfeature")
        route.return_value = httpx.Response(httpx.codes.FORBIDDEN, json={"status": {"code": 403}})
        with pytest.raises(ERClientPermissionDenied):
            await er_client.post_spatialfeature(spatialfeature_payload)
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_spatialfeature(er_client, spatialfeature_response):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.patch("spatialfeature/sf-001")
        updated = {**spatialfeature_response, "name": "Updated Park"}
        route.return_value = httpx.Response(httpx.codes.OK, json={"data": updated})
        result = await er_client.patch_spatialfeature("sf-001", {"name": "Updated Park"})
        assert route.called
        assert result["name"] == "Updated Park"
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_spatialfeature_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.patch("spatialfeature/nonexistent")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.patch_spatialfeature("nonexistent", {"name": "x"})
        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_spatialfeature(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.delete("spatialfeature/sf-001/")
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)
        result = await er_client.delete_spatialfeature("sf-001")
        assert route.called
        assert result is None
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_spatialfeature_not_found(er_client):
    async with respx.mock(base_url=er_client.service_root, assert_all_called=False) as respx_mock:
        route = respx_mock.delete("spatialfeature/nonexistent/")
        route.return_value = httpx.Response(httpx.codes.NOT_FOUND, json={"status": {"code": 404}})
        with pytest.raises(ERClientNotFound):
            await er_client.delete_spatialfeature("nonexistent")
        assert route.called
        await er_client.close()
