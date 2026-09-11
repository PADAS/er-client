"""Telling a caller their password grant is on its way out: the site still
lists its own token endpoint, so the grant works, but it also lists Auth0."""
import logging

import pytest
from tests.auth.conftest import Reply, auth_warnings

from erclient import client as client_module
from erclient.er_errors import ERClientAuthWarning, ERClientBadCredentials

AUTH0_ISSUER = "https://auth-dev.pamdas.org"


@pytest.fixture
def das_issuer(service_root):
    return f"{service_root}/oauth2"


@pytest.fixture
def publishes(server, discovery_url, service_root):
    """Make the site publish the issuers a test names."""

    def _publish(*authorization_servers):
        server.always("GET", discovery_url, Reply(json_body={
            "resource": service_root,
            "authorization_servers": list(authorization_servers)}))

    return _publish


@pytest.fixture
def logged_in(client, server, ropc_kwargs, default_token_url, token_response):
    """A password-grant client whose token endpoint will answer."""
    server.respond("POST", default_token_url, json_body=token_response)
    return client.make(**ropc_kwargs)


@pytest.fixture
def warning_message(service_root):
    return (
        f"Site {service_root} supports EarthRanger's Auth0 sign-in. "
        "Username/password login through the site's legacy token endpoint "
        "still works but is deprecated and will stop working when the site "
        "completes its migration. Pass an Auth0-issued access token with "
        "token=, or construct the client with no credentials and call login() "
        "to sign in interactively."
    )


class TestASiteMidMigration:

    def test_the_password_grant_still_works_and_says_so(
            self, logged_in, publishes, das_issuer, warning_message):
        publishes(das_issuer, AUTH0_ISSUER)

        with pytest.warns(ERClientAuthWarning) as record:
            assert logged_in.login() is True

        assert str(record[0].message) == warning_message
        assert logged_in.auth["access_token"] == "access-token-1"

    def test_the_log_carries_it_too(self, logged_in, publishes, das_issuer,
                                    warning_message, caplog):
        publishes(das_issuer, AUTH0_ISSUER)

        with caplog.at_level(logging.WARNING):
            with pytest.warns(ERClientAuthWarning):
                logged_in.login()

        assert warning_message in caplog.text

    def test_it_is_not_blamed_on_the_library(self, logged_in, publishes,
                                             das_issuer):
        publishes(das_issuer, AUTH0_ISSUER)

        with pytest.warns(ERClientAuthWarning) as record:
            logged_in.login()

        # Blamed here, a caller could neither locate the call nor filter it by
        # module. The frame it names is the one that called login().
        assert record[0].filename != client_module.__file__

    def test_it_is_said_once_however_often_the_client_logs_in(
            self, logged_in, publishes, das_issuer):
        publishes(das_issuer, AUTH0_ISSUER)

        with pytest.warns(ERClientAuthWarning) as record:
            logged_in.login()
            logged_in.login()

        assert len(auth_warnings(record.list)) == 1


class TestWhenThereIsNothingToSay:

    def test_a_site_that_lists_only_its_own_issuer(self, logged_in, publishes,
                                                   das_issuer, recwarn):
        publishes(das_issuer)

        assert logged_in.login() is True
        assert auth_warnings(recwarn.list) == []

    def test_a_site_that_lists_nothing(self, logged_in, publishes, recwarn):
        publishes()

        assert logged_in.login() is True
        assert auth_warnings(recwarn.list) == []

    def test_a_site_that_serves_no_document(self, logged_in, recwarn):
        assert logged_in.login() is True
        assert auth_warnings(recwarn.list) == []

    def test_a_site_that_has_finished_migrating_is_refused_not_warned(
            self, client, server, ropc_kwargs, publishes, recwarn):
        publishes(AUTH0_ISSUER)
        client.make(**ropc_kwargs)

        with pytest.raises(ERClientBadCredentials):
            client.auth_headers()

        assert auth_warnings(recwarn.list) == []

    def test_discovery_false_leaves_the_client_nothing_to_warn_from(
            self, client, server, ropc_kwargs, default_token_url,
            token_response, publishes, recwarn):
        publishes(f"{ropc_kwargs['service_root']}/oauth2", AUTH0_ISSUER)
        server.respond("POST", default_token_url, json_body=token_response)
        client.make(**ropc_kwargs, discovery=False)

        assert client.login() is True
        assert auth_warnings(recwarn.list) == []

    def test_a_client_signing_in_interactively_is_not_a_legacy_caller(
            self, client, server, service_root, publishes, recwarn, no_tty):
        publishes(f"{service_root}/oauth2", AUTH0_ISSUER)
        client.make(service_root=service_root)

        with pytest.raises(ERClientBadCredentials):
            client.auth_headers()

        assert auth_warnings(recwarn.list) == []
