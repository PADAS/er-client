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
)
# Or with a bearer token
client = ERClient(service_root="https://sandbox.pamdas.org", token="your_bearer_token")
```

Common patterns:

```python
# Single item
event = client.get_event(event_id="uuid")
subject = client.get_subject(subject_id="uuid")

# Paginated iteration (generators)
for event in client.get_events(filter=..., max_results=100):
    ...
for obs in client.get_observations(start="2023-11-10T00:00:00Z", end="2023-11-11T00:00:00Z"):
    ...

# Create / update
new_event = client.post_report({"event_type": "...", "title": "...", "location": {...}, ...})
client.post_sensor_observation(observation, sensor_type="generic")  # requires provider_key
client.post_event_file(event_id, filepath="/path/to/file", comment="...")
```

For bulk reads the sync client also provides `get_objects_multithreaded(object="observations", ...)`.

## Async client (AsyncERClient)

Use an **async context manager** so the HTTP session is always closed:

```python
import asyncio
from erclient import AsyncERClient

async def main():
    async with AsyncERClient(
        service_root="https://sandbox.pamdas.org",
        client_id="example_client_id",
        username="your_username",
        password="your_password",
    ) as client:
        # Single-item calls: await
        event = await client.get_event(event_id="uuid")
        event_types = await client.get_event_types()

        # Stream events or observations: async for
        async for event in client.get_events(filter=..., page_size=100):
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
client = AsyncERClient(service_root="...", client_id="...", username="...", password="...")
try:
    await client.post_report(report)
    async for obs in client.get_observations(start="2023-11-10T00:00:00-06:00"):
        print(obs)
finally:
    await client.close()
```

### Async client scope

The async client currently supports:

* **Post:** Sensor observations (positions), events/reports, event attachments, camera trap reports, messages; event/subject/event type/category CRUD where implemented.
* **Get:** Events, single event, event types, observations, subject groups, feature groups, sources, source assignments (subjectsources), user/me.
* **Patch/delete:** Events, event files/notes, subjects (patch), and related incident/relationship APIs as in the sync client.

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

## Best practices

* **Async:** Prefer `async with AsyncERClient(...) as client:` so the session is closed even on errors.
* **Errors:** Catch `ERClientException` and subclasses (`ERClientBadCredentials`, `ERClientNotFound`, `ERClientPermissionDenied`, `ERClientRateLimitExceeded`, `ERClientServiceUnreachable`, etc.) for robust handling.
* **Time ranges:** Use timezone-aware datetimes or ISO 8601 strings with timezone (e.g. `"2023-11-10T00:00:00-06:00"`) for `start`/`end` and filter `date_range` to avoid ambiguity.
* **Sensor/camera-trap posts:** Set `provider_key` on the client when posting sensor observations or camera trap reports.
* **Large reads:** Sync: consider `get_objects_multithreaded` for big list endpoints. Async: use `page_size` and optional `batch_size` in `get_events`/`get_observations`; cursor-based pagination is used by default.
* **Rate limits:** The API may throttle (e.g. one observation per second per source); the client raises `ERClientRateLimitExceeded` on 409/429. Back off and retry as needed.

For more on the EarthRanger API and event types, see [EarthRanger](https://www.earthranger.com/) and your ER instance's API documentation.
