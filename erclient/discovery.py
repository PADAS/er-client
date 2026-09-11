"""RFC 9728 protected-resource metadata: parsing and interpretation.

Pure functions only -- the clients own the HTTP. An EarthRanger site serves
``/.well-known/oauth-protected-resource`` unauthenticated.
"""
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
    """Where to fetch the site's metadata, or None if there is no site to ask."""
    if not service_root:
        return None
    return f"{service_root.rstrip('/')}{DISCOVERY_PATH}"


def parse_absolute_url(value):
    """``value`` split into parts if it is an absolute URL, else None. Never raises."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urlparse(value)
        parsed.port  # a property; a non-numeric port raises here
    except ValueError:
        return None
    if not parsed.scheme or not parsed.hostname:
        return None
    return parsed


def _is_issuer_identifier(value):
    """Whether ``value`` is an http or https URL, as a listed issuer must be."""
    parsed = parse_absolute_url(value)
    return parsed is not None and parsed.scheme.lower() in ('http', 'https')


def _without_trailing_slash(path):
    """``path`` less one trailing slash, the only one RFC 3986 lets us forgive."""
    # Not rstrip: /foo/// and /foo are different paths, and treating them as
    # one would let a document for either stand in for the other.
    return path[:-1] if path.endswith("/") else path


def _same_resource(resource, expected_resource):
    """Whether two resource identifiers name the same thing (RFC 9728 3.3)."""
    actual = parse_absolute_url(resource)
    expected = parse_absolute_url(expected_resource)
    if actual is None or expected is None:
        return False
    return (actual.scheme.lower() == expected.scheme.lower()
            and actual.netloc.lower() == expected.netloc.lower()
            and (_without_trailing_slash(actual.path)
                 == _without_trailing_slash(expected.path)))


def parse_protected_resource_metadata(text, expected_resource):
    """Parse a discovery document, or return None if it is unusable. Never raises."""
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
    # One bad entry discards the whole document rather than itself: read as an
    # external authorization server, it could turn a working login into a
    # refusal.
    if not all(_is_issuer_identifier(issuer) for issuer in authorization_servers):
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

    An issuer on the site's own host is its legacy token endpoint, whatever
    path it carries; anything else is an external authorization server.
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


def normalize_issuer(issuer):
    """An issuer URL in the form we compare and display.

    EarthRanger validates a JWT's ``iss`` against exactly the string the site
    advertises, so the only differences forgiven are the ones RFC 3986 calls
    insignificant: the case of scheme and host, and a trailing slash. What
    does not parse comes back untouched, so the comparison simply fails.
    """
    parsed = parse_absolute_url(issuer)
    if parsed is None:
        return issuer

    netloc = parsed.hostname.lower()
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse((parsed.scheme.lower(), netloc,
                       _without_trailing_slash(parsed.path),
                       parsed.params, parsed.query, parsed.fragment))
