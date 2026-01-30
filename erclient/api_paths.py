"""
Centralized path configuration for versioned ER API endpoints.

Paths are keyed by literal API version (e.g. "v1.0", "v2.0") as used in the URL.
"""

DEFAULT_VERSION = "v1.0"

# Event types: path prefix for list/get/post; patch appends identifier (id for v1.0, value for v2.0).
EVENT_TYPES_PATHS = {
    "v1.0": "activity/events/eventtypes",
    "v2.0": "activity/eventtypes",
}


def event_types_list_path(version: str = DEFAULT_VERSION) -> str:
    """Path for listing or posting event types (no trailing segment)."""
    return EVENT_TYPES_PATHS.get(version, EVENT_TYPES_PATHS[DEFAULT_VERSION])


def event_types_patch_path(version: str, event_type: dict) -> str:
    """
    Path for patching an event type.

    v1.0 uses event_type["id"] in the path; v2.0 uses event_type["value"] (slug).
    """
    base = event_types_list_path(version)
    if version == "v2.0":
        return f"{base}/{event_type.get('value')}"
    return f"{base}/{event_type.get('id')}"


def event_type_detail_path(version: str, value: str) -> str:
    """
    Path for getting a single event type by name/slug.

    v1.0 uses schema path activity/events/schema/eventtype/{value};
    v2.0 uses activity/eventtypes/{value}.
    """
    if version == "v2.0":
        return f"{event_types_list_path(version)}/{value}"
    return f"activity/events/schema/eventtype/{value}"
