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
from dataclasses import dataclass, field
from typing import Any, List, Optional

import httpx

from .client import normalize_service_root
from .er_errors import (ERClientBadCredentials, ERClientDiscoveryError,
                        ERClientException, ERClientServiceUnreachable)

# RFC 9728 s3.1: the metadata lives at a well-known path under the resource origin.
PROTECTED_RESOURCE_PATH = "/.well-known/oauth-protected-resource"

# Discovery is a single small pre-flight request; a caller waiting on an
# interactive login should learn quickly that a site is unreachable.
DISCOVERY_TIMEOUT_SECONDS = 10

# A token exchange is a single round trip, but it is the one the caller is
# actually waiting on, so it gets more room than discovery.
TOKEN_TIMEOUT_SECONDS = 30


@dataclass
class AccessToken:
    """A token issued by an authorization server, plus what came with it.

    Held in memory only -- this library never writes one to disk and never
    refreshes one. A caller that needs either does it a layer above.

    The two secrets are excluded from the generated repr so that a logged or
    printed AccessToken -- or one surfaced in a traceback -- does not hand out
    live credentials.
    """
    access_token: str = field(repr=False)
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    # Populated only if the server volunteers one. The library does nothing
    # with it, but dropping it silently would deny the caller the choice.
    refresh_token: Optional[str] = field(default=None, repr=False)


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


def authenticate_with_password(
    issuer: str,
    username: str,
    password: str,
    client_id: Optional[str] = None,
) -> AccessToken:
    """Exchange a username and password for a token at ``issuer``.

    The OAuth 2.0 password grant, sent exactly as the client has always sent it.
    Its endpoint is the issuer plus /token, which is also the token URL an
    ERClient built for the same site derives on its own.

    Rejected credentials raise ERClientBadCredentials; a server that is merely
    unwell raises something else, so a caller is never told to go re-check a
    password that was fine.
    """
    payload = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    # Only when there is one: httpx would encode a None as an empty client_id,
    # where requests -- which ERClient.login() has always used -- omits the key.
    if client_id is not None:
        payload["client_id"] = client_id

    try:
        response = httpx.post(
            issuer + "/token", data=payload, timeout=TOKEN_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise ERClientServiceUnreachable(
            "Could not reach the token endpoint at {}: {}".format(issuer, exc))

    if not response.is_success:
        raise _token_error(response, issuer)

    return _access_token_from(response, issuer)


def _token_error(response: httpx.Response, issuer: str) -> ERClientException:
    """Turn a failed token exchange into the narrowest error that fits."""
    if _server_blames_the_credentials(response):
        return ERClientBadCredentials(
            "{} rejected the credentials supplied.".format(issuer),
            status_code=response.status_code,
            response_body=response.text,
        )

    return ERClientException(
        "The token request to {} failed.".format(issuer),
        status_code=response.status_code,
        response_body=response.text,
    )


def _server_blames_the_credentials(response: httpx.Response) -> bool:
    """True only when the server itself says the credentials were the problem.

    RFC 6749 s5.2 puts an ``error`` code in every failed token response. A
    wrong password comes back as invalid_grant and an unrecognized client_id
    as invalid_client -- but the same 400 also carries invalid_request and
    unsupported_grant_type, which are a broken request, not a bad password.
    So the status code alone is not enough: only the two credential codes are
    reported as ERClientBadCredentials, and a rejection with no readable error
    code falls through to the generic error rather than sending the caller to
    re-check a password that may have been fine.
    """
    if response.status_code not in (
            httpx.codes.BAD_REQUEST, httpx.codes.UNAUTHORIZED):
        return False

    try:
        payload = response.json()
    except ValueError:
        return False

    if not isinstance(payload, dict):
        return False

    return payload.get("error") in ("invalid_grant", "invalid_client")


def _access_token_from(response: httpx.Response, issuer: str) -> AccessToken:
    """Build an AccessToken from a successful token response."""
    try:
        payload = response.json()
    except ValueError as exc:
        raise ERClientException(
            "The token response from {} is not JSON: {}".format(issuer, exc),
            status_code=response.status_code,
            response_body=response.text,
        )

    access_token = payload.get("access_token") if isinstance(
        payload, dict) else None
    if not access_token:
        raise ERClientException(
            "{} answered successfully but issued no access token.".format(
                issuer),
            status_code=response.status_code,
            response_body=response.text,
        )

    return AccessToken(
        access_token=access_token,
        token_type=payload.get("token_type") or "Bearer",
        expires_in=payload.get("expires_in"),
        scope=payload.get("scope"),
        refresh_token=payload.get("refresh_token"),
    )
