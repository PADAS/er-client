"""ERClient refuses credentials the site's discovery document rules out.

Where ``test_discovery_sync.py`` covers credentials that are merely legacy —
deprecated, still working, worth a warning — these are the ones the site's API
is certain to reject. The client says so before any request, so the caller sees
their real problem instead of a 401 that reads as a bad password.

A caller who brought their own token never calls ``login()``, so for those the
refusal happens in ``auth_headers()``, which every API call goes through.
"""
from unittest.mock import MagicMock

import pytest
import requests
from tests.auth.conftest import (AUTH0_ISSUER, JWT_TOKEN, JWT_WITH_ISSUER,
                                 auth_warnings, jwt_with_issuer)

from erclient.client import ERClient
from erclient.er_errors import (CREDENTIAL_SITE_MISMATCH, ERClientAuthWarning,
                                ERClientBadCredentials)

OTHER_ISSUER = "https://someone-elses-tenant.us.auth0.com"


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


class TestOpaqueTokenAtAMigratedSite:
    """A site listing only Auth0 rejects every token its own endpoint issued."""

    def test_auth_headers_raises_instead_of_returning_them(
        self, token_kwargs, serving, external_only_document,
        opaque_token_mismatch_message,
    ):
        serving(external_only_document)
        client = ERClient(**token_kwargs)

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert str(exc_info.value) == opaque_token_mismatch_message

    def test_every_later_call_raises_too_without_refetching(
        self, token_kwargs, patched_get, serving, external_only_document,
        opaque_token_mismatch_message,
    ):
        """A client holding a token the site cannot accept is unusable, not
        merely unlucky the first time."""
        serving(external_only_document)
        client = ERClient(**token_kwargs)

        for _ in range(3):
            with pytest.raises(ERClientBadCredentials) as exc_info:
                client.auth_headers()
            assert str(exc_info.value) == opaque_token_mismatch_message

        assert patched_get.call_count == 1

    def test_no_api_call_is_attempted(
        self, token_kwargs, serving, external_only_document,
    ):
        serving(external_only_document)
        client = ERClient(**token_kwargs)
        client._http_session = MagicMock()

        with pytest.raises(ERClientBadCredentials):
            client.get_me()

        assert not client._http_session.get.called

    def test_the_reason_names_no_request_because_there_was_none(
        self, token_kwargs, serving, external_only_document,
        opaque_token_mismatch_message,
    ):
        """Token mode posts to no token endpoint, so there is nothing to name."""
        serving(external_only_document)
        client = ERClient(**token_kwargs)

        with pytest.raises(ERClientBadCredentials):
            client.auth_headers()

        auth_error = client.last_auth_error
        assert auth_error.error == CREDENTIAL_SITE_MISMATCH
        assert auth_error.error_description == opaque_token_mismatch_message
        assert auth_error.url is None
        assert auth_error.grant_type is None
        assert auth_error.status_code is None
        assert auth_error.response_body is None

    def test_the_deprecation_warning_gives_way_to_the_error(
        self, token_kwargs, serving, external_only_document, recwarn,
    ):
        serving(external_only_document)
        client = ERClient(**token_kwargs)

        with pytest.raises(ERClientBadCredentials):
            client.auth_headers()

        assert auth_warnings(recwarn.list) == []


class TestJwtFromAnUnlistedIssuer:
    """DAS validates ``iss`` against the string discovery advertises, so a JWT
    from anywhere else is rejected on every kind of site."""

    @pytest.mark.parametrize(
        "issuers", [("das",), ("das", "auth0"), ("auth0",)],
        ids=["not_migrated", "migrating", "migrated"],
    )
    def test_it_is_refused_wherever_the_site_is_in_its_migration(
        self, service_root, serving, make_discovery_document, das_issuer,
        issuers, unlisted_issuer_message,
    ):
        lookup = {"das": das_issuer, "auth0": AUTH0_ISSUER}
        accepted = [lookup[name] for name in issuers]
        serving(make_discovery_document(*accepted))
        client = ERClient(service_root=service_root,
                          token=jwt_with_issuer(OTHER_ISSUER))

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert str(exc_info.value) == unlisted_issuer_message(
            OTHER_ISSUER, accepted)

    def test_the_issuer_is_named_as_we_compared_it(
        self, service_root, serving, external_only_document,
        unlisted_issuer_message,
    ):
        """Normalized, so the caller sees the string that failed to match."""
        serving(external_only_document)
        client = ERClient(service_root=service_root,
                          token=jwt_with_issuer(f"HTTPS://SOMEONE-ELSES-TENANT.US.AUTH0.COM/"))

        with pytest.raises(ERClientBadCredentials) as exc_info:
            client.auth_headers()

        assert str(exc_info.value) == unlisted_issuer_message(
            OTHER_ISSUER, [AUTH0_ISSUER])

    def test_no_api_call_is_attempted(
        self, service_root, serving, external_only_document,
    ):
        serving(external_only_document)
        client = ERClient(service_root=service_root,
                          token=jwt_with_issuer(OTHER_ISSUER))
        client._http_session = MagicMock()

        with pytest.raises(ERClientBadCredentials):
            client.get_me()

        assert not client._http_session.get.called


