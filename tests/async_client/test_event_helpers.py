"""
Tests for AsyncERClient event helper methods.

These tests verify URL/path construction, parameter handling, and error cases
for the convenience methods: post_event, patch_event, post_event_file,
post_event_note, delete_event_file, delete_event_note, add_event_to_incident,
remove_event_from_incident, and delete_event.
"""

import httpx
import pytest
import respx

from erclient import ERClientNotFound, ERClientPermissionDenied

# --- post_event tests ---


@pytest.mark.asyncio
async def test_post_event_constructs_correct_path(er_client, report, report_created_response):
    """post_event should POST to activity/events endpoint."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('activity/events')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=report_created_response)

        response = await er_client.post_event(report)

        assert route.called
        assert response == report_created_response['data']
        await er_client.close()


@pytest.mark.asyncio
async def test_post_event_is_alias_for_post_report(er_client, report, report_created_response):
    """post_event should behave identically to post_report."""
    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post('activity/events')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=report_created_response)

        # Both methods should produce identical results
        event_response = await er_client.post_event(report)
        assert event_response == report_created_response['data']
        await er_client.close()


# --- patch_event tests ---

@pytest.mark.asyncio
async def test_patch_event_constructs_correct_path(er_client, report_updated_response):
    """patch_event should PATCH to activity/event/{event_id} endpoint."""
    event_id = 'bf7e56c7-0751-4899-844f-b5888eb813b1'
    payload = {'state': 'active'}

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f'activity/event/{event_id}')
        route.return_value = httpx.Response(
            httpx.codes.OK, json=report_updated_response)

        response = await er_client.patch_event(event_id, payload)

        assert route.called
        assert response == report_updated_response['data']
        await er_client.close()


@pytest.mark.asyncio
async def test_patch_event_not_found(er_client, not_found_response):
    """patch_event should raise ERClientNotFound for non-existent events."""
    event_id = 'non-existent-id'
    payload = {'state': 'active'}

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.patch(f'activity/event/{event_id}')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json=not_found_response)

        with pytest.raises(ERClientNotFound):
            await er_client.patch_event(event_id, payload)

        assert route.called
        await er_client.close()


# --- post_event_file tests ---

@pytest.mark.asyncio
async def test_post_event_file_constructs_correct_path(
        er_client, report_created_response, attachment_created_response, tmp_path
):
    """post_event_file should POST to activity/event/{event_id}/files/ endpoint."""
    event_id = report_created_response["data"]["id"]

    # Create a temporary test file
    test_file = tmp_path / "test_image.jpg"
    test_file.write_bytes(b"fake image content")

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'activity/event/{event_id}/files/')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=attachment_created_response)

        response = await er_client.post_event_file(event_id, filepath=str(test_file))

        assert route.called
        assert response == attachment_created_response['data']
        await er_client.close()


@pytest.mark.asyncio
async def test_post_event_file_with_comment(
        er_client, report_created_response, attachment_created_response, tmp_path
):
    """post_event_file should include comment in the request body."""
    event_id = report_created_response["data"]["id"]
    comment = "Test comment for the file"

    # Create a temporary test file
    test_file = tmp_path / "test_image.jpg"
    test_file.write_bytes(b"fake image content")

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'activity/event/{event_id}/files/')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=attachment_created_response)

        response = await er_client.post_event_file(
            event_id, filepath=str(test_file), comment=comment
        )

        assert route.called
        # Verify comment was included in request
        request = route.calls[0].request
        # The body should contain the comment (multipart form data)
        assert b'comment' in request.content
        await er_client.close()


@pytest.mark.asyncio
async def test_post_event_file_handles_uuid_event_id(
        er_client, attachment_created_response, tmp_path
):
    """post_event_file should handle UUID event_id (convert to string)."""
    import uuid
    event_id = uuid.UUID('9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f')

    test_file = tmp_path / "test_image.jpg"
    test_file.write_bytes(b"fake image content")

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        # The path should use string version of UUID
        route = respx_mock.post(f'activity/event/{str(event_id)}/files/')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=attachment_created_response)

        response = await er_client.post_event_file(event_id, filepath=str(test_file))

        assert route.called
        await er_client.close()


# --- post_event_note tests ---

@pytest.mark.asyncio
async def test_post_event_note_single_note(er_client, report_created_response):
    """post_event_note should POST a single note to activity/event/{event_id}/notes."""
    event_id = report_created_response["data"]["id"]
    note_text = "This is a test note"

    note_response = {
        'data': {
            'id': 'note-id-123',
            'text': note_text,
            'event': event_id
        },
        'status': {'code': 201, 'message': 'Created'}
    }

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'activity/event/{event_id}/notes')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=note_response)

        result = await er_client.post_event_note(event_id, note_text)

        assert route.called
        assert len(result) == 1
        assert result[0] == note_response['data']
        await er_client.close()


@pytest.mark.asyncio
async def test_post_event_note_multiple_notes(er_client, report_created_response):
    """post_event_note should handle a list of notes."""
    event_id = report_created_response["data"]["id"]
    notes = ["First note", "Second note", "Third note"]

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'activity/event/{event_id}/notes')

        def create_response(request):
            return httpx.Response(
                httpx.codes.CREATED,
                json={'data': {'id': 'note-id', 'text': 'note'},
                      'status': {'code': 201}}
            )

        route.side_effect = create_response

        result = await er_client.post_event_note(event_id, notes)

        assert route.call_count == 3
        assert len(result) == 3
        await er_client.close()


@pytest.mark.asyncio
async def test_post_event_note_request_payload(er_client, report_created_response):
    """post_event_note should send correct payload with event and text fields."""
    event_id = report_created_response["data"]["id"]
    note_text = "Test note content"

    note_response = {
        'data': {'id': 'note-id', 'text': note_text},
        'status': {'code': 201}
    }

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'activity/event/{event_id}/notes')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=note_response)

        await er_client.post_event_note(event_id, note_text)

        # Verify request payload
        request = route.calls[0].request
        import json
        payload = json.loads(request.content)
        assert payload['event'] == event_id
        assert payload['text'] == note_text
        await er_client.close()


# --- delete_event_file tests ---

@pytest.mark.asyncio
async def test_delete_event_file_constructs_correct_path(er_client):
    """delete_event_file should DELETE to activity/event/{event_id}/file/{file_id}."""
    event_id = '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f'
    file_id = '8e095bc9-94bd-44bd-aeaf-d2765de1fd12'

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'activity/event/{event_id}/file/{file_id}')
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        await er_client.delete_event_file(event_id, file_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_event_file_not_found(er_client, not_found_response):
    """delete_event_file should raise ERClientNotFound for non-existent file."""
    event_id = '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f'
    file_id = 'non-existent-file-id'

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'activity/event/{event_id}/file/{file_id}')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json=not_found_response)

        with pytest.raises(ERClientNotFound):
            await er_client.delete_event_file(event_id, file_id)

        assert route.called
        await er_client.close()


# --- delete_event_note tests ---

@pytest.mark.asyncio
async def test_delete_event_note_constructs_correct_path(er_client):
    """delete_event_note should DELETE to activity/event/{event_id}/note/{note_id}."""
    event_id = '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f'
    note_id = 'note-id-123'

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'activity/event/{event_id}/note/{note_id}')
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        await er_client.delete_event_note(event_id, note_id)

        assert route.called
        await er_client.close()


# --- add_event_to_incident tests ---

@pytest.mark.asyncio
async def test_add_event_to_incident_constructs_correct_path(er_client):
    """add_event_to_incident should POST to activity/event/{incident_id}/relationships."""
    event_id = '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f'
    incident_id = 'incident-id-456'

    relationship_response = {
        'data': {
            'id': 'relationship-id',
            'to_event_id': event_id,
            'type': 'contains'
        },
        'status': {'code': 201, 'message': 'Created'}
    }

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'activity/event/{incident_id}/relationships')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=relationship_response)

        response = await er_client.add_event_to_incident(event_id, incident_id)

        assert route.called
        assert response == relationship_response['data']
        await er_client.close()


@pytest.mark.asyncio
async def test_add_event_to_incident_sends_correct_payload(er_client):
    """add_event_to_incident should send payload with to_event_id and type='contains'."""
    event_id = '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f'
    incident_id = 'incident-id-456'

    relationship_response = {
        'data': {'id': 'relationship-id'},
        'status': {'code': 201}
    }

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.post(f'activity/event/{incident_id}/relationships')
        route.return_value = httpx.Response(
            httpx.codes.CREATED, json=relationship_response)

        await er_client.add_event_to_incident(event_id, incident_id)

        # Verify request payload
        request = route.calls[0].request
        import json
        payload = json.loads(request.content)
        assert payload['to_event_id'] == event_id
        assert payload['type'] == 'contains'
        await er_client.close()


# --- remove_event_from_incident tests ---

@pytest.mark.asyncio
async def test_remove_event_from_incident_constructs_correct_path(er_client):
    """remove_event_from_incident should DELETE to correct relationship endpoint."""
    event_id = '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f'
    incident_id = 'incident-id-456'

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(
            f'activity/event/{incident_id}/relationship/contains/{event_id}/')
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        await er_client.remove_event_from_incident(event_id, incident_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_remove_event_from_incident_custom_relationship_type(er_client):
    """remove_event_from_incident should support custom relationship types."""
    event_id = '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f'
    incident_id = 'incident-id-456'
    relationship_type = 'is_linked_to'

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(
            f'activity/event/{incident_id}/relationship/{relationship_type}/{event_id}/')
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        await er_client.remove_event_from_incident(
            event_id, incident_id, relationship_type=relationship_type
        )

        assert route.called
        await er_client.close()


# --- delete_event tests ---

@pytest.mark.asyncio
async def test_delete_event_constructs_correct_path(er_client):
    """delete_event should DELETE to activity/event/{event_id}/."""
    event_id = '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f'

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'activity/event/{event_id}/')
        route.return_value = httpx.Response(httpx.codes.NO_CONTENT)

        await er_client.delete_event(event_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_event_not_found(er_client, not_found_response):
    """delete_event should raise ERClientNotFound for non-existent event."""
    event_id = 'non-existent-event-id'

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'activity/event/{event_id}/')
        route.return_value = httpx.Response(
            httpx.codes.NOT_FOUND, json=not_found_response)

        with pytest.raises(ERClientNotFound):
            await er_client.delete_event(event_id)

        assert route.called
        await er_client.close()


@pytest.mark.asyncio
async def test_delete_event_forbidden(er_client, forbidden_response):
    """delete_event should raise ERClientPermissionDenied when not authorized."""
    event_id = '9d55bb9f-9fb5-4f43-b1c1-c0ba5164651f'

    async with respx.mock(
            base_url=er_client._api_root("v1.0"), assert_all_called=False
    ) as respx_mock:
        route = respx_mock.delete(f'activity/event/{event_id}/')
        route.return_value = httpx.Response(
            httpx.codes.FORBIDDEN, json=forbidden_response)

        with pytest.raises(ERClientPermissionDenied):
            await er_client.delete_event(event_id)

        assert route.called
        await er_client.close()
