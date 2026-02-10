"""
Centralized path configuration for versioned ER API endpoints.

Paths are keyed by literal API version (e.g. "v1.0", "v2.0") as used in the URL.
"""

VERSION_1_0 = "v1.0"
VERSION_2_0 = "v2.0"
DEFAULT_VERSION = VERSION_1_0

SUPPORTED_VERSIONS = (VERSION_1_0, VERSION_2_0)
VERSION_ALIASES = {"v1": VERSION_1_0, "v2": VERSION_2_0}

# Event types: path prefix for list/get/post; patch appends identifier (id for v1.0, value for v2.0).
EVENT_TYPES_PATHS = {
    VERSION_1_0: "activity/events/eventtypes",
    VERSION_2_0: "activity/eventtypes",
}


def normalize_version(version: str) -> str:
    """
    Return the canonical API version string and validate it is supported.

    Normalizes aliases (e.g. "v1" -> "v1.0", "v2" -> "v2.0"). Raises ValueError
    for unknown or unsupported versions so base URL and path stay consistent.
    """
    canonical = VERSION_ALIASES.get(version, version)
    if canonical not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"Unsupported API version {version!r}; supported: {list(SUPPORTED_VERSIONS)}"
        )
    return canonical


def event_types_list_path(version: str = DEFAULT_VERSION) -> str:
    """Path for listing or posting event types (no trailing segment)."""
    version = normalize_version(version)
    return EVENT_TYPES_PATHS[version]


def event_types_patch_path(version: str, event_type: dict) -> str:
    """
    Path for patching an event type.

    v1.0 uses event_type["id"] in the path; v2.0 uses event_type["value"] (slug).
    """
    version = normalize_version(version)
    base = EVENT_TYPES_PATHS[version]
    if version == VERSION_2_0:
        try:
            value = event_type['value']
            return f"{base}/{value}"
        except KeyError:
            raise ValueError(f"Event type value is required for v2.0 patching")

    try:
        event_type_id = event_type['id']
        return f"{base}/{event_type_id}"
    except KeyError:
        raise ValueError(f"Event type id is required for v1.0 patching")


def event_type_delete_path(version: str, value: str) -> str:
    """
    Path for deleting an event type by slug (value).

    v2.0 uses activity/eventtypes/{value};
    v1.0 uses activity/events/eventtypes/{value} (if the server supports it).
    """
    version = normalize_version(version)
    return f"{EVENT_TYPES_PATHS[version]}/{value}"


def event_type_detail_path(version: str, value: str) -> str:
    """
    Path for getting a single event type by name/slug.

    v1.0 uses schema path activity/events/schema/eventtype/{value};
    v2.0 uses activity/eventtypes/{value}.
    """
    version = normalize_version(version)
    if version == VERSION_2_0:
        return f"{EVENT_TYPES_PATHS[version]}/{value}"
    return f"activity/events/schema/eventtype/{value}"
