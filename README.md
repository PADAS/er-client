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

See `docs/examples/simple-example.py` for a full sync example (pulse, subjects, tracks, create event, attach file, query events). See `docs/examples/interactive-example.py` for signing in as yourself from a terminal or notebook, with no credentials in the script.

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

Both clients take the same constructor arguments, apart from two async-only timeouts (see "Constructor arguments" below). The async client supports a subset of the sync client's endpoints (see "Async client scope" below).

## Authentication

EarthRanger sites are moving from their own token endpoint to Auth0. The client supports three ways to authenticate, and tells you when the one you are using is on its way out at the site you are talking to.

| You are | Use | Notes |
|---|---|---|
| a person at a keyboard, notebook, or shell | no credentials, then `login()` | Signs in as you via your browser. The token lasts about two days; call `login()` again when it expires. Works on any site that has enabled Auth0 sign-in. |
| automation holding an Auth0-issued token | `token=` | Nothing is fetched from the token endpoint. The client checks the token's issuer against the site before the first request. |
| an existing integration with a username and password | `username`, `password`, `client_id` | The legacy password grant. Still works while the site lists its own token endpoint; the client warns when that is ending and refuses when it has ended. |

Sign in as yourself:

```python
from erclient import ERClient

client = ERClient(service_root="https://sandbox.pamdas.org")
client.login()
```

```
You are about to authorize the EarthRanger Python Client to access https://sandbox.pamdas.org as your user.
Open https://auth.pamdas.org/activate?user_code=WDJB-MJHT in a browser and confirm that it shows the code WDJB-MJHT.
Waiting for approval...
```

Approve it in the browser and `login()` returns; the client holds the token from then on. See "Signing in interactively" below for the details.

Use an Auth0-issued token you already hold:

```python
client = ERClient(service_root="https://sandbox.pamdas.org", token="your_bearer_token")
```

Use a username and password, the legacy path:

```python
client = ERClient(
    service_root="https://sandbox.pamdas.org",
    client_id="example_client_id",
    username="your_username",
    password="your_password",
)
```

`AsyncERClient` takes the same arguments and behaves the same way in all three cases; with no credentials, `await client.login()`.

### Signing in interactively

