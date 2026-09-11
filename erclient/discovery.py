"""RFC 9728 protected-resource metadata: parsing and interpretation.

Pure functions only -- the clients own the HTTP. An EarthRanger site serves
``/.well-known/oauth-protected-resource`` unauthenticated.
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


def looks_like_jwt(token):
    """Whether ``token`` is shaped like a JWT: three segments whose header
    decodes to a JSON object with an ``alg``. Never raises."""
    if not isinstance(token, str):
        return False
    segments = token.split('.') if token else []
    if len(segments) != 3 or not all(segments):
        return False

    try:
        header = json.loads(_decode_segment(segments[0]))
    except (ValueError, binascii.Error):
        return False

    return isinstance(header, dict) and 'alg' in header


def _decode_segment(segment):
    """One base64url JWT segment, with the padding a JWT strips put back."""
    return base64.urlsafe_b64decode(segment + '=' * (-len(segment) % 4))


def jwt_issuer(token):
    """The token's ``iss`` claim, or None if there is not a usable one.

    Read, not trusted: nothing verifies the signature. A forged ``iss`` can
    only make this client decline to send a token it was handed, so reading it
    unverified costs nothing. Never raises.
    """
    if not looks_like_jwt(token):
        return None

    try:
        payload = json.loads(_decode_segment(token.split('.')[1]))
    except (ValueError, binascii.Error):
        return None

    if not isinstance(payload, dict):
        return None
    issuer = payload.get('iss')
    return issuer if isinstance(issuer, str) and issuer else None


def credential_site_mismatch(*, metadata, service_root, mode,
                             token_issuer=None):
    """Why these credentials look wrong for this site, or None.

    ``mode`` is "password", "opaque_token" or "jwt_token". No metadata means
    no opinion. The password wording is a refusal, since the client declines
    to post; the token wordings describe what the document says and leave the
    verdict to the server.
    """
    if metadata is None or not metadata.authorization_servers:
        return None

    if mode in ('password', 'opaque_token'):
        has_das, has_external = classify_authorization_servers(
            metadata, service_root)
        # While the site still lists its own issuer, legacy credentials can
        # work. That is legacy_auth_warning's business, not this one's.
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
            f"EarthRanger-issued token, but site {service_root} lists only "
            "Auth0 issuers. Use an Auth0-issued access token, or construct "
            "the client with no credentials and call login() to sign in "
            "interactively."
        )

    if mode == 'jwt_token':
        # A JWT whose issuer we could not read is not one we can judge; the
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
            f"{service_root} does not list among the issuers it accepts: "
            f"{', '.join(accepted)}."
        )

    return None


def legacy_auth_warning(*, service_root, has_das, has_external, mode):
    """The warning a password grant deserves at this site, or None.

    Only a site listing both its own issuer and an external one is warned
    about: the external one is what makes the grant a migration problem rather
    than the only option, and its own is what makes the grant still work. Once
    that is gone the grant cannot work at all, which is
    :func:`credential_site_mismatch`'s business.
    """
    if not (has_das and has_external):
        return None

    if mode == 'password':
        return (
            f"Site {service_root} supports EarthRanger's Auth0 sign-in. "
            "Username/password login through the site's legacy token endpoint "
            "still works but is deprecated and will stop working when the "
            "site completes its migration. Pass an Auth0-issued access token "
            "with token=, or construct the client with no credentials and "
            "call login() to sign in interactively."
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
