"""Discovery-routed authentication for one-off, interactive jobs.

Different sites accept tokens from different authorization servers, and a
client has to pick one before it holds a token of any kind. A site answers that
question itself: its RFC 9728 protected-resource metadata, served at
/.well-known/oauth-protected-resource, names the authorization server(s) it
accepts. This module reads that and authenticates accordingly, so callers do
not have to know or configure which is which.

This module is deliberately sync-only and standalone. It hands back a token;
what holds it is the caller's business, and ERClient/AsyncERClient are
untouched:

    token = authenticate_for_site("https://example.pamdas.org", ...)
    client = ERClient(service_root="https://example.pamdas.org",
                      token=token.access_token)

Everything here must run on Python 3.8, the package floor -- so typing.Optional
and typing.List rather than PEP 604/585 syntax, in annotations and dataclass
fields alike.
"""
from typing import Any, List

import httpx

from .client import normalize_service_root
from .er_errors import ERClientDiscoveryError

# RFC 9728 s3.1: the metadata lives at a well-known path under the resource origin.
PROTECTED_RESOURCE_PATH = "/.well-known/oauth-protected-resource"

# Discovery is a single small pre-flight request; a caller waiting on an
# interactive login should learn quickly that a site is unreachable.
DISCOVERY_TIMEOUT_SECONDS = 10


def discover_authorization_servers(site: str) -> List[str]:
    """Ask a site which authorization server(s) it accepts.

    ``site`` is whatever gets passed to ERClient as service_root -- a bare
    origin or a full API root -- and is reduced to an origin either way.

    Returns the ``authorization_servers`` list verbatim, in the order the site
    advertised it. Raises ERClientDiscoveryError if the endpoint is unreachable,
    answers non-2xx, returns something we cannot parse, or returns a document
    that fails the RFC 9728 s3.3 identity check.
    """
    origin = normalize_service_root(site)
    # Appending the well-known path diverges from RFC 9728 s3 when the origin
    # carries a path of its own: the spec inserts the well-known segment
    # between host and path (https://host/.well-known/...<path>), not after it.
    # EarthRanger sites are bare origins, where the two constructions agree --
    # but a site proxied under a subpath would be probed at the wrong URL, and
    # the s3.3 identity check compares against the same path-bearing origin.
    url = origin + PROTECTED_RESOURCE_PATH

    try:
        # Redirects are followed because sites sit behind load balancers that
        # normalize scheme and host. Note that the s3.3 check below is NOT what
        # makes this safe -- it only catches a document that truthfully names a
        # different resource; a malicious redirect target can simply claim our
        # origin and pass it. What bounds the damage is that this document
        # never chooses where credentials go: authenticate_for_site derives the
        # token URL from the caller's own ``site`` argument and consults this
        # list only as a yes/no on sending them at all. A spoofed document can
        # misroute -- a refusal, a spurious warning -- but not exfiltrate.
        # Anything that reads this list MUST preserve that invariant.
        response = httpx.get(
            url, timeout=DISCOVERY_TIMEOUT_SECONDS, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise ERClientDiscoveryError(
            "Could not reach the authorization-server discovery endpoint for "
            "{}: {}".format(origin, exc))

    if not response.is_success:
        raise ERClientDiscoveryError(
            "Authorization-server discovery failed for {}. A site that predates "
            "RFC 9728 discovery will answer 404 here.".format(origin),
            status_code=response.status_code,
            response_body=response.text,
        )

    return _authorization_servers_from(response, origin)


def _authorization_servers_from(response: httpx.Response, origin: str) -> List[str]:
    """Validate a protected-resource document and pull its authorization servers out."""
    try:
        document = response.json()
    except ValueError as exc:
        raise ERClientDiscoveryError(
            "Authorization-server discovery for {} returned a body that is not "
            "JSON: {}".format(origin, exc),
            status_code=response.status_code,
            response_body=response.text,
        )

    if not isinstance(document, dict):
        raise ERClientDiscoveryError(
            "Authorization-server discovery for {} returned {}, not a JSON "
            "object.".format(origin, type(document).__name__),
            status_code=response.status_code,
            response_body=response.text,
        )

    _check_resource_identity(document.get("resource"), origin, response)

    authorization_servers = document.get("authorization_servers")
    if not isinstance(authorization_servers, list) or not authorization_servers:
        raise ERClientDiscoveryError(
            "The protected-resource metadata for {} lists no authorization "
            "servers, so there is nothing to authenticate against.".format(
                origin),
            status_code=response.status_code,
            response_body=response.text,
        )

    return authorization_servers


def _check_resource_identity(resource: Any, origin: str, response: httpx.Response) -> None:
    """Enforce RFC 9728 s3.3.

    The document has to claim the very origin we built the metadata URL from.
    Comparison is string-exact -- the spec does not invite normalization -- so a
    mismatch means the document describes some other resource and must be
    discarded rather than trusted to name our authorization servers.
    """
    if resource == origin:
        return

    raise ERClientDiscoveryError(
        "The protected-resource metadata served for {origin} identifies itself "
        "as {resource!r}. RFC 9728 requires these to match exactly, so the "
        "document was discarded.".format(origin=origin, resource=resource),
        status_code=response.status_code,
        response_body=response.text,
    )
