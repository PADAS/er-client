"""ERClient discovery: fetching the site's protected-resource metadata, and
warning when the credentials in hand look legacy for that site.

Discovery is advisory. Every failure mode has the same outcome: no metadata,
nothing raised, nothing logged above debug. A caller with working credentials
and an unreachable discovery endpoint must still be able to log in.

The warnings are matched here on a distinctive fragment rather than in full;
``tests/test_discovery.py`` pins the exact wording of every message, so it
stays the one place to edit when the wording changes.
"""
import json
import logging
from unittest.mock import MagicMock, patch

import pytest
import requests
from tests.auth.conftest import AUTH0_ISSUER, JWT_TOKEN, auth_warnings

from erclient.client import ERClient
from erclient.er_errors import ERClientAuthWarning


class TestDiscoverySucceeds:
    """The happy path: a site that serves the document."""

    def test_returns_and_stores_the_metadata(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document, service_root,
    ):
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        metadata = client.discover()

        assert metadata.resource == service_root
        assert metadata.authorization_servers == (
            f"{service_root}/oauth2", AUTH0_ISSUER)
        assert client.protected_resource_metadata is metadata

    def test_fetches_the_well_known_url(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document, discovery_url,
    ):
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        client.discover()

        assert patched_get.call_args.args[0] == discovery_url

    def test_sends_no_credentials(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document,
    ):
        """The document is public; sending auth would mean logging in first."""
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        client.discover()

        assert "Authorization" not in patched_get.call_args.kwargs["headers"]

    def test_identifies_the_client_and_asks_for_json(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document,
    ):
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        client.discover()

        assert patched_get.call_args.kwargs["headers"] == {
            "User-Agent": client.user_agent,
            "Accept": "application/json",
        }

    def test_uses_a_short_timeout(
        self, ropc_kwargs, patched_get, make_requests_response,
        discovery_document,
    ):
        """An advisory read must not stall a login behind a slow site."""
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)

        client.discover()

        assert patched_get.call_args.kwargs["timeout"] == 5


class TestDiscoveryFails:
    """Every failure is the same answer: no metadata, and nothing raised."""

    @pytest.mark.parametrize(
        "status_code, text",
        [
            (404, ""),
            (500, "<html><body>Server Error</body></html>"),
            (200, "<html><body>Single Page App</body></html>"),
            (200, json.dumps({"resource": "https://other-site.erdomain.org",
                              "authorization_servers": [AUTH0_ISSUER]})),
        ],
        ids=["not_found", "server_error",
             "not_json", "resource_is_another_host"],
    )
    def test_unusable_responses_yield_no_metadata(
        self, ropc_kwargs, patched_get, make_requests_response, status_code, text,
    ):
        patched_get.return_value = make_requests_response(
            status_code, text=text)
        client = ERClient(**ropc_kwargs)

        assert client.discover() is None
        assert client.protected_resource_metadata is None

    @pytest.mark.parametrize(
        "exception",
        [
            requests.ConnectionError("no route to host"),
            requests.Timeout("timed out"),
        ],
        ids=["connection_error", "timeout"],
    )
    def test_transport_errors_are_swallowed(
        self, ropc_kwargs, patched_get, exception,
    ):
        """A site we cannot reach for discovery is not a reason to refuse a login."""
        patched_get.side_effect = exception
        client = ERClient(**ropc_kwargs)

        assert client.discover() is None
        assert client.protected_resource_metadata is None

    def test_a_later_failure_clears_earlier_metadata(
        self, ropc_kwargs, patched_get, make_requests_response, discovery_document,
    ):
        """The property reports the most recent fetch, not the best one."""
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs)
        client.discover()

        patched_get.return_value = make_requests_response(404, text="")
        client.discover()

        assert client.protected_resource_metadata is None


