"""Shared fixtures for the auth tests.

Every test here mocks HTTP with respx: the discovery endpoint and both token
legs are the only network this module ever touches. The hostnames are the
same invented ones the rest of the suite uses -- nothing here should resolve,
and no real EarthRanger site or Auth0 tenant is named.
"""
import pytest

SITE = "https://fake-site.erdomain.org"
DISCOVERY_URL = SITE + "/.well-known/oauth-protected-resource"

# The issuer a site advertises when it is its own authorization server:
# the site origin plus /oauth2.
DAS_ISSUER = SITE + "/oauth2"

# An external tenant issuer, shaped the way sites advertise one: its own host,
# with a trailing slash. Invented, like every other host in this suite.
AUTH0_ISSUER = "https://fake-auth.erdomain.org/"


@pytest.fixture
def discovery_document():
    """Build an RFC 9728 protected-resource document shaped the way a site serves one.

    ``resource`` is the site origin, carrying no trailing slash.
    """
    def _build(authorization_servers, resource=SITE):
        return {
            "resource": resource,
            "authorization_servers": list(authorization_servers),
        }
    return _build
