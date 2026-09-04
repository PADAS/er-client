"""ERClient refuses credentials the site's discovery document rules out.

Where ``test_discovery_sync.py`` covers credentials that are merely legacy —
deprecated, still working, worth a warning — these are the ones the site's API
is certain to reject. The client says so before any request, so the caller sees
their real problem instead of a 401 that reads as a bad password.

Password grant only, so far; the token cases arrive with the token-mode check.
"""
import pytest
import requests
from tests.auth.conftest import auth_warnings

from erclient.client import ERClient
from erclient.er_errors import (CREDENTIAL_SITE_MISMATCH, ERClientAuthWarning,
                                ERClientBadCredentials)


class TestPasswordGrantAtAMigratedSite:
    """A site listing only Auth0 will reject whatever its token endpoint issues."""

    def test_login_refuses_without_posting(
        self, ropc_kwargs, patched_post, serving, external_only_document,
    ):
        serving(external_only_document)
        client = ERClient(**ropc_kwargs)

        assert client.login() is False
        assert not patched_post.called

    def test_no_credentials_are_left_on_the_client(
        self, ropc_kwargs, patched_post, serving, external_only_document,
    ):
        """A refused login must not leave a half-authenticated client behind."""
        serving(external_only_document)
        client = ERClient(**ropc_kwargs)

        client.login()

        assert client.auth is None
        assert not client._auth_is_valid()

    def test_the_reason_is_recorded_for_the_caller(
        self, ropc_kwargs, patched_post, serving, external_only_document,
        password_mismatch_message, default_token_url,
    ):
        """login() only returns a bool, so last_auth_error carries the why."""
        serving(external_only_document)
        client = ERClient(**ropc_kwargs)

        client.login()

        auth_error = client.last_auth_error
        assert auth_error.error == CREDENTIAL_SITE_MISMATCH
        assert auth_error.error_description == password_mismatch_message
        assert auth_error.url == default_token_url
        assert auth_error.grant_type == "password"

    def test_no_server_was_consulted(
        self, ropc_kwargs, patched_post, serving, external_only_document,
    ):
        """Nothing was sent, so there is no status and no body to report."""
        serving(external_only_document)
        client = ERClient(**ropc_kwargs)

        client.login()

        assert client.last_auth_error.status_code is None
        assert client.last_auth_error.response_body is None

    def test_auth_headers_raises_bad_credentials(
        self, ropc_kwargs, patched_post, serving, external_only_document,
        password_mismatch_message,
    ):
        serving(external_only_document)
        client = ERClient(**ropc_kwargs)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert not patched_post.called
        assert str(exc_info.value) == password_mismatch_message

    def test_the_message_carries_no_server_suffixes(
        self, ropc_kwargs, patched_post, serving, external_only_document,
    ):
        """ERClientException appends status and body when it has them; here it must not."""
        serving(external_only_document)
        client = ERClient(**ropc_kwargs)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert exc_info.value.status_code is None
        assert exc_info.value.response_body is None

    def test_the_deprecation_warning_gives_way_to_the_error(
        self, ropc_kwargs, patched_post, serving, external_only_document, recwarn,
    ):
        """One clear failure, not a warning and then a silent False."""
        serving(external_only_document)
        client = ERClient(**ropc_kwargs)

        client.login()

        assert auth_warnings(recwarn.list) == []


class TestTheCheckIsPerLogin:
    """Discovery is refetched on every login, so a refusal is never sticky."""

    def test_a_site_that_lists_its_own_issuer_again_can_be_logged_into(
        self, ropc_kwargs, patched_post, serving, external_only_document,
        discovery_document,
    ):
        serving(external_only_document)
        client = ERClient(**ropc_kwargs)
        assert client.login() is False

        serving(discovery_document)

        with pytest.warns(ERClientAuthWarning):
            assert client.login() is True
        assert patched_post.called
        assert client.last_auth_error is None


class TestSitesThatStillAcceptAPassword:
    """The warn-versus-raise boundary: only "Auth0 and nothing else" raises."""

    def test_a_migrating_site_still_only_warns(
        self, ropc_kwargs, patched_post, serving, discovery_document,
    ):
        """A site listing both issuers may still honour the password grant."""
        serving(discovery_document)
        client = ERClient(**ropc_kwargs)

        with pytest.warns(ERClientAuthWarning, match="still works but is deprecated"):
            assert client.login() is True

        assert patched_post.called

    def test_a_site_that_has_not_migrated_says_nothing(
        self, ropc_kwargs, patched_post, serving, make_discovery_document,
        das_issuer, recwarn,
    ):
        serving(make_discovery_document(das_issuer))
        client = ERClient(**ropc_kwargs)

        assert client.login() is True
        assert auth_warnings(recwarn.list) == []


class TestWithoutDiscoveryThereIsNoCheck:
    """No document, or no permission to fetch one, means the login proceeds."""

    def test_a_site_serving_no_document(
        self, ropc_kwargs, patched_get, patched_post, make_requests_response,
    ):
        patched_get.return_value = make_requests_response(404, text="")
        client = ERClient(**ropc_kwargs)

        assert client.login() is True
        assert patched_post.called
        assert client.last_auth_error is None

    def test_a_site_we_cannot_reach_for_discovery(
        self, ropc_kwargs, patched_get, patched_post,
    ):
        patched_get.side_effect = requests.ConnectionError("no route to host")
        client = ERClient(**ropc_kwargs)

        assert client.login() is True
        assert patched_post.called

    def test_opting_out_skips_the_check_along_with_the_warning(
        self, ropc_kwargs, patched_get, patched_post, serving,
        external_only_document,
    ):
        """discovery=False means never asking, so there is nothing to refuse on."""
        serving(external_only_document)
        client = ERClient(**ropc_kwargs, discovery=False)

        assert client.login() is True
        assert not patched_get.called
        assert patched_post.called
