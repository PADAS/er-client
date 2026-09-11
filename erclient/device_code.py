"""RFC 8628 device authorization: tables, parsers, and the prompt.

Pure functions only -- the clients own the HTTP. A site's discovery document
names the authorization servers it accepts, but not the registered client_id
and audience a device-code flow also needs, so those live in the table here.

That table is keyed by the custom domains EarthRanger advertises, never the
canonical *.auth0.com names behind them: EarthRanger validates a token's iss
against exactly the string its discovery document serves, so a token minted
through the canonical domain is refused on arrival.

Every parser answers an unusable document with None and never raises.
"""
import json
from dataclasses import dataclass
from typing import Optional

from .discovery import normalize_issuer, parse_absolute_url

DEVICE_CODE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"

# No offline_access: the registration issues no refresh token, by decision, so
# asking for one would only be refused.
DEFAULT_SCOPE = "openid profile email"

# RFC 8628 section 3.2: the interval to use when the server names none.
# Section 3.5 adds five seconds per slow_down.
DEFAULT_POLL_INTERVAL_SECONDS = 5
SLOW_DOWN_INCREMENT_SECONDS = 5

AUTHORIZATION_SERVER_METADATA_PATH = "/.well-known/openid-configuration"


@dataclass(frozen=True)
class AuthorizationServer:
    """Everything the device-code flow needs about one authorization server."""

    issuer: str
    client_id: str
    audience: str


@dataclass(frozen=True)
class DeviceAuthorization:
    """A device-authorization response (RFC 8628 section 3.2)."""

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: Optional[str]
    expires_in: int
    interval: int


KNOWN_AUTHORIZATION_SERVERS = {
    "https://auth-dev.pamdas.org": AuthorizationServer(
        issuer="https://auth-dev.pamdas.org",
        client_id="tpPAukxw0S8MXwZPcK6hwIEcqM0cAp5l",
        audience="https://dev.pamdas.org/api",
    ),
    "https://auth.pamdas.org": AuthorizationServer(
        issuer="https://auth.pamdas.org",
        client_id="JMzSKHVrOVjFYC6KjeONw9ZToPRw56uZ",
        audience="https://pamdas.org/api",
    ),
}


def select_authorization_server(metadata):
    """The first issuer in the site's list this release knows, or None."""
    if metadata is None:
        return None

    for candidate in metadata.authorization_servers:
        known = KNOWN_AUTHORIZATION_SERVERS.get(normalize_issuer(candidate))
        if known:
            return known
    return None


def authorization_server_metadata_url(issuer):
    """Where the authorization server describes itself (OIDC Discovery)."""
    return f"{normalize_issuer(issuer)}{AUTHORIZATION_SERVER_METADATA_PATH}"


def is_https_url(value):
    """Whether ``value`` is an absolute https URL: the bar for every URL the
    flow fetches from, posts to, or sends the user to. Never raises."""
    parsed = parse_absolute_url(value)
    return parsed is not None and parsed.scheme.lower() == 'https'


def _https_url(value):
    """``value`` if it is an absolute https URL, else None."""
    return value if is_https_url(value) else None


def _parsed_object(text):
    """``text`` as a JSON object, or None if it is anything else."""
    try:
        body = json.loads(text)
    except (TypeError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def parse_authorization_server_metadata(text, expected_issuer):
    """The ``(device_authorization_endpoint, token_endpoint)`` pair, or None.

    The document has to name the issuer we asked about (RFC 8414 section 3.3):
    that is what stops a redirect to the canonical Auth0 domain from minting
    tokens EarthRanger will reject.
    """
    body = _parsed_object(text)
    if body is None:
        return None

    issuer = body.get('issuer')
    if not isinstance(issuer, str):
        return None
    if normalize_issuer(issuer) != normalize_issuer(expected_issuer):
        return None

    device_authorization_endpoint = _https_url(
        body.get('device_authorization_endpoint'))
    token_endpoint = _https_url(body.get('token_endpoint'))
    if not device_authorization_endpoint or not token_endpoint:
        return None

    return (device_authorization_endpoint, token_endpoint)


def _non_empty_string(value):
    return value if isinstance(value, str) and value else None


def _positive_whole_number(value):
    """An integer as JSON carries one, above zero. ``True`` is not a duration."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value > 0 else None


def parse_device_authorization(text):
    """A device-authorization response, or None if we could not poll on it.

    An unusable ``interval`` falls back to the default rather than failing a
    flow that would otherwise work; every other field here is required.
    """
    body = _parsed_object(text)
    if body is None:
        return None

    device_code = _non_empty_string(body.get('device_code'))
    user_code = _non_empty_string(body.get('user_code'))
    verification_uri = _https_url(body.get('verification_uri'))
    expires_in = _positive_whole_number(body.get('expires_in'))
    if not (device_code and user_code and verification_uri) or expires_in is None:
        return None

    interval = _positive_whole_number(body.get('interval'))
    return DeviceAuthorization(
        device_code=device_code,
        user_code=user_code,
        verification_uri=verification_uri,
        verification_uri_complete=_https_url(
            body.get('verification_uri_complete')),
        expires_in=expires_in,
        interval=DEFAULT_POLL_INTERVAL_SECONDS if interval is None else interval,
    )


def parse_token_response(text):
    """An approved token response as a dict, or None if we could not use it.

    A refresh_token is dropped if one arrives. This flow does not refresh, by
    decision: a tenant that grants one anyway must not leave behind a
    credential the clients' shared refresh path would post to the site's
    legacy token endpoint.
    """
    body = _parsed_object(text)
    if body is None:
        return None
    if not _non_empty_string(body.get('access_token')):
        return None
    if not _non_empty_string(body.get('token_type')):
        return None
    if _positive_whole_number(body.get('expires_in')) is None:
        return None
    return {key: value for key, value in body.items() if key != 'refresh_token'}


def default_prompt_text(*, service_root, authorization):
    """What the user reads before going off to approve the code.

    Names the site, because a caller may hold clients for several, and shows
    the code, which RFC 8628 section 5.4 asks the user to confirm.
    """
    url = (authorization.verification_uri_complete
           or authorization.verification_uri)
    return (
        "You are about to authorize the EarthRanger Python Client to access "
        f"{service_root} as your user.\n"
        f"Open {url} in a browser and confirm that it shows the code "
        f"{authorization.user_code}.\n"
        "Waiting for approval..."
    )
