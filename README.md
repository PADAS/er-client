# EarthRanger Client

## Introduction

[EarthRanger](https://www.earthranger.com/) is a software solution that helps protected area managers, ecologists, and wildlife biologists make informed operational decisions for wildlife conservation.

The earthranger-client (er-client) is a Python library for accessing the EarthRanger HTTP API. It simplifies interaction with the API by abstracting resource-based endpoints and offers both **synchronous** and **asyncio** clients, plus multi-threaded helpers for bulk reads.

## Uses of er-client

* Extracting data for analysis
* Importing ecological or other historical data
* Integrating a new field sensor type. If you do and will be supporting multiple ER sites, contact us to talk about our Gundi integrations platform
* Performing external analysis that results in publishing an Alert on the ER platform.

## Quick Start

See `docs/examples/simple-example.py` for a full sync example (pulse, subjects, tracks, create event, attach file, query events).

## Installation

From PyPI:

```bash
pip install earthranger-client
```

## Choosing sync vs async

| Use case | Client | Notes |
|----------|--------|--------|
| Scripts, notebooks, one-off jobs | `ERClient` (sync) | Blocking calls; no event loop. |
| Asyncio apps (e.g. web servers, async pipelines) | `AsyncERClient` (async) | Use `async with` or call `close()` when done. |

Both clients share the same constructor arguments. The async client supports a subset of the sync client's endpoints (see "Async client scope" below).

## Sync client (ERClient)

Import and construct with `service_root` and either username/password (+ `client_id`) or a bearer `token`:

```python
from erclient import ERClient

# Username/password (client_id required)
client = ERClient(
    service_root="https://sandbox.pamdas.org",
    client_id="example_client_id",
    username="your_username",
    password="your_password",
    provider_key="your_provider_key",  # only needed for sensor / camera-trap posts
)
# Or with a bearer token
client = ERClient(service_root="https://sandbox.pamdas.org", token="your_bearer_token")
```

Common patterns:

```python
import json
from datetime import datetime, timezone

# Single item
event = client.get_event(event_id="uuid")
subject = client.get_subject(subject_id="uuid")

# Paginated iteration (generators).
# `filter` must be a JSON-encoded string, not a dict.
event_filter = json.dumps({
    "date_range": {
        "lower": "2023-11-10T00:00:00-06:00",
        "upper": "2023-11-11T00:00:00-06:00",
    },
})
for event in client.get_events(filter=event_filter, max_results=100):
    ...
for obs in client.get_observations(
    start=datetime(2023, 11, 10, tzinfo=timezone.utc),
    end=datetime(2023, 11, 11, tzinfo=timezone.utc),
):
    ...

# Create / update
new_event = client.post_report({
    "event_type": "wildlife_sighting_rep",  # must match an event type in your ER site
    "title": "A new event",
    "location": {"latitude": 47.5978393, "longitude": -122.3308366},
})
client.post_sensor_observation(observation, sensor_type="generic")  # requires provider_key
client.post_event_file(event_id, filepath="/path/to/file", comment="...")
```

For bulk reads the sync client also provides `get_objects_multithreaded(object="observations", ...)`.

## Async client (AsyncERClient)

Use an **async context manager** so the HTTP session is always closed:

```python
import asyncio
import json

from erclient import AsyncERClient

async def main():
    async with AsyncERClient(
        service_root="https://sandbox.pamdas.org",
        client_id="example_client_id",
        username="your_username",
        password="your_password",
        provider_key="your_provider_key",  # only needed for sensor / camera-trap posts
    ) as client:
        # Single-item calls: await
        event = await client.get_event(event_id="uuid")
        event_types = await client.get_event_types()

        # Stream events or observations: async for.
        # `filter` must be a JSON-encoded string, not a dict.
        event_filter = json.dumps({"date_range": {"lower": "2023-11-10T00:00:00-06:00"}})
        async for event in client.get_events(filter=event_filter, page_size=100):
            ...
        async for observation in client.get_observations(start="2023-11-10T00:00:00-06:00"):
            ...

        # Post (await)
        await client.post_sensor_observation(position)
        await client.post_report(report)
        await client.post_camera_trap_report(camera_trap_payload, file=file_handle)

asyncio.run(main())
```

Without a context manager, create the client and call `await client.close()` when finished:

```python
async def main():
    client = AsyncERClient(service_root="...", client_id="...", username="...", password="...")
    try:
        await client.post_report(report)
        async for obs in client.get_observations(start="2023-11-10T00:00:00-06:00"):
            print(obs)
    finally:
        await client.close()

asyncio.run(main())
```

### Async client scope

The async client currently supports:

* **Post:** Sensor observations (positions), events/reports, event attachments, camera trap reports, messages; event type/category CRUD; adding subjects to a subject group.
* **Get:** Events, single event, event types, event categories, observations, subject groups, subject sources, feature groups, sources (by manufacturer id), source assignments (subjectsources), user/me.
* **Patch:** Events, reports, subjects, event types, event categories.
* **Delete:** Events, event files, event notes, subjects, sources.
* **Relationships:** Adding/removing events to and from incidents; removing subjects from a subject group.

For the full sync surface (e.g. patrols, tracking data export, multithreaded bulk), use `ERClient`.

## Common method signatures (reference)

* **Constructor:** `ERClient(service_root, client_id=None, username=None, password=None, token=None, provider_key=None, ...)`  
  Same for `AsyncERClient`. Use `token` or `client_id`+`username`+`password`. Set `provider_key` when posting sensor/camera-trap data.

* **Events:**  
  `get_events(*, filter, page_size, max_results, ...)` → sync: generator; async: async generator.  
  `get_event(*, event_id, include_details, include_notes, ...)` → single dict.  
  `post_report(data)` / `post_event(data)` → created resource.

* **Observations:**  
  `get_observations(*, subject_id, source_id, start, end, page_size, ...)` → sync: generator; async: async generator.  
  `post_sensor_observation(observation, sensor_type='generic')` → requires `provider_key`.

* **Single resources:**  
  `get_subject(subject_id)`, `get_source_by_id(id)`, `get_event_type(event_type_name, version=...)`, etc. return one object.

### Sync vs async differences

Behaviors that are **not** shared, despite the common signatures above:

| Behavior | `ERClient` (sync) | `AsyncERClient` (async) |
|---|---|---|
| `get_observations` `start`/`end` | `datetime` only — ISO strings are silently ignored | `datetime` or ISO 8601 string |
| `get_events` `max_results` | honored client-side | ignored (forwarded as a query param) |
| `get_observations` `page_size` default | 10000 | 100 |
| HTTP 409 / 429 | plain `ERClientException` | `ERClientRateLimitExceeded`, with `retry_after` |
| HTTP error → exception subclass | only 403 / 404 are consistent; other codes often raise plain `ERClientException`, and 401 / 502 / 504 vary by method | common statuses (400, 401, 403, 404, 409, 429, 500, 502, 503, 504) mapped to subclasses; others raise plain `ERClientException` |
| `exc.status_code` / `exc.response_body` / `exc.retry_after` | never set (always `None`); the status is recoverable only from the exception type, or from the message text for unmapped codes | populated on every HTTP error |
| Helpers only on one client | `get_subject`, `get_source_by_id`, `get_sources`, `get_subjects`, `pulse` | `get_feature_group`, `get_source_subjects`, `get_source_assignments` |

## Best practices

* **Async:** Prefer `async with AsyncERClient(...) as client:` so the session is closed even on errors.
* **Errors:** Catch `ERClientException`; every client error subclasses it. Async maps common statuses to specific subclasses (`ERClientBadRequest`, `ERClientBadCredentials`, `ERClientPermissionDenied`, `ERClientNotFound`, `ERClientRateLimitExceeded`, `ERClientInternalError`, `ERClientServiceUnreachable`); unmapped statuses raise `ERClientException` itself, still with `status_code` set. Sync maps only 403 and 404 consistently, and sync-raised exceptions never populate `exc.status_code` (it is always `None`). For the codes sync does map, the exception type is the only signal — a 404 raises `ERClientNotFound` with no message at all — and the numeric status reaches the message text only for unmapped codes. There is no reliable way to branch on status with the sync client.
* **Time ranges:** Pass timezone-aware `datetime` for `start`/`end` — correct on both clients. Sync silently ignores ISO strings there; async accepts them. Filter `date_range` bounds are ISO 8601 strings with timezone, e.g. `"2023-11-10T00:00:00-06:00"`.
* **Sensor/camera-trap posts:** Set `provider_key` on the client when posting sensor observations or camera trap reports.
* **Large reads:** Sync: consider `get_objects_multithreaded` for big list endpoints. Async: use `page_size` and optional `batch_size` in `get_events`/`get_observations`; cursor-based pagination is used by default.
* **Rate limits:** The API may throttle (e.g. one observation per second per source). Async maps 409/429 to `ERClientRateLimitExceeded`, with `exc.retry_after` in seconds; sync raises a plain `ERClientException` with `exc.status_code` unset — the status appears only in the message text.

For more on the EarthRanger API and event types, see [EarthRanger](https://www.earthranger.com/) and your ER instance's API documentation.