class TestJwtsTheSiteHasNoQuarrelWith:
    """Only an issuer we can read *and* the site does not list is refused."""

    def test_a_listed_issuer_differing_only_by_a_trailing_slash(
        self, service_root, serving, external_only_document, recwarn,
    ):
        serving(external_only_document)
        client = ERClient(service_root=service_root, token=JWT_WITH_ISSUER)

        headers = client.auth_headers()

        assert headers["Authorization"] == f"Bearer {JWT_WITH_ISSUER}"
        assert auth_warnings(recwarn.list) == []

    def test_a_listed_issuer_differing_only_by_host_case(
        self, service_root, serving, make_discovery_document,
    ):
        serving(make_discovery_document(AUTH0_ISSUER.upper()))
        client = ERClient(service_root=service_root, token=JWT_WITH_ISSUER)

        assert client.auth_headers()["Authorization"].startswith("Bearer ")

    def test_a_jwt_whose_payload_we_cannot_read(
        self, service_root, serving, external_only_document, recwarn,
    ):
        """Unreadable is not the same as wrong; the server still gets to judge."""
        serving(external_only_document)
        client = ERClient(service_root=service_root, token=JWT_TOKEN)

        headers = client.auth_headers()

        assert headers["Authorization"] == f"Bearer {JWT_TOKEN}"
        assert auth_warnings(recwarn.list) == []


class TestTokensTheSiteMayStillAccept:
    """The warn-versus-raise boundary, in token mode."""

    def test_an_opaque_token_at_a_migrating_site_still_only_warns(
        self, token_kwargs, serving, discovery_document,
    ):
        """A DAS token still works for a bypass_auth0 application there."""
        serving(discovery_document)
        client = ERClient(**token_kwargs)

        with pytest.warns(ERClientAuthWarning, match="looks like a legacy"):
            headers = client.auth_headers()

        assert headers["Authorization"].startswith("Bearer ")

    def test_an_opaque_token_at_a_site_that_has_not_migrated(
        self, token_kwargs, serving, make_discovery_document, das_issuer, recwarn,
    ):
        serving(make_discovery_document(das_issuer))
        client = ERClient(**token_kwargs)

        assert client.auth_headers()["Authorization"].startswith("Bearer ")
        assert auth_warnings(recwarn.list) == []


class TestWithoutDiscoveryThereIsNoTokenCheck:
    """No document, or no permission to fetch one, means the token is used."""

    def test_an_opaque_token_at_a_site_serving_no_document(
        self, token_kwargs, patched_get, make_requests_response,
    ):
        patched_get.return_value = make_requests_response(404, text="")
        client = ERClient(**token_kwargs)

        assert client.auth_headers()["Authorization"].startswith("Bearer ")

    def test_a_jwt_from_an_unlisted_issuer_at_such_a_site(
        self, service_root, patched_get, make_requests_response,
    ):
        patched_get.return_value = make_requests_response(404, text="")
        client = ERClient(service_root=service_root,
                          token=jwt_with_issuer(OTHER_ISSUER))

        assert client.auth_headers()["Authorization"].startswith("Bearer ")

    def test_opting_out_skips_the_check_along_with_the_warning(
        self, token_kwargs, patched_get, serving, external_only_document,
    ):
        serving(external_only_document)
        client = ERClient(**token_kwargs, discovery=False)

        assert client.auth_headers()["Authorization"].startswith("Bearer ")
        assert not patched_get.called