class TestDiscoveryIsSkipped:
    """Cases where there is nothing to ask, or nobody to ask."""

    def test_no_metadata_before_the_first_fetch(self, ropc_kwargs, patched_get):
        client = ERClient(**ropc_kwargs)

        assert client.protected_resource_metadata is None
        assert not patched_get.called

    def test_a_client_without_a_service_root_asks_nobody(self, patched_get):
        client = ERClient(username="test-user", password="test-password")

        assert client.discover() is None
        assert client.protected_resource_metadata is None
        assert not patched_get.called

    def test_opting_out_does_not_disable_an_explicit_discover(
        self, ropc_kwargs, patched_get, make_requests_response, discovery_document,
    ):
        """discovery=False turns off the automatic fetches, not the method."""
        patched_get.return_value = make_requests_response(
            200, json_data=discovery_document)
        client = ERClient(**ropc_kwargs, discovery=False)

        assert client.discover() is not None
        assert patched_get.called


@pytest.mark.filterwarnings("ignore::erclient.er_errors.ERClientAuthWarning")
class TestLoginDiscovers:
    """A password grant is a decision about auth, so it asks the site first."""

    def test_discovery_precedes_the_token_request(
        self, ropc_kwargs, patched_get, patched_post, serving, discovery_document,
    ):
        """Ordering, not just counts: the answer is worthless after the POST."""
        serving(discovery_document)
        calls = MagicMock()
        calls.attach_mock(patched_get, "get")
        calls.attach_mock(patched_post, "post")
        client = ERClient(**ropc_kwargs)

        client.login()

        assert [name for name, _, _ in calls.mock_calls] == ["get", "post"]

    def test_every_login_refetches(
        self, ropc_kwargs, patched_get, patched_post, serving, discovery_document,
    ):
        """No cache: a site that migrates mid-process is noticed at the next login."""
        serving(discovery_document)
        client = ERClient(**ropc_kwargs)

        client.login()
        client.login()
        client.login()

        assert patched_get.call_count == 3

    def test_refreshing_does_not_discover(
        self, ropc_kwargs, patched_get, patched_post, serving, discovery_document,
    ):
        """A refresh decides nothing about which credentials to use."""
        serving(discovery_document)
        client = ERClient(**ropc_kwargs)
        client.login()
        patched_get.reset_mock()

        client.refresh_token()

        assert not patched_get.called

    def test_opting_out_keeps_login_offline_but_for_the_token_request(
        self, ropc_kwargs, patched_get, patched_post, serving, discovery_document,
    ):
        serving(discovery_document)
        client = ERClient(**ropc_kwargs, discovery=False)

        client.login()
        client.refresh_token()

        assert not patched_get.called

    def test_an_issuer_override_does_not_keep_login_offline(
        self, ropc_kwargs, patched_get, patched_post, serving, discovery_document,
    ):
        """device_code_issuer= skips discovery for the interactive sign-in only.

        A password client is asking a different question — whether the site
        still accepts its credentials — and the override does not answer it.
        """
        serving(discovery_document)
        client = ERClient(**ropc_kwargs,
                          device_code_issuer="https://auth-dev.pamdas.org")

        client.login()

        assert patched_get.call_count == 1


class TestDiscoveryFailuresLeaveLoginAlone:
    """Whatever goes wrong with discovery, the login is unaffected.

    Not folded into ``TestLoginDiscovers``: that class silences the warning
    category, and half of what these assert is that no warning is issued.
    """

    @pytest.mark.parametrize(
        "status_code, text, exception",
        [
            (404, "", None),
            (500, "<html><body>Server Error</body></html>", None),
            (200, "<html><body>Single Page App</body></html>", None),
            (200, json.dumps({"resource": "https://other-site.erdomain.org",
                              "authorization_servers": [AUTH0_ISSUER]}), None),
            (None, None, requests.ConnectionError("no route to host")),
            (None, None, requests.Timeout("timed out")),
        ],
        ids=[
            "not_found",
            "server_error",
            "not_json",
            # What a redirect to another site's document looks like by the
            # time it reaches the parser.
            "resource_is_another_host",
            "connection_error",
            "timeout",
        ],
    )
    def test_the_login_still_proceeds_and_says_nothing(
        self, ropc_kwargs, patched_get, patched_post, make_requests_response,
        status_code, text, exception, recwarn,
    ):
        if exception is not None:
            patched_get.side_effect = exception
        else:
            patched_get.return_value = make_requests_response(
                status_code, text=text)
        client = ERClient(**ropc_kwargs)

        assert client.login() is True
        assert patched_post.called
        assert auth_warnings(recwarn.list) == []


