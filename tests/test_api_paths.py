"""Unit tests for erclient.api_paths path resolution."""

import pytest

from erclient.api_paths import (DEFAULT_VERSION, event_type_delete_path,
                                event_type_detail_path,
                                event_types_list_path, event_types_patch_path,
                                normalize_version)


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


def test_normalize_version_canonical():
    assert normalize_version("v1.0") == "v1.0"
    assert normalize_version("v2.0") == "v2.0"


def test_normalize_version_aliases():
    assert normalize_version("v1") == "v1.0"
    assert normalize_version("v2") == "v2.0"


def test_normalize_version_unsupported_raises():
    with pytest.raises(ValueError, match="Unsupported API version"):
        normalize_version("v3")
    with pytest.raises(ValueError, match="Unsupported API version"):
        normalize_version("foo")


def test_event_types_list_path_alias_v1():
    assert event_types_list_path("v1") == "activity/events/eventtypes"


def test_event_types_list_path_alias_v2():
    assert event_types_list_path("v2") == "activity/eventtypes"


def test_event_types_list_path_unsupported_raises():
    with pytest.raises(ValueError, match="Unsupported API version"):
        event_types_list_path("v3")


def test_event_type_delete_path_v2():
    assert event_type_delete_path("v2.0", "my_slug") == "activity/eventtypes/my_slug"


def test_event_type_delete_path_v1():
    assert event_type_delete_path("v1.0", "my_slug") == "activity/events/eventtypes/my_slug"


def test_event_type_delete_path_alias():
    assert event_type_delete_path("v2", "my_slug") == "activity/eventtypes/my_slug"


def test_event_type_delete_path_unsupported_raises():
    with pytest.raises(ValueError, match="Unsupported API version"):
        event_type_delete_path("v3", "my_slug")
