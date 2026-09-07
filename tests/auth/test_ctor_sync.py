"""Characterization tests for ERClient construction and its lazy auth paths.

Every assertion here describes behavior on the current implementation, warts
included. A wart that is still locked in carries a `# wart:` comment; when a
later step fixes one, the assertion is flipped in the same commit as the source
change, so the change is deliberate rather than a surprise failure.

The sync client's token requests go through the *module-level* ``requests.post``
(not ``self._http_session``), so these tests patch ``erclient.client.requests.post``.
"""
import json
import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytz
import requests
from tests.auth.conftest import auth_warnings

from erclient.client import AsyncERClient, ERClient
from erclient.er_errors import (ERClientAuthWarning, ERClientBadCredentials,
                                ERClientBadRequest, ERClientException,
                                ERClientInternalError)
from erclient.version import __version__


class TestConstruction:
    """Construction is offline and never validates what it is given."""

    @pytest.mark.parametrize(
        "kwargs_name",
        ["ropc_kwargs", "token_kwargs"],
        ids=["ropc", "pre_acquired_token"],
    )
    def test_issues_no_http_request(self, request, kwargs_name):
        """__init__ never contacts the network, whatever credentials are supplied."""
        kwargs = request.getfixturevalue(kwargs_name)
        with patch("erclient.client.requests.post") as mock_post, patch(
            "erclient.client.requests.get"
        ) as mock_get, patch("erclient.client.requests.Session") as mock_session:
            session = MagicMock()
            mock_session.return_value = session

            ERClient(**kwargs)

            assert not mock_post.called
            assert not mock_get.called
            assert not session.post.called
            assert not session.get.called
            assert not session.request.called

    def test_unknown_kwargs_are_silently_ignored(self, service_root):
        """Unrecognized kwargs neither raise nor become attributes."""
        client = ERClient(service_root=service_root,
                          not_a_real_option="whatever")

        assert not hasattr(client, "not_a_real_option")

    def test_positional_argument_is_rejected(self, service_root):
        """The constructor is kwargs-only."""
        with pytest.raises(TypeError):
            ERClient(service_root)

    def test_common_attributes_are_stored_as_given(self, service_root):
        """Credentials and identifiers are stored verbatim."""
        client = ERClient(
            service_root=service_root,
            username="a-user",
            password="a-password",
            client_id="a-client-id",
            provider_key="a-provider-key",
            realtime_url="https://realtime.erdomain.org",
        )

        assert client.username == "a-user"
        assert client.password == "a-password"
        assert client.client_id == "a-client-id"
        assert client.provider_key == "a-provider-key"
        assert client.realtime_url == "https://realtime.erdomain.org"
        assert client.user_agent == f"das-client/{__version__}"
        assert client.logger.name == "ERClient"

    def test_omitted_attributes_default_to_none(self, service_root):
        """Anything not supplied is stored as None rather than being absent."""
        client = ERClient(service_root=service_root)

        assert client.username is None
        assert client.password is None
        assert client.client_id is None
        assert client.provider_key is None
        assert client.realtime_url is None
        assert client.token is None

    class TestTokenUrl:
        """Where the client will post, decided entirely at construction time."""

        def test_defaults_to_relative_url_without_service_root(self):
            """Omitting service_root is accepted and produces an unusable URL."""
            client = ERClient()

            assert client.service_root == ""
            assert client.token_url == "/oauth2/token"  # wart: not a usable URL

        @pytest.mark.parametrize(
            "service_root_input",
            [
                "https://example.com",
                "https://example.com/",
                "https://example.com/api",
                "https://example.com/api/",
                "https://example.com/api/v1.0",
                "https://example.com/api/v2.0",
            ],
            ids=[
                "base_no_slash",
                "base_trailing_slash",
                "ends_with_api",
                "ends_with_api_slash",
                "full_v1",
                "full_v2",
            ],
        )
        def test_derives_from_normalized_service_root(self, service_root_input):
            """Built from the normalized base, so it never carries /api or a double slash."""
            client = ERClient(service_root=service_root_input)

            assert client.token_url == "https://example.com/oauth2/token"

        def test_explicit_value_is_used_verbatim(self, service_root, custom_token_url):
            """An explicit token_url wins; service_root does not influence it."""
            client = ERClient(service_root=service_root,
                              token_url=custom_token_url)

            assert client.token_url == custom_token_url