@pytest.mark.filterwarnings("ignore::erclient.er_errors.ERClientAuthWarning")
class TestTokenModeDiscovers:
    """A caller who brought their own token never calls login(), so
    auth_headers() is the only place left to look at the site."""

    def test_the_first_call_discovers(
        self, token_kwargs, patched_get, serving, discovery_document,
    ):
        serving(discovery_document)
        client = ERClient(**token_kwargs)

        client.auth_headers()

        assert patched_get.call_count == 1

    def test_later_calls_issue_nothing(
        self, token_kwargs, patched_get, serving, discovery_document,
    ):
        """Every API call goes through auth_headers(); only the first may fetch."""
        serving(discovery_document)
        client = ERClient(**token_kwargs)

        for _ in range(6):
            client.auth_headers()

        assert patched_get.call_count == 1

    def test_the_token_endpoint_is_left_alone(
        self, token_kwargs, patched_get, patched_post, serving, discovery_document,
    ):
        serving(discovery_document)
        client = ERClient(**token_kwargs)

        client.auth_headers()

        assert not patched_post.called

    def test_opting_out_keeps_token_mode_offline(
        self, token_kwargs, patched_get, serving, discovery_document,
    ):
        serving(discovery_document)
        client = ERClient(**token_kwargs, discovery=False)

        client.auth_headers()

        assert not patched_get.called

    def test_an_issuer_override_does_not_keep_token_mode_offline(
        self, token_kwargs, patched_get, serving, discovery_document,
    ):
        """device_code_issuer= skips discovery for the interactive sign-in only;
        a client that brought a token still has to learn whether the site
        accepts it."""
        serving(discovery_document)
        client = ERClient(**token_kwargs,
                          device_code_issuer="https://auth-dev.pamdas.org")

        client.auth_headers()

        assert patched_get.call_count == 1


class TestWarnsAboutLegacyCredentials:
    """The warning table, from the client's side."""

    def test_password_grant_at_a_migrating_site(
        self, ropc_kwargs, patched_post, serving, discovery_document, caplog,
    ):
        serving(discovery_document)
        client = ERClient(**ropc_kwargs)

        with caplog.at_level(logging.WARNING):
            with pytest.warns(ERClientAuthWarning, match="still works but is deprecated"):
                client.login()

        assert "still works but is deprecated" in caplog.text

    def test_opaque_token_at_a_migrating_site(
        self, token_kwargs, serving, discovery_document, caplog,
    ):
        serving(discovery_document)
        client = ERClient(**token_kwargs)

        with caplog.at_level(logging.WARNING):
            with pytest.warns(ERClientAuthWarning, match="looks like a legacy"):
                client.auth_headers()

        assert "looks like a legacy" in caplog.text

    def test_the_warning_offers_interactive_sign_in(
        self, ropc_kwargs, patched_post, serving, discovery_document,
    ):
        """The way out of a deprecated credential is named, not just implied."""
        serving(discovery_document)
        client = ERClient(**ropc_kwargs)

        with pytest.warns(
            ERClientAuthWarning,
            match="call login\\(\\) to sign in interactively",
        ):
            client.login()

    def test_the_same_warning_is_issued_once_per_client(
        self, ropc_kwargs, patched_get, patched_post, serving, discovery_document,
        caplog, recwarn,
    ):
        """A retry loop must not turn one deprecation into a wall of noise."""
        serving(discovery_document)
        client = ERClient(**ropc_kwargs)

        with caplog.at_level(logging.WARNING):
            client.login()
            client.login()

        assert len(auth_warnings(recwarn.list)) == 1
        assert len(
            [r for r in caplog.records if "Auth0" in r.getMessage()]) == 1
        assert patched_get.call_count == 2


