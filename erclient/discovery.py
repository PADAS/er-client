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
from urllib.parse import urlparse

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


def _same_resource(resource, expected_resource):
    """Compare two resource identifiers, ignoring cosmetic differences.

    RFC 9728 section 3.3 requires the document to name the resource we asked
    about. Scheme and host are case-insensitive per RFC 3986, and a trailing
    slash carries no meaning here.
    """
    actual = urlparse(resource)
    expected = urlparse(expected_resource)
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


def classify_authorization_servers(metadata, service_root):
    """Return ``(has_das, has_external)`` for the metadata's issuer list.

    An issuer on the site's own host is the site's legacy token endpoint,
    whatever path it carries. Anything else is an external authorization
    server — in practice the EarthRanger Auth0 tenant. Which one it is does not
    matter yet; that it is not the site is the whole signal.
    """
    site_host = (urlparse(service_root).hostname or "").lower()
    has_das = False
    has_external = False
    for issuer in metadata.authorization_servers:
        if (urlparse(issuer).hostname or "").lower() == site_host:
            has_das = True
        else:
            has_external = True
    return (has_das, has_external)


def looks_like_jwt(token):
    """Whether the token is shaped like a JWT.

    A shape check only: three segments whose header decodes to a JSON object
    with an ``alg``. No signature check and no claim decoding — Step 3 compares
    the issuer claim.

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


def legacy_auth_warning(*, service_root, has_das, has_external, mode):
    """The warning these credentials deserve at this site, or None.

    Silent unless the site has an external authorization server, since that is
    what makes legacy credentials a migration problem rather than the only
    option. ``mode`` is ``"password"``, ``"opaque_token"``, or ``"jwt_token"``.
    """
    if not has_external:
        return None

    if mode == 'password':
        if has_das:
            return (
                f"Site {service_root} supports EarthRanger's Auth0 sign-in. "
                "Username/password login through the site's legacy token endpoint "
                "still works but is deprecated and will stop working when the site "
                "completes its migration. Pass an Auth0-issued access token with "
                "token= instead."
            )
        return (
            f"Site {service_root} accepts only Auth0-issued tokens. "
            "Username/password login against its legacy token endpoint will "
            "fail. Pass an Auth0-issued access token with token= instead."
        )

    if mode == 'opaque_token':
        if has_das:
            return (
                "The token passed with token= looks like a legacy "
                f"EarthRanger-issued token. Site {service_root} supports Auth0 "
                "sign-in, and legacy tokens will stop working when the site "
                "completes its migration. Use an Auth0-issued access token."
            )
        return (
            "The token passed with token= looks like a legacy "
            f"EarthRanger-issued token, but site {service_root} accepts only "
            "Auth0-issued tokens. Requests will be rejected. Use an "
            "Auth0-issued access token."
        )

    return None
