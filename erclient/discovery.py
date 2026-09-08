"""RFC 9728 protected-resource metadata: parsing and interpretation.

Pure functions only — the clients own the HTTP. An EarthRanger site serves
``/.well-known/oauth-protected-resource`` unauthenticated, listing the
authorization servers it accepts. Comparing that list against the credentials
in hand is what lets the client tell a caller their username/password grant or
their site-issued token is on borrowed time.
"""
import base64
import binascii
import json
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

DISCOVERY_PATH = "/.well-known/oauth-protected-resource"


@dataclass(frozen=True)
class ProtectedResourceMetadata:
    """The subset of RFC 9728 metadata this client acts on."""

    resource: str
    authorization_servers: tuple
    raw: dict


def discovery_url(service_root):
    """Where to fetch the site's protected-resource metadata.

    ``None`` when there is no site to ask — the caller then skips discovery.
    ``service_root`` is already normalized by the client's constructor.
    """
    if not service_root:
        return None
    return f"{service_root.rstrip('/')}{DISCOVERY_PATH}"


def parse_absolute_url(value):
    """``value`` split into parts if it is an absolute URL, else None.

    The one place a URL from outside is taken apart. ``urlparse`` raises on a
    malformed IPv6 host and reading ``.port`` raises on a non-numeric one, and
    the values that reach here — a discovery document, an authorization
    server's metadata, a token's ``iss`` claim — are exactly the ones the
    functions around this promise to absorb rather than propagate. An absolute
    URL here means a scheme and a host; anything less is not a URL we can
    compare.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = urlparse(value)
        parsed.port  # a property; this is where a bad port raises
    except ValueError:
        return None
    if not parsed.scheme or not parsed.hostname:
        return None
    return parsed


def _same_resource(resource, expected_resource):
    """Compare two resource identifiers, ignoring cosmetic differences.

    RFC 9728 section 3.3 requires the document to name the resource we asked
    about. Scheme and host are case-insensitive per RFC 3986, and a trailing
    slash carries no meaning here. A resource that is not a URL matches
    nothing.
    """
    actual = parse_absolute_url(resource)
    expected = parse_absolute_url(expected_resource)
    if actual is None or expected is None:
        return False
    return (actual.scheme.lower() == expected.scheme.lower()
            and actual.netloc.lower() == expected.netloc.lower()
            and actual.path.rstrip("/") == expected.path.rstrip("/"))


def parse_protected_resource_metadata(text, expected_resource):
    """Parse a discovery document, or return None if it is unusable.

    A 404 page, an HTML error, a document for a different resource, and a
    document missing the fields we need are all the same answer: no metadata.
    Never raises.
    """
    try:
        body = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(body, dict):
        return None

    resource = body.get('resource')
    if not isinstance(resource, str) or not _same_resource(resource, expected_resource):
        return None

    authorization_servers = body.get('authorization_servers')
    if not isinstance(authorization_servers, list):
        return None
    if not all(isinstance(issuer, str) for issuer in authorization_servers):
        return None

    return ProtectedResourceMetadata(
        resource=resource,
        authorization_servers=tuple(authorization_servers),
        raw=body,
    )


def _hostname(url):
    """The lowercased host of ``url``, or ``""`` if it has none to compare."""
    parsed = parse_absolute_url(url)
    return parsed.hostname.lower() if parsed else ""


def classify_authorization_servers(metadata, service_root):
    """Return ``(has_das, has_external)`` for the metadata's issuer list.

    An issuer on the site's own host is the site's legacy token endpoint,
    whatever path it carries. Anything else is an external authorization
    server — in practice the EarthRanger Auth0 tenant. Which one it is does not
    matter yet; that it is not the site is the whole signal.
    """
    site_host = _hostname(service_root)
    has_das = False
    has_external = False
    for issuer in metadata.authorization_servers:
        if _hostname(issuer) == site_host:
            has_das = True
        else:
            has_external = True
    return (has_das, has_external)


def looks_like_jwt(token):
    """Whether the token is shaped like a JWT.

    A shape check only: three segments whose header decodes to a JSON object
    with an ``alg``. No signature check and no claim decoding — reading the
    issuer claim is :func:`jwt_issuer`'s job, and comparing it is
    :func:`credential_site_mismatch`'s.

    An Auth0 *opaque* token would read as legacy here. That is acceptable:
    EarthRanger validates Auth0 tokens as JWTs, so an Auth0 token that works
    against a site is always a JWT.
    """
    segments = token.split('.') if token else []
    if len(segments) != 3 or not all(segments):
        return False

    padded = segments[0] + '=' * (-len(segments[0]) % 4)
    try:
        header = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, binascii.Error):
        return False

    return isinstance(header, dict) and 'alg' in header


def normalize_issuer(issuer):
    """An issuer URL in the form we compare and display.

    DAS validates a JWT's ``iss`` against exactly the string the discovery
    document advertises, so the only differences to forgive are the ones RFC
    3986 calls insignificant: the case of scheme and host, and a trailing
    slash. Anything that does not parse as a URL with a scheme and a host —
    including one ``urlparse`` chokes on — comes back untouched: there is
    nothing to normalize, and the comparison should then simply fail.
    """
    parsed = parse_absolute_url(issuer)
    if parsed is None:
        return issuer

    netloc = parsed.hostname.lower()
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    path = parsed.path[:-1] if parsed.path.endswith("/") else parsed.path
    return urlunparse((parsed.scheme.lower(), netloc, path,
                       parsed.params, parsed.query, parsed.fragment))


def jwt_issuer(token):
    """The token's ``iss`` claim, or None if there isn't a usable one.

    Read, not trusted: the payload is base64url-decoded with its stripped
    padding put back, and nothing verifies the signature. A forged ``iss`` can
    only make this client decline to send a token it was handed, so reading it
    unverified costs nothing. Never raises.
    """
    if not looks_like_jwt(token):
        return None

    segment = token.split('.')[1]
    padded = segment + '=' * (-len(segment) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, binascii.Error):
        return None

    if not isinstance(payload, dict):
        return None
    issuer = payload.get('iss')
    return issuer if isinstance(issuer, str) and issuer else None


def credential_site_mismatch(*, metadata, service_root, mode, token_issuer=None):
    """Why these credentials cannot work at this site, or None.

    Unlike :func:`legacy_auth_warning`, this speaks only to credentials the
    site's API is certain to reject, so the caller is better served by an error
    before any request than by a 401 that reads as a bad password. ``mode`` is
    ``"password"``, ``"opaque_token"``, or ``"jwt_token"``.

    No metadata, or a document listing no authorization servers, means no
    opinion: the site has told us nothing to act on.
    """
    if metadata is None or not metadata.authorization_servers:
        return None

    if mode in ('password', 'opaque_token'):
        has_das, has_external = classify_authorization_servers(
            metadata, service_root)
        # While the site still lists its own issuer, legacy credentials can
        # work — a DAS token does for a bypass_auth0 application. That is
        # legacy_auth_warning's territory, not ours.
        if not has_external or has_das:
            return None
        if mode == 'password':
            return (
                f"Site {service_root} accepts only Auth0-issued tokens, so "
                "username/password login against its legacy token endpoint "
                "cannot work: the token endpoint may still issue a token, but "
                "every API request would be rejected. Pass an Auth0-issued "
                "access token with token=, or construct the client with no "
                "credentials and call login() to sign in interactively."
            )
        return (
            "The token passed with token= looks like a legacy "
            f"EarthRanger-issued token, but site {service_root} accepts only "
            "Auth0-issued tokens. Use an Auth0-issued access token, or "
            "construct the client with no credentials and call login() to "
            "sign in interactively."
        )

    if mode == 'jwt_token':
        # A JWT whose issuer we could not read is not a JWT we can judge; the
        # server still will.
        if token_issuer is None:
            return None
        accepted = [normalize_issuer(issuer)
                    for issuer in metadata.authorization_servers]
        issuer = normalize_issuer(token_issuer)
        if issuer in accepted:
            return None
        return (
            f"The token passed with token= was issued by {issuer}, which site "
            f"{service_root} does not accept. Accepted issuers: "
            f"{', '.join(accepted)}."
        )

    return None


def legacy_auth_warning(*, service_root, has_das, has_external, mode):
    """The warning these credentials deserve at this site, or None.

    Only a site that lists both its own issuer and an external one is warned
    about: an external issuer is what makes legacy credentials a migration
    problem rather than the only option, and the site's own issuer is what
    makes them still work today. Once it is gone they cannot work at all, and
    :func:`credential_site_mismatch` owns that. ``mode`` is ``"password"``,
    ``"opaque_token"``, or ``"jwt_token"``.
    """
    if not (has_das and has_external):
        return None

    if mode == 'password':
        return (
            f"Site {service_root} supports EarthRanger's Auth0 sign-in. "
            "Username/password login through the site's legacy token endpoint "
            "still works but is deprecated and will stop working when the site "
            "completes its migration. Pass an Auth0-issued access token with "
            "token=, or construct the client with no credentials and call "
            "login() to sign in interactively."
        )

    if mode == 'opaque_token':
        return (
            "The token passed with token= looks like a legacy "
            f"EarthRanger-issued token. Site {service_root} supports Auth0 "
            "sign-in, and legacy tokens will stop working when the site "
            "completes its migration. Use an Auth0-issued access token, or "
            "construct the client with no credentials and call login() to "
            "sign in interactively."
        )

    return None
