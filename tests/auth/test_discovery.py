"""discover() on both clients. It is advisory: a site that will not answer,
or answers with nonsense, means no metadata rather than a failure."""
import pytest
from tests.auth.conftest import Reply


@pytest.fixture
def discovery_document(service_root):
    return {"resource": service_root,
            "authorization_servers": [f"{service_root}/oauth2",
                                      "https://auth-dev.pamdas.org"]}


class TestWhatItFetches:

    def test_asks_the_sites_well_known_path(self, client, server,
                                            service_root, discovery_url,
                                            discovery_document):
        server.respond("GET", discovery_url, json_body=discovery_document)
        client.make(service_root=service_root)

        metadata = client.call(client.discover)

        assert server.calls == [("GET", discovery_url)]
        assert metadata.resource == service_root
        assert metadata.authorization_servers == (
            f"{service_root}/oauth2", "https://auth-dev.pamdas.org")

    def test_keeps_what_it_found(self, client, server, service_root,
                                 discovery_url, discovery_document):
        server.respond("GET", discovery_url, json_body=discovery_document)
        client.make(service_root=service_root)

        assert client.call(
            client.discover) is client._protected_resource_metadata

    def test_a_site_with_no_url_to_ask_is_not_asked(self, client, server):
        client.make()

        assert client.call(client.discover) is None
        assert server.traffic == []


class TestWhatItForgives:

    @pytest.mark.parametrize("status_code", [301, 404, 500, 502])
    def test_a_status_that_is_not_a_document(self, client, server,
                                             service_root, discovery_url,
                                             status_code):
        server.respond("GET", discovery_url, status_code, text="")
        client.make(service_root=service_root)

        assert client.call(client.discover) is None

    @pytest.mark.parametrize("text", ["", "not json", "<html>404</html>"])
    def test_a_body_it_cannot_read(self, client, server, service_root,
                                   discovery_url, text):
        server.respond("GET", discovery_url, text=text)
        client.make(service_root=service_root)

        assert client.call(client.discover) is None

    def test_a_document_for_another_resource(self, client, server,
                                             service_root, discovery_url):
        server.respond("GET", discovery_url, json_body={
            "resource": "https://other-site.erdomain.org",
            "authorization_servers": []})
        client.make(service_root=service_root)

        assert client.call(client.discover) is None

    def test_a_site_it_cannot_reach(self, client, server, service_root,
                                    discovery_url):
        server.fail("GET", discovery_url,
                    client.transport_error("no route to host"))
        client.make(service_root=service_root)

        assert client.call(client.discover) is None

    def test_a_second_look_replaces_what_the_first_found(
            self, client, server, service_root, discovery_url,
            discovery_document):
        server.script("GET", discovery_url,
                      Reply(json_body=discovery_document),
                      Reply(404, text=""))
        client.make(service_root=service_root)

        assert client.call(client.discover) is not None
        assert client.call(client.discover) is None
        assert client._protected_resource_metadata is None


class TestNothingElseAsksForIt:
    """A caller who brought their own token never discovers."""

    def test_a_supplied_token_does_not_discover(self, client, server,
                                                token_kwargs):
        client.make(**token_kwargs)

        client.auth_headers()

        assert server.traffic == []

    def test_discovery_false_still_permits_an_explicit_discover(
            self, client, server, service_root, discovery_url,
            discovery_document):
        server.respond("GET", discovery_url, json_body=discovery_document)
        client.make(service_root=service_root, discovery=False)

        assert client.call(client.discover) is not None