class TestStaysSilent:
    """Silence is the default: only an external issuer makes credentials legacy."""

    def test_password_grant_at_a_site_that_has_not_migrated(
        self, ropc_kwargs, patched_post, serving, make_discovery_document,
        das_issuer, recwarn,
    ):
        serving(make_discovery_document(das_issuer))
        client = ERClient(**ropc_kwargs)

        client.login()

        assert auth_warnings(recwarn.list) == []

    def test_opaque_token_at_a_site_that_has_not_migrated(
        self, token_kwargs, serving, make_discovery_document, das_issuer, recwarn,
    ):
        serving(make_discovery_document(das_issuer))
        client = ERClient(**token_kwargs)

        client.auth_headers()

        assert auth_warnings(recwarn.list) == []

    @pytest.mark.parametrize(
        "issuers",
        [("das", "auth0"), ("auth0",)],
        ids=["migrating", "migrated"],
    )
    def test_a_jwt_is_never_warned_about(
        self, service_root, serving, make_discovery_document, das_issuer,
        issuers, recwarn,
    ):
        """A modern token is what the warnings are asking callers to move to."""
        lookup = {"das": das_issuer, "auth0": AUTH0_ISSUER}
        serving(make_discovery_document(*(lookup[name] for name in issuers)))
        client = ERClient(service_root=service_root, token=JWT_TOKEN)

        client.auth_headers()

        assert auth_warnings(recwarn.list) == []

    def test_a_site_with_no_metadata_says_nothing(
        self, ropc_kwargs, patched_get, patched_post, make_requests_response, recwarn,
    ):
        """Unavailable metadata is not evidence of anything."""
        patched_get.return_value = make_requests_response(404, text="")
        client = ERClient(**ropc_kwargs)

        client.login()

        assert auth_warnings(recwarn.list) == []

    def test_opting_out_silences_even_a_fully_migrated_site(
        self, ropc_kwargs, patched_get, patched_post, serving,
        make_discovery_document, recwarn,
    ):
        """discovery=False means never asking, so there is nothing to warn about."""
        serving(make_discovery_document(AUTH0_ISSUER))
        client = ERClient(**ropc_kwargs, discovery=False)

        client.login()

        assert not patched_get.called
        assert auth_warnings(recwarn.list) == []


class TestTokenTransportErrorsStillPropagate:
    """Discovery swallows its own transport errors; the token endpoint's are
    still the caller's to see.

    Both halves matter. A caller with working credentials and an unreachable
    discovery endpoint must still be able to log in, and a caller whose token
    endpoint is unreachable must still get the real transport error rather
    than a classified login failure or a bare False.
    """

    def test_a_connection_error_on_the_token_post_is_raised_raw(
        self, ropc_kwargs, patched_get, make_requests_response,
    ):
        patched_get.return_value = make_requests_response(404, text="")
        client = ERClient(**ropc_kwargs)

        with patch("erclient.client.requests.post") as mock_post:
            mock_post.side_effect = requests.ConnectionError(
                "no route to host")

            with pytest.raises(requests.ConnectionError):
                client.login()

    def test_the_same_when_discovery_did_serve_a_document(
        self, ropc_kwargs, serving, discovery_document,
    ):
        """Having metadata in hand changes nothing about how the POST fails."""
        serving(discovery_document)
        client = ERClient(**ropc_kwargs)

        with patch("erclient.client.requests.post") as mock_post:
            mock_post.side_effect = requests.ConnectionError(
                "no route to host")

            with pytest.warns(ERClientAuthWarning):
                with pytest.raises(requests.ConnectionError):
                    client.login()


class TestWarningsPointAtTheCaller:
    """A caller holding several clients has to see which line warned.

    Without a ``stacklevel`` every one of these reports a line inside
    ``client.py``, which tells the reader nothing they did not know.
    """

    def test_the_password_grant_warning_blames_the_login_call(
        self, ropc_kwargs, patched_post, serving, discovery_document,
    ):
        serving(discovery_document)
        client = ERClient(**ropc_kwargs)

        with pytest.warns(ERClientAuthWarning) as record:
            client.login()

        assert record[0].filename == __file__

    def test_the_token_mode_warning_blames_the_auth_headers_call(
        self, token_kwargs, serving, discovery_document,
    ):
        """A different depth: this one comes up through _discover_for_token_mode."""
        serving(discovery_document)
        client = ERClient(**token_kwargs)

        with pytest.warns(ERClientAuthWarning) as record:
            client.auth_headers()

        assert record[0].filename == __file__