class TestPreAcquiredToken:
    """token= mode: auth is complete at construction and never refreshed."""

    def test_sets_auth_and_pins_expiry_to_2099(self, token_kwargs):
        """A supplied token is wrapped as Bearer auth that effectively never expires."""
        client = ERClient(**token_kwargs)

        assert client.auth == {
            "token_type": "Bearer",
            "access_token": token_kwargs["token"],
        }
        assert client.auth_expires == datetime(2099, 1, 1, tzinfo=pytz.utc)
        assert client.token == token_kwargs["token"]

    def test_auth_headers_issue_no_token_request(self, token_kwargs):
        """auth_headers() serves the supplied token without contacting the endpoint."""
        client = ERClient(**token_kwargs)

        with patch("erclient.client.requests.post") as mock_post:
            headers = client.auth_headers()

            assert headers == {
                "Authorization": f"Bearer {token_kwargs['token']}",
                "Accept-Type": "application/json",
            }
            assert not mock_post.called

    def test_repeated_auth_headers_never_expire(self, token_kwargs):
        """The pinned 2099 expiry means repeated calls never trip a refresh."""
        client = ERClient(**token_kwargs)

        with patch("erclient.client.requests.post") as mock_post:
            for _ in range(3):
                client.auth_headers()

            assert not mock_post.called

    def test_token_wins_over_supplied_credentials(self, ropc_kwargs, token_kwargs):
        """When both are given the token is used; the credentials are kept but unused."""
        with pytest.warns(ERClientAuthWarning):
            client = ERClient(**{**ropc_kwargs, **token_kwargs})

        with patch("erclient.client.requests.post") as mock_post:
            headers = client.auth_headers()

        assert headers["Authorization"] == f"Bearer {token_kwargs['token']}"
        assert not mock_post.called
        assert client.username == ropc_kwargs["username"]
        assert client.password == ropc_kwargs["password"]

    @pytest.mark.parametrize("credential", ["username", "password"])
    def test_supplying_both_kinds_of_credential_is_worth_saying(
        self, service_root, token_kwargs, credential, caplog,
    ):
        """Silently ignoring half of what a caller passed is how they end up
        debugging the wrong credentials."""
        with caplog.at_level(logging.WARNING):
            with pytest.warns(ERClientAuthWarning) as recorded:
                ERClient(**token_kwargs, **{credential: "test-value"})

        assert str(recorded[0].message) == (
            "Both token= and username/password were supplied; token= takes "
            "precedence and the username/password are ignored."
        )
        assert "token= takes precedence" in caplog.text

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"token": "not-a-real-token"},
            {"username": "test-user", "password": "test-password"},
            {"token": "", "username": "test-user", "password": "test-password"},
        ],
        ids=["token_alone", "credentials_alone", "empty_token_is_no_token"],
    )
    def test_one_kind_of_credential_is_unremarkable(
        self, service_root, kwargs, recwarn,
    ):
        ERClient(service_root=service_root, **kwargs)

        assert auth_warnings(recwarn.list) == []

    def test_the_warning_costs_no_http(self, ropc_kwargs, token_kwargs):
        """Construction still touches nothing; only auth_headers() may."""
        with patch("erclient.client.requests.get") as mock_get:
            with pytest.warns(ERClientAuthWarning):
                ERClient(**{**ropc_kwargs, **token_kwargs})

            assert not mock_get.called

    def test_empty_token_is_no_token_at_all(self, service_root):
        """token="" is falsy, so the token branch is skipped entirely.

        It used to fall through to a password grant of ``None``s. It now falls
        through to the interactive sign-in, which is what a client holding no
        credentials should do.
        """
        client = ERClient(service_root=service_root, token="")

        assert client.auth is None
        assert client.token == ""
        assert client._uses_device_code() is True

    def test_empty_token_alongside_credentials_still_means_the_password_grant(
        self, service_root
    ):
        """The legacy path is chosen by the legacy kwargs, not by the empty one."""
        client = ERClient(service_root=service_root, token="",
                          username="u", password="p")

        assert client._uses_device_code() is False

    def test_token_none_is_same_as_omitted(self, service_root):
        """An explicit token=None behaves exactly like omitting the kwarg."""
        explicit = ERClient(service_root=service_root, token=None)
        omitted = ERClient(service_root=service_root)

        assert explicit.auth is omitted.auth is None
        assert explicit.token is omitted.token is None
        assert explicit.auth_expires == omitted.auth_expires

    def test_rejected_token_surfaces_from_the_api_call(
        self, token_kwargs, make_requests_response
    ):
        """A bad token is discovered by the API, not by the token endpoint."""
        client = ERClient(**token_kwargs)
        unauthorized = make_requests_response(
            401, json_data={"status": {"detail": "Invalid token."}}
        )

        with patch("erclient.client.requests.post") as mock_post, patch.object(
            client._http_session, "get", return_value=unauthorized
        ) as mock_get:
            with pytest.raises(ERClientBadCredentials) as exc_info:
                client.get_me()

            assert mock_get.called
            assert not mock_post.called
            assert "Invalid token." in str(exc_info.value)