A client constructed with no `token`, `username`, `password` or `client_id` signs the user in with the device-authorization grant ([RFC 8628](https://www.rfc-editor.org/rfc/rfc8628.html)) instead of posting a password grant. Any one of those four keywords, even on its own, keeps the old path. `token=""` counts as no token.

Which authorization server it signs in against comes from the site's own discovery document: the client takes the first issuer the site lists that it holds a registration for, and the registrations are keyed by the **custom domain** a site advertises (`https://auth.pamdas.org`, `https://auth-dev.pamdas.org`), never the canonical Auth0 hostname behind it — EarthRanger validates a token's `iss` against exactly the advertised string. It then reads the tenant's own `/.well-known/openid-configuration` for the endpoints rather than assuming them. `KNOWN_AUTHORIZATION_SERVERS` is importable from `erclient` if you want to see what a release knows; a tenant it does not know needs `device_code_issuer`, `device_code_client_id` and `device_code_audience` together.

```python
from erclient import ERClient, ERClientBadCredentials

client = ERClient(service_root="https://sandbox.pamdas.org")
try:
    client.login()          # prints the URL and code, blocks until approved
except ERClientBadCredentials as e:
    print(e)                # expired code, declined sign-in, or no tenant to use
```

Unlike the password grant, a zero-argument `login()` **raises on failure on both clients** rather than returning `False`; `last_auth_error` is still populated. It refuses before sending anything when the site publishes no authorization servers, lists none this release knows, or when `discovery=False` was passed with no `device_code_issuer`. An authorization server that cannot be read raises `ERClientServiceUnreachable`. While polling, `authorization_pending` and `slow_down` are handled per RFC 8628 §3.5 (the interval grows by five seconds, and a longer `Retry-After` wins); an expired code or a declined sign-in raises `ERClientBadCredentials`.

The prompt goes to **stderr**, so a script whose stdout is piped stays clean, and to the client's logger at INFO. Replace it with `device_code_prompt=`, a callable taking the text.

The arguments that shape the interactive sign-in, all optional:

| Argument | Default | Notes |
|---|---|---|
| `device_code_issuer` | from discovery | Sign in against this Auth0 issuer instead of the one the site names. |
| `device_code_client_id` | from the registration | Client id for the issuer. Required with `device_code_issuer` for a tenant this release does not know. |
| `device_code_audience` | from the registration | API audience for the issuer. Required on the same terms as `device_code_client_id`. |
| `device_code_scope` | `"openid profile email"` | Scopes to request. |
| `device_code_prompt` | writes to stderr | Callable taking the prompt text. |
| `open_browser` | `False` | Also open the verification URL with `webbrowser.open()`. |

The token carries **no refresh token** — the registration does not ask for `offline_access` — so it simply expires, after roughly two days. An explicit `login()` always proceeds, including in a notebook, which reports no terminal on stdin. An *implicit* one does not: when a request method finds no token, or an expired one, and stdin is not a terminal, it raises `ERClientBadCredentials` telling you to call `login()` where you can see the prompt or to pass `token=`. Printing a code into a log nobody is reading and then polling until it expires helps no one.

### What the site tells the client

EarthRanger sites publish the authorization servers they accept at `{service_root}/.well-known/oauth-protected-resource` ([RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html)). Both clients fetch it on every `login()`, and once on the first `auth_headers()` when you passed `token=` — never during construction, and never on a refresh. What the site says decides whether you get a warning:

| The site accepts | With `username`/`password` | With a site-issued (legacy) `token=` | With an Auth0-issued `token=` |
|---|---|---|---|
| its own token endpoint only | silent | silent | silent |
| Auth0 **and** its own | warns: deprecated, still works | warns: deprecated, still works | silent |
| Auth0 only | raises `ERClientBadCredentials` before any request | raises `ERClientBadCredentials` before any request | silent |

An Auth0-issued `token=` is refused the same way, on any row, if its `iss` claim is not one of the authorization servers the site listed — the site validates that claim against exactly the string discovery advertises, so a token from another tenant cannot work anywhere. Issuers are compared ignoring the case of scheme and host and a trailing slash; a JWT whose payload carries no readable `iss` is left alone.

A token is read as Auth0-issued if it is shaped like a JWT; anything else is assumed to be a site-issued (legacy) token. Warnings go to the `ERClient`/`AsyncERClient` logger at WARNING and to `warnings.warn` as `ERClientAuthWarning`, once per client per distinct message. Silence them with `warnings.filterwarnings("ignore", category=ERClientAuthWarning)`. Supplying `token=` together with a `username` or `password` warns the same way at construction: the token wins, as it always has, and the credentials are ignored.

Both the warnings and the refusals name the way out: pass an Auth0-issued token, or construct the client with no credentials and call `login()` to sign in interactively.

The warning rows change nothing — what worked before still works, and a failing login still raises exactly what it raised before. The raise rows are the cases the site's API would reject on every call: sync `login()` returns `False` without posting and `auth_headers()` raises, async `login()` raises directly, and in `token=` mode every `auth_headers()` raises. Discovery itself never blocks auth: a 404, a 5xx, a malformed document or an unreachable endpoint all just mean "no metadata", logged at DEBUG, and no metadata means no warning and no refusal. Pass `discovery=False` to the constructor to switch off the automatic fetches, the warnings and the refusals entirely; `client.discover()` still works, returning `ProtectedResourceMetadata | None`, and `client.protected_resource_metadata` holds whatever the last fetch found.

### When sign-in fails

A failed sign-in has one of three shapes. Either the server refused (the message is `Login failed.`, with the status and body attached), or the client refused before sending anything because the site cannot accept the credentials (the message is the explanation, and `status_code` is `None`), or the interactive flow did not complete (an expired code, a declined sign-in, or no terminal to show the prompt on).

A refusal from the token endpoint is classified by the OAuth `error` code in the response body rather than by HTTP status, which token endpoints use inconsistently (RFC 6749 section 5.2 allows either `400` or `401` for the same condition). Both clients raise the same subclass, with the message `Login failed.` and `exc.status_code` / `exc.response_body` populated, plus `exc.retry_after` in seconds when the refusal carried a `Retry-After` header:

| In the body | Exception |
|---|---|
| `invalid_grant`, `invalid_client`, `unauthorized_client`, `access_denied`, `expired_token` | `ERClientBadCredentials` |
| `invalid_request`, `unsupported_grant_type`, `invalid_scope` | `ERClientBadRequest` |
| no OAuth `error` — status decides: 401, 400, 429, 500, 502/503/504 | `ERClientBadCredentials`, `ERClientBadRequest`, `ERClientRateLimitExceeded`, `ERClientInternalError`, `ERClientServiceUnreachable` |
| `credential_site_mismatch`, `interactive_sign_in_unavailable` — the client's own codes, never sent or received on the wire | `ERClientBadCredentials` |
| anything else (unknown code, other status, unparseable body) | `ERClientException` |

Whether `login()` itself raises depends on the client and the grant. Sync `login()` returns `False` for a failed password grant and raises for a failed interactive sign-in. Async `login()` raises in both cases: `httpx.HTTPStatusError` for a password grant refused when you called `login()` or `refresh_token()` directly, and the classified subclass above for an interactive sign-in. On both clients the classification always applies when a request method such as `get_events()` triggers the login, and on sync `auth_headers()` raises the classified subclass too.

For the reason behind a `False`, read `client.last_auth_error` — an `AuthError` carrying `status_code`, `error`, `error_description`, `response_body`, `url`, `grant_type` and `retry_after`. It is `None` until a token request is refused, and is cleared by the next successful one. It is also set when the client refuses before sending anything; `status_code` and `response_body` are then `None`, since no server was consulted, and the exception's message is the whole explanation rather than `Login failed.`. Which of the two client-side codes you get says why: `credential_site_mismatch` means the credentials you supplied cannot work at this site (see "What the site tells the client" above), and `interactive_sign_in_unavailable` means you supplied none and the interactive sign-in that would have got some cannot run — `discovery=False` with no `device_code_issuer`, an incomplete issuer override, a site naming no tenant this release knows, or no terminal to show the prompt on. `last_auth_error` is available on both clients.

## Sync client (ERClient)

Import and construct with `service_root` and one of the three ways to authenticate described above; the examples here use a token:

```python
from erclient import ERClient

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
        token="your_bearer_token",
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
    client = AsyncERClient(service_root="...", token="...")
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

* **Post:** Sensor observations (positions), events/reports, event attachments, camera trap reports, messages, event types, event categories; adding subjects to a subject group.
* **Get:** Events, single event, event types, event categories, observations, subject groups, subject sources, feature groups, sources (by manufacturer id), source assignments (subjectsources), user/me.
* **Patch:** Events, reports, subjects, event types, event categories.
* **Delete:** Events, event files, event notes, subjects, sources. Neither client can delete event types or event categories.
* **Relationships:** Adding/removing events to and from incidents; removing subjects from a subject group.

For the full sync surface (e.g. patrols, tracking data export, multithreaded bulk), use `ERClient`.

## Constructor arguments

Both clients are declared as `__init__(self, **kwargs)`, so **every argument is
keyword-only** — `ERClient("https://sandbox.pamdas.org")` raises `TypeError`.
Unrecognised keywords are silently ignored rather than rejected, so a typo such as
`provider_ke=` leaves `provider_key` unset with no error.

| Argument | Default | Notes |
|---|---|---|
| `service_root` | `None` | Base URL, e.g. `https://sandbox.pamdas.org`. A full API root is also accepted: any `/api/...` suffix is stripped, so passing `.../api/v2.0` does **not** select v2.0. |
| `token` | `None` | Bearer token, ideally Auth0-issued. Nothing is fetched from the token endpoint. Takes precedence over username/password. |
| `client_id` | `None` | Required for the legacy username/password grant. Its presence selects that grant even without username/password. |
| `username`, `password` | `None` | The legacy password grant; use together with `client_id`. |
| `token_url` | `{service_root}/oauth2/token` | Override only if the site's token endpoint differs. Password grant only. |
| `discovery` | `True` | Whether to fetch the site's protected-resource metadata on the paths that decide auth, warn about legacy credentials, and refuse credentials the site cannot accept. See "What the site tells the client" under Authentication. |
| `device_code_issuer` | `None` | Sign in against this Auth0 issuer instead of the one the site's discovery document names. Skips the discovery lookup. |
| `device_code_client_id` | `None` | Overrides the client id registered for the chosen issuer. Required with `device_code_issuer` for a tenant this release does not know. |
| `device_code_audience` | `None` | Overrides the API audience requested for the chosen issuer. Required on the same terms as `device_code_client_id`. |
| `device_code_scope` | `"openid profile email"` | Scopes to request. No `offline_access`: the registration issues no refresh token. |
| `device_code_prompt` | `None` | Callable taking the prompt text, replacing the default that writes to stderr and logs at INFO. |
| `open_browser` | `False` | Also open the verification URL with `webbrowser.open()`. A browser that will not open is logged at DEBUG and ignored — the URL was printed either way. |
| `provider_key` | `None` | Required for sensor and camera-trap posts; it becomes a path segment. |
| `max_http_retries` | `5` | Connection-level retries. **Effective on async only** — the sync client accepts and stores it but never uses it; sync retry behavior is fixed (5 session-level retries on 502, plus per-request retries in GETs). |
| `realtime_url` | `None` | Accepted and stored, but unused by this library. |
| `connect_timeout` | `3.1` | Seconds. **Async only.** |
| `data_timeout` | `20` | Seconds. **Async only.** |

Use either `token`, or `client_id` + `username` + `password`, or nothing at all and
`login()`; see "Authentication" above. The `device_code_*` arguments and `open_browser`
only apply to that last case.

## API versions

Event-type endpoints exist in two API versions. `v1.0` is the default; pass `version=`
to opt into `v2.0`:

```python
from erclient import ERClient, VERSION_2_0

client = ERClient(service_root="https://sandbox.pamdas.org", token="your_bearer_token")
event_types = client.get_event_types(version=VERSION_2_0)
```

Four methods accept `version=`, on both clients — `get_event_types`, `get_event_type`,
`post_event_type`, `patch_event_type`. Every other call is `v1.0`, and passing
`.../api/v2.0` as `service_root` does **not** change that (see "Constructor arguments").

Accepted values are `VERSION_1_0` (`"v1.0"`) and `VERSION_2_0` (`"v2.0"`); the aliases
`"v1"` and `"v2"` work too. Anything else raises `ValueError`, including `"1.0"` — the
leading `v` is required.

`patch_event_type` identifies the event type differently per version, and raises
`ValueError` when the key it needs is absent from the payload:

| Version | Key used | Resulting path |
|---|---|---|
| `v1.0` | `event_type["id"]` | `activity/events/eventtypes/{id}` |
| `v2.0` | `event_type["value"]` (slug) | `activity/eventtypes/{value}` |

Caveat: the async client's `patch_event_type` reads `event_type["value"]` regardless of
version (for logging), so on `AsyncERClient` a `v1.0` payload must include `value` as
well as `id` — a payload without `value` raises `KeyError` there, not `ValueError`.

## Common method signatures (reference)

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
| HTTP 409 / 429 for API responses | plain `ERClientException` | `ERClientRateLimitExceeded`, with `retry_after` |
| HTTP error → exception subclass | only 403 / 404 are consistent; other codes often raise plain `ERClientException`, and 401 / 502 / 504 vary by method | common statuses (400, 401, 403, 404, 409, 429, 500, 502, 503, 504) mapped to subclasses; others raise plain `ERClientException` |
| `exc.status_code` / `exc.response_body` / `exc.retry_after` | never set (always `None`) for API errors; the status is recoverable only from the exception type, or from the message text for unmapped codes. Login failures are the exception: `status_code` and `response_body` are set, and `retry_after` when the token endpoint sent the header | populated on every HTTP error |
| Login failure | `auth_headers()` raises the classified subclass; `login()` returns `False` | request methods raise the classified subclass; `login()` raises `httpx.HTTPStatusError` |
| Interactive sign-in failure | `login()` raises | `login()` raises the same class — never `httpx.HTTPStatusError` |
| Helpers only on one client | `get_subject`, `get_source_by_id`, `get_sources`, `get_subjects`, `pulse` | `get_feature_group`, `get_source_subjects`, `get_source_assignments` |

## Best practices

* **Async:** Prefer `async with AsyncERClient(...) as client:` so the session is closed even on errors.
* **Errors:** Catch `ERClientException`; every client error subclasses it. Async maps common statuses to specific subclasses (`ERClientBadRequest`, `ERClientBadCredentials`, `ERClientPermissionDenied`, `ERClientNotFound`, `ERClientRateLimitExceeded`, `ERClientInternalError`, `ERClientServiceUnreachable`); unmapped statuses raise `ERClientException` itself, still with `status_code` set. Sync maps only 403 and 404 consistently, and sync-raised exceptions never populate `exc.status_code` for API errors (it is always `None`). For the codes sync does map, the exception type is the only signal — a 404 raises `ERClientNotFound` with no message at all — and the numeric status reaches the message text only for unmapped codes. There is no reliable way to branch on status with the sync client, except for login failures — see "When sign-in fails" under Authentication.
* **Authentication:** see the "Authentication" section above for the three ways to sign in, what the site's discovery document changes, and how failures are reported.
* **Time ranges:** Pass timezone-aware `datetime` for `start`/`end` — correct on both clients. Sync silently ignores ISO strings there; async accepts them. Filter `date_range` bounds are ISO 8601 strings with timezone, e.g. `"2023-11-10T00:00:00-06:00"`.
* **Sensor/camera-trap posts:** Set `provider_key` on the client when posting sensor observations or camera trap reports.
* **Large reads:** Sync: consider `get_objects_multithreaded` for big list endpoints. Async: use `page_size` and optional `batch_size` in `get_events`/`get_observations`; cursor-based pagination is used by default.
* **Rate limits:** The API may throttle (e.g. one observation per second per source). Async maps 409/429 to `ERClientRateLimitExceeded`, with `exc.retry_after` in seconds; sync raises a plain `ERClientException` with `exc.status_code` unset — the status appears only in the message text.

For more on the EarthRanger API and event types, see [EarthRanger](https://www.earthranger.com/) and your ER instance's API documentation.
