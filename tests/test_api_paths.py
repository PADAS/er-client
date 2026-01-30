"""Unit tests for erclient.api_paths path resolution."""


from erclient.api_paths import (DEFAULT_VERSION, event_type_detail_path,
                                event_types_list_path, event_types_patch_path)


def test_event_types_list_path_v1():
    assert event_types_list_path("v1.0") == "activity/events/eventtypes"


def test_event_types_list_path_v2():
    assert event_types_list_path("v2.0") == "activity/eventtypes"


def test_event_types_list_path_default():
    assert event_types_list_path() == event_types_list_path(DEFAULT_VERSION)


def test_event_types_patch_path_v1_uses_id():
    event_type = {"id": "abc-123", "value": "my_type"}
    assert event_types_patch_path(
        "v1.0", event_type) == "activity/events/eventtypes/abc-123"


def test_event_types_patch_path_v2_uses_value():
    event_type = {"id": "abc-123", "value": "my_type"}
    assert event_types_patch_path(
        "v2.0", event_type) == "activity/eventtypes/my_type"


def test_event_type_detail_path_v1():
    assert event_type_detail_path(
        "v1.0", "my_slug") == "activity/events/schema/eventtype/my_slug"


def test_event_type_detail_path_v2():
    assert event_type_detail_path(
        "v2.0", "my_slug") == "activity/eventtypes/my_slug"
