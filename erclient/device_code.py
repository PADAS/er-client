"""RFC 8628 device authorization: tables, parsers, and the prompt.

Pure functions only — the clients own the HTTP, as in :mod:`erclient.discovery`.

An EarthRanger site's discovery document names the authorization servers it
accepts, but not what to send them: a device-code flow also needs a registered
``client_id`` and the API's ``audience``. Those come from the registration, so
they live here in a table keyed by issuer, overridable for a tenant this
release has never heard of.

The table keys are the **custom domains** EarthRanger advertises, never the
canonical ``*.auth0.com`` names behind them. EarthRanger validates a token's
``iss`` claim against exactly the string its discovery document serves, so a
token minted through the canonical domain is refused on arrival — by the server
and by this client's own issuer check alike.

Every parser here answers an unusable document with ``None`` and never raises:
the caller decides what a broken authorization server deserves.
"""
import json
from dataclasses import dataclass, replace
from typing import Optional

from .discovery import normalize_issuer, parse_absolute_url

DEVICE_CODE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"

# No offline_access: the registration issues no refresh token, by decision, so
# asking for one would only be refused.
DEFAULT_SCOPE = "openid profile email"

# RFC 8628 section 3.2: the polling interval to use when the authorization
# server does not name one. Section 3.5 adds five seconds per ``slow_down``.
DEFAULT_POLL_INTERVAL_SECONDS = 5
SLOW_DOWN_INCREMENT_SECONDS = 5

AUTHORIZATION_SERVER_METADATA_PATH = "/.well-known/openid-configuration"


@dataclass(frozen=True)
class AuthorizationServer:
    """Everything the device-code flow needs about one authorization server.

    ``issuer`` is normalized, so it compares equal to the same issuer written
    with a trailing slash or a differently-cased host.
    """

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


def _with_overrides(server, client_id, audience):
    """The table entry as the caller's overrides amend it."""
    overrides = {}
    if client_id:
        overrides['client_id'] = client_id
    if audience:
        overrides['audience'] = audience
    return replace(server, **overrides) if overrides else server


def select_authorization_server(metadata, *, issuer=None, client_id=None,
                                audience=None):
    """Which authorization server to run the flow against, or None.

    An explicit ``issuer`` settles it: known, and it comes from the table with
    any overrides applied; unknown, and the overrides have to supply the whole
    registration, since a ``client_id`` cannot be guessed. Either way it has to
    be an issuer identifier — see :func:`is_issuer_url` — or nothing is
    selected. Otherwise the site's own list decides, in the order it
    published — the first issuer this client knows wins. ``None`` means
    nothing here can start a flow, and the client turns that into the refusal
    that fits how it got here.
    """
    if issuer:
        if not is_issuer_url(issuer):
            return None
        normalized = normalize_issuer(issuer)
        known = KNOWN_AUTHORIZATION_SERVERS.get(normalized)
        if known:
            return _with_overrides(known, client_id, audience)
        if client_id and audience:
            return AuthorizationServer(
                issuer=normalized, client_id=client_id, audience=audience)
        return None

    if metadata is None:
        return None

    for candidate in metadata.authorization_servers:
        known = KNOWN_AUTHORIZATION_SERVERS.get(normalize_issuer(candidate))
        if known:
            return _with_overrides(known, client_id, audience)
    return None


def authorization_server_metadata_url(issuer):
    """Where the authorization server describes itself.

    OIDC Discovery rather than RFC 8414's ``oauth-authorization-server`` path:
    Auth0 serves the OIDC one, and the endpoints are read from the document
    rather than derived, so nothing here assumes a URL shape beyond this.
    """
    return f"{normalize_issuer(issuer)}{AUTHORIZATION_SERVER_METADATA_PATH}"


def is_https_url(value):
    """Whether ``value`` is an absolute ``https`` URL.

    The bar for every URL the flow fetches from, posts to, or sends the user
    to. It applies to the issuer override as much as to what an authorization
    server sends: its metadata document names the device and token endpoints,
    so fetching it in cleartext would let anyone on the path choose where a
    device code and, in time, an access token are posted. Never raises.
    """
    parsed = parse_absolute_url(value)
    return parsed is not None and parsed.scheme.lower() == 'https'


