# incident notes: internal-note confidentiality, authorship rules, and closed-ticket behaviour
import pytest

from tests.helpers import admin_patch, auth, report


@pytest.fixture
async def ticket(client, world) -> int:
    """reported by emp, assigned to eng"""
    incident = await report(client, world.emp, world.tower)
    await admin_patch(client, world.admin, incident["id"], assignee_id=world.eng.id)
    return incident["id"]

async def add_note(client, user, incident_id, body="Update", **fields):
    return await client.post(f"/incidents/{incident_id}/notes", json={"body": body, **fields}, headers=auth(user))

async def note_bodies(client, user, incident_id) -> list[str]:
    response = await client.get(f"/incidents/{incident_id}/notes", headers=auth(user))
    assert response.status_code == 200
    return [note["body"] for note in response.json()]


async def test_everyone_on_the_ticket_can_add_and_read_public_notes(client, world, ticket):
    for user, body in ((world.emp, "From reporter"), (world.eng, "From engineer"), (world.admin, "From admin")):
        response = await add_note(client, user, ticket, body)
        assert response.status_code == 201
        assert response.json()["author_id"] == user.id
    for user in (world.emp, world.eng, world.admin):
        assert await note_bodies(client, user, ticket) == ["From reporter", "From engineer", "From admin"]

async def test_internal_notes_are_hidden_from_employees(client, world, ticket):
    await add_note(client, world.emp, ticket, "Public")
    assert (await add_note(client, world.eng, ticket, "Engineer only", is_internal=True)).status_code == 201

    assert await note_bodies(client, world.emp, ticket) == ["Public"]
    assert await note_bodies(client, world.eng, ticket) == ["Public", "Engineer only"]
    assert await note_bodies(client, world.admin, ticket) == ["Public", "Engineer only"]

async def test_internal_notes_cannot_be_reached_by_id_either(client, world, ticket):
    internal = (await add_note(client, world.eng, ticket, "Secret", is_internal=True)).json()
    path = f"/incidents/{ticket}/notes/{internal['id']}"
    assert (await client.patch(path, json={"body": "seen it"}, headers=auth(world.emp))).status_code == 404
    assert (await client.delete(path, headers=auth(world.emp))).status_code == 404

async def test_employees_cannot_write_internal_notes(client, world, ticket):
    assert (await add_note(client, world.emp, ticket, is_internal=True)).status_code == 403
    note = (await add_note(client, world.emp, ticket)).json()
    response = await client.patch(f"/incidents/{ticket}/notes/{note['id']}", json={"is_internal": True}, headers=auth(world.emp))
    assert response.status_code == 403

async def test_authors_edit_only_their_own_notes(client, world, ticket):
    engineer_note = (await add_note(client, world.eng, ticket, "Engineer says")).json()
    own_note = (await add_note(client, world.emp, ticket, "Typo")).json()

    response = await client.patch(f"/incidents/{ticket}/notes/{engineer_note['id']}", json={"body": "forged"}, headers=auth(world.emp))
    assert response.status_code == 403
    # not even an admin can rewrite someone else's words
    response = await client.patch(f"/incidents/{ticket}/notes/{engineer_note['id']}", json={"body": "forged"}, headers=auth(world.admin))
    assert response.status_code == 403

    response = await client.patch(f"/incidents/{ticket}/notes/{own_note['id']}", json={"body": "Fixed typo"}, headers=auth(world.emp))
    assert response.status_code == 200 and response.json()["body"] == "Fixed typo"

async def test_authors_delete_their_own_notes_admins_delete_any(client, world, ticket):
    engineer_note = (await add_note(client, world.eng, ticket)).json()
    own_note = (await add_note(client, world.emp, ticket)).json()

    assert (await client.delete(f"/incidents/{ticket}/notes/{engineer_note['id']}", headers=auth(world.emp))).status_code == 403
    assert (await client.delete(f"/incidents/{ticket}/notes/{own_note['id']}", headers=auth(world.emp))).status_code == 204
    assert (await client.delete(f"/incidents/{ticket}/notes/{engineer_note['id']}", headers=auth(world.admin))).status_code == 204
    assert await note_bodies(client, world.admin, ticket) == []

async def test_notes_on_other_peoples_tickets_are_404(client, world, ticket):
    note = (await add_note(client, world.emp, ticket)).json()
    for user in (world.emp2, world.eng2, world.west_emp):
        assert (await add_note(client, user, ticket)).status_code == 404
        assert (await client.get(f"/incidents/{ticket}/notes", headers=auth(user))).status_code == 404
        assert (await client.delete(f"/incidents/{ticket}/notes/{note['id']}", headers=auth(user))).status_code == 404

async def test_note_ids_are_scoped_to_their_incident(client, world, ticket):
    # emp2 owns a note on their own ticket; they can't reach it through emp's ticket id, and vice versa
    other = await report(client, world.emp2, world.tower)
    note = (await add_note(client, world.emp2, other["id"])).json()
    response = await client.patch(f"/incidents/{ticket}/notes/{note['id']}", json={"body": "x"}, headers=auth(world.admin))
    assert response.status_code == 404

async def test_closed_tickets_only_take_notes_from_admins(client, world, ticket):
    await admin_patch(client, world.admin, ticket, status="Closed")
    assert (await add_note(client, world.emp, ticket)).status_code == 400
    assert (await add_note(client, world.eng, ticket)).status_code == 400
    assert (await add_note(client, world.admin, ticket)).status_code == 201

async def test_empty_notes_are_rejected(client, world, ticket):
    assert (await add_note(client, world.emp, ticket, body="")).status_code == 422