class TestPasswordGrant:
    """ROPC mode: nothing happens until the first request needs headers."""

    def test_construction_leaves_auth_unset(self, ropc_kwargs):
        """Nothing is acquired eagerly."""
        client = ERClient(**ropc_kwargs)

        assert client.auth is None
        assert client.auth_expires == pytz.utc.localize(datetime.min)
        assert client.token is None

    class TestFirstLogin:

        def test_posts_exactly_the_password_payload(
            self, ropc_kwargs, default_token_url, token_response, make_requests_response
        ):
            """Exactly one form-encoded password grant, with no extra fields."""
            client = ERClient(**ropc_kwargs)

            with patch(
                "erclient.client.requests.post",
                return_value=make_requests_response(
                    200, json_data=token_response),
            ) as mock_post:
                client.auth_headers()

                mock_post.assert_called_once()
                assert mock_post.call_args.args[0] == default_token_url
                assert mock_post.call_args.kwargs == {
                    "data": {
                        "grant_type": "password",
                        "username": ropc_kwargs["username"],
                        "password": ropc_kwargs["password"],
                        "client_id": ropc_kwargs["client_id"],
                    }
                }

        @pytest.mark.parametrize(
            "expires_in", [3600, "3600"], ids=["int", "string"])
        def test_response_is_stored_whole_with_derived_expiry(
            self,
            ropc_kwargs,
            token_response_factory,
            make_requests_response,
            assert_expiry_matches,
            expires_in,
        ):
            """The whole body becomes self.auth; expiry is now + expires_in - 300s."""
            body = token_response_factory(expires_in=expires_in)
            client = ERClient(**ropc_kwargs)

            with patch(
                "erclient.client.requests.post",
                return_value=make_requests_response(200, json_data=body),
            ):
                client.auth_headers()

            assert client.auth == body
            assert client.auth["scope"] == "read write"  # extra keys survive
            assert_expiry_matches(client.auth_expires, expires_in)

        def test_authorization_header_uses_the_response_token_type(
            self, ropc_kwargs, token_response_factory, make_requests_response
        ):
            """token_type comes from the response verbatim, not a hard-coded "Bearer"."""
            body = token_response_factory(
                token_type="MAC", access_token="abc123")
            client = ERClient(**ropc_kwargs)

            with patch(
                "erclient.client.requests.post",
                return_value=make_requests_response(200, json_data=body),
            ):
                headers = client.auth_headers()

            assert headers["Authorization"] == "MAC abc123"

        def test_explicit_login_returns_true_on_success(
            self, ropc_kwargs, token_response, make_requests_response
        ):
            """Explicit login() reports success as a bool."""
            client = ERClient(**ropc_kwargs)

            with patch(
                "erclient.client.requests.post",
                return_value=make_requests_response(
                    200, json_data=token_response),
            ):
                assert client.login() is True

            assert client.auth == token_response

        def test_bypasses_the_retrying_session(
            self, ropc_kwargs, token_response, make_requests_response
        ):
            """Token requests use module-level requests.post; the session never sees them."""
            client = ERClient(**ropc_kwargs)

            with patch.object(client._http_session, "post") as mock_session_post, patch(
                "erclient.client.requests.post",
                return_value=make_requests_response(
                    200, json_data=token_response),
            ) as mock_post:
                client.login()

            # wart: the token endpoint gets none of the session's retry/backoff policy
            assert mock_post.called
            assert not mock_session_post.called

    class TestExpiryAndRefresh:

        def test_live_token_is_reused(
            self, ropc_kwargs, token_response, make_requests_response
        ):
            """A second auth_headers() inside the validity window makes no request."""
            client = ERClient(**ropc_kwargs)

            with patch(
                "erclient.client.requests.post",
                return_value=make_requests_response(
                    200, json_data=token_response),
            ) as mock_post:
                client.auth_headers()
                client.auth_headers()

                assert mock_post.call_count == 1

        def test_expired_auth_refreshes_without_a_password_grant(
            self, ropc_kwargs, token_response_factory, make_requests_response
        ):
            """On expiry the client tries refresh_token first and stops there when it works."""
            client = ERClient(**ropc_kwargs)
            responses = [
                make_requests_response(
                    200, json_data=token_response_factory()),
                make_requests_response(
                    200,
                    json_data=token_response_factory(
                        access_token="access-token-2"),
                ),
            ]

            with patch(
                "erclient.client.requests.post", side_effect=responses
            ) as mock_post:
                client.auth_headers()
                client.auth_expires = pytz.utc.localize(datetime.min)
                headers = client.auth_headers()

                assert mock_post.call_count == 2
                assert mock_post.call_args_list[1].kwargs["data"] == {
                    "grant_type": "refresh_token",
                    "refresh_token": "refresh-token-1",
                    "client_id": ropc_kwargs["client_id"],
                }
                assert headers["Authorization"] == "Bearer access-token-2"

        def test_failed_refresh_falls_back_to_password_grant(
            self, ropc_kwargs, token_response_factory, make_requests_response
        ):
            """A rejected refresh is swallowed and a fresh password grant is attempted."""
            client = ERClient(**ropc_kwargs)
            responses = [
                make_requests_response(
                    200, json_data=token_response_factory()),
                make_requests_response(
                    401, json_data={"error": "invalid_grant"}),
                make_requests_response(
                    200,
                    json_data=token_response_factory(
                        access_token="access-token-3"),
                ),
            ]

            with patch(
                "erclient.client.requests.post", side_effect=responses
            ) as mock_post:
                client.auth_headers()
                client.auth_expires = pytz.utc.localize(datetime.min)
                headers = client.auth_headers()

                grant_types = [
                    call.kwargs["data"]["grant_type"]
                    for call in mock_post.call_args_list
                ]
                assert grant_types == [
                    "password", "refresh_token", "password"]
                assert headers["Authorization"] == "Bearer access-token-3"

        def test_missing_refresh_token_goes_straight_to_a_password_grant(
            self, ropc_kwargs, token_response_factory, make_requests_response
        ):
            """With no refresh token to send, expiry re-runs login() instead."""
            body = token_response_factory(refresh_token=None)
            client = ERClient(**ropc_kwargs)
            responses = [
                make_requests_response(200, json_data=body),
                make_requests_response(
                    200,
                    json_data=token_response_factory(
                        access_token="access-token-2", refresh_token=None
                    ),
                ),
            ]

            with patch(
                "erclient.client.requests.post", side_effect=responses
            ) as mock_post:
                client.auth_headers()
                client.auth_expires = pytz.utc.localize(datetime.min)
                headers = client.auth_headers()

            grant_types = [
                call.kwargs["data"]["grant_type"]
                for call in mock_post.call_args_list
            ]
            assert grant_types == ["password", "password"]
            assert headers["Authorization"] == "Bearer access-token-2"

        def test_refresh_token_without_one_returns_false_and_sends_nothing(
            self, ropc_kwargs, token_response_factory, make_requests_response
        ):
            """Called directly, refresh_token() reports the obvious rather than raising."""
            body = token_response_factory(refresh_token=None)
            client = ERClient(**ropc_kwargs)

            with patch(
                "erclient.client.requests.post",
                return_value=make_requests_response(200, json_data=body),
            ) as mock_post:
                client.login()
                mock_post.reset_mock()

                assert client.refresh_token() is False
                assert not mock_post.called

            # The still-usable token is left alone.
            assert client.auth == body

        def test_auth_is_valid_tracks_the_recorded_expiry(self, token_kwargs):
            """_auth_is_valid is a pure comparison against auth_expires."""
            client = ERClient(**token_kwargs)

            assert client._auth_is_valid() is True

            client.auth_expires = datetime.now(tz=timezone.utc)
            assert client._auth_is_valid() is False

    class TestFailures:

        def test_refresh_and_login_both_failing_raises_the_classified_error(
            self, ropc_kwargs, token_response_factory, make_requests_response
        ):
            """When both grants fail the client resets and describes the refusal."""
            client = ERClient(**ropc_kwargs)
            login_failure_body = {"error_description": "wrong password"}
            responses = [
                make_requests_response(
                    200, json_data=token_response_factory()),
                make_requests_response(
                    401, json_data={"error": "invalid_grant"}),
                make_requests_response(400, json_data=login_failure_body),
            ]

            with patch("erclient.client.requests.post", side_effect=responses):
                client.auth_headers()
                client.auth_expires = pytz.utc.localize(datetime.min)

                with pytest.raises(ERClientException) as exc_info:
                    client.auth_headers()

            # The login failure is what is reported, not the earlier refresh.
            # This body carries no OAuth error code, so the 400 classifies it.
            assert type(exc_info.value) is ERClientBadRequest
            assert exc_info.value.status_code == 400
            assert exc_info.value.response_body == json.dumps(
                login_failure_body)
            assert client.auth is None
            assert client.auth_expires == pytz.utc.localize(datetime.min)

        @pytest.mark.parametrize(
            "status_code,expected_exception",
            [
                (400, ERClientBadRequest),
                (401, ERClientBadCredentials),
                (500, ERClientInternalError),
            ],
        )
        def test_each_failure_status_gets_its_own_class(
            self, ropc_kwargs, make_requests_response, status_code, expected_exception
        ):
            """A body with no OAuth error code still separates the three cases.

            The caller can now tell "wrong password" (400/401) from "the auth
            server is broken" (500). ``login()`` still reports failure as a
            bool, with the detail on ``last_auth_error``.
            """
            client = ERClient(**ropc_kwargs)

            with patch(
                "erclient.client.requests.post",
                return_value=make_requests_response(status_code, text="nope"),
            ):
                assert client.login() is False
                assert client.last_auth_error.status_code == status_code
                assert client.last_auth_error.error is None

                with pytest.raises(expected_exception) as exc_info:
                    client.auth_headers()

            assert type(exc_info.value) is expected_exception
            assert exc_info.value.status_code == status_code
            assert exc_info.value.response_body == "nope"
            assert client.auth is None
            assert client.auth_expires == pytz.utc.localize(datetime.min)