def is_issuer_url(value):
    """Whether ``value`` can be an authorization server's issuer identifier.

    RFC 8414 section 2: an ``https`` URL with no query or fragment. The
    second half matters here because :func:`authorization_server_metadata_url`
    appends the well-known path to the issuer as text, so a query would
    swallow the path and a fragment would hide it, and the metadata request
    would go somewhere else entirely. The check is on the characters rather
    than the parsed components, because ``urlparse`` cannot tell a bare ``?``
    or ``#`` from their absence and either one would still break the append.
    Never raises.
    """
    parsed = parse_absolute_url(value)
    return (parsed is not None and parsed.scheme.lower() == 'https'
            and '?' not in value and '#' not in value)


def _https_endpoint(value):
    """The value if it is an absolute https URL, else None."""
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

    RFC 8414 section 3.3 requires the document to name the issuer we asked
    about, and here that check is load-bearing rather than ceremonial: it is
    what stops a redirect to the canonical Auth0 domain from quietly minting
    tokens EarthRanger will reject. The endpoints must be absolute ``https``
    URLs, since a device code and, in time, an access token are posted to them.
    """
    body = _parsed_object(text)
    if body is None:
        return None

    issuer = body.get('issuer')
    if not isinstance(issuer, str):
        return None
    if normalize_issuer(issuer) != normalize_issuer(expected_issuer):
        return None

    device_authorization_endpoint = _https_endpoint(
        body.get('device_authorization_endpoint'))
    token_endpoint = _https_endpoint(body.get('token_endpoint'))
    if not device_authorization_endpoint or not token_endpoint:
        return None

    return (device_authorization_endpoint, token_endpoint)


def _non_empty_string(value):
    return value if isinstance(value, str) and value else None


def _whole_number(value):
    """An integer as JSON carries one. ``True`` is not a duration."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _positive_whole_number(value):
    """The same, for the fields that are only meaningful above zero.

    A ``0`` or negative ``interval`` is not a wait the poller can take, and a
    lifetime that has already run out leaves nothing to poll on.
    """
    number = _whole_number(value)
    return number if number is not None and number > 0 else None


def parse_device_authorization(text):
    """A device-authorization response, or None if we could not poll on it.

    The required fields are the ones the flow cannot run without: the code we
    poll with, the code and URL the user needs, and how long any of it is good
    for. The optional two are conveniences, so a malformed one falls back to
    its default rather than failing a flow that would otherwise work.

    Both verification URIs go through the same ``https`` check the endpoints
    do: they are printed to the user and, with ``open_browser=True``, handed
    to ``webbrowser.open()``, which is no place for whatever scheme an
    authorization server happened to send.
    """
    body = _parsed_object(text)
    if body is None:
        return None

    device_code = _non_empty_string(body.get('device_code'))
    user_code = _non_empty_string(body.get('user_code'))
    verification_uri = _https_endpoint(body.get('verification_uri'))
    expires_in = _positive_whole_number(body.get('expires_in'))
    if not (device_code and user_code and verification_uri) or expires_in is None:
        return None

    interval = _positive_whole_number(body.get('interval'))
    return DeviceAuthorization(
        device_code=device_code,
        user_code=user_code,
        verification_uri=verification_uri,
        verification_uri_complete=_https_endpoint(
            body.get('verification_uri_complete')),
        expires_in=expires_in,
        interval=DEFAULT_POLL_INTERVAL_SECONDS if interval is None else interval,
    )


def parse_token_response(text):
    """An approved token response as a dict, or None if we could not use it.

    A 2xx from the token endpoint is the flow succeeding, but the body still
    has to carry what the client will read from it: the token, the type that
    goes in front of it in an Authorization header (RFC 6749 section 5.1),
    and a lifetime to schedule the next sign-in by. A 204, an HTML page, or a
    JSON object missing any of those is not a token, and the caller must not
    be left half signed in by it.
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
    return body


def default_prompt_text(*, service_root, authorization):
    """What the user reads before going off to approve the code.

    Names the site, because a caller may hold clients for several; shows the
    code, because RFC 8628 section 5.4 asks the user to confirm the page shows
    the same one before they approve anything.
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