class TestCustomTokenUrl:

    def test_receives_the_password_grant(
        self, ropc_kwargs, custom_token_url, token_response, make_requests_response
    ):
        """A custom token_url changes the target but not the payload."""
        client = ERClient(**ropc_kwargs, token_url=custom_token_url)

        with patch(
            "erclient.client.requests.post",
            return_value=make_requests_response(200, json_data=token_response),
        ) as mock_post:
            client.auth_headers()

            assert mock_post.call_args.args[0] == custom_token_url
            assert mock_post.call_args.kwargs["data"] == {
                "grant_type": "password",
                "username": ropc_kwargs["username"],
                "password": ropc_kwargs["password"],
                "client_id": ropc_kwargs["client_id"],
            }

    def test_is_never_contacted_when_a_token_is_supplied(
        self, token_kwargs, custom_token_url
    ):
        """A pre-acquired token short-circuits the token endpoint, custom or not."""
        client = ERClient(**token_kwargs, token_url=custom_token_url)

        with patch("erclient.client.requests.post") as mock_post:
            client.auth_headers()

            assert not mock_post.called


class TestNoCredentials:
    """Nothing was supplied, so the client signs the user in itself."""

    def test_constructs_fine(self, service_root):
        client = ERClient(service_root=service_root)

        assert client.auth is None
        assert client.username is None

    def test_selects_the_interactive_sign_in(self, service_root):
        """It used to post a password grant of Nones and report "Login failed."."""
        client = ERClient(service_root=service_root)

        assert client._uses_device_code() is True

    def test_without_a_terminal_it_says_so_and_sends_nothing(
        self, service_root, no_tty
    ):
        """The device-code path is covered in full in test_device_code_sync.py."""
        client = ERClient(service_root=service_root)

        with patch("erclient.client.requests.post") as mock_post:
            with pytest.raises(ERClientBadCredentials):
                client.auth_headers()

        assert not mock_post.called

    def test_requests_drops_none_valued_form_fields(self, default_token_url):
        """Record how requests encodes a password payload with None fields.

        Locks in the library's behavior so an upgrade that starts sending
        ``username=`` instead of dropping the key is caught here.
        """
        prepared = requests.Request(
            "POST",
            default_token_url,
            data={
                "grant_type": "password",
                "username": None,
                "password": None,
                "client_id": None,
            },
        ).prepare()

        assert prepared.body == "grant_type=password"


class TestTheBothCredentialsWarningPointsAtTheCaller:
    """The construction that supplied both is the line worth reporting."""

    def test_it_blames_the_constructor_call(self, service_root):
        with pytest.warns(ERClientAuthWarning) as record:
            ERClient(service_root=service_root, token="a-token",
                     username="someone")

        assert record[0].filename == __file__


class TestTheTwoClientsShareTheirAuthLogic:
    """Anything that is not a request belongs to both clients, not to each.

    Asserted as function identity rather than equal behaviour: a copy that
    starts out identical is exactly how the two drifted apart before, and only
    ``is`` catches a member pasted back into one of them.
    """

    @pytest.mark.parametrize(
        "name",
        ["_warn_if_legacy_auth", "_refuse_token", "_uses_device_code",
         "_device_code_refusal", "_init_auth_options", "_clear_auth"],
    )
    def test_the_same_function_object_serves_both(self, name):
        assert getattr(ERClient, name) is getattr(AsyncERClient, name)

    @pytest.mark.parametrize(
        "name", ["last_auth_error", "protected_resource_metadata"])
    def test_the_same_property_serves_both(self, name):
        assert vars(ERClient).get(name) is None, (
            f"{name} is redefined on ERClient rather than inherited")
        assert vars(AsyncERClient).get(name) is None, (
            f"{name} is redefined on AsyncERClient rather than inherited")
        assert getattr(ERClient, name) is getattr(AsyncERClient, name)
