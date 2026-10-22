# incidents: row-level visibility, field-level permissions, the status workflow, assignment rules and filters
import pytest

from tests.helpers import admin_patch, auth, patch_incident, report


async def get(client, user, path, **params):
    return await client.get(path, params=params, headers=auth(user))

async def ids(client, user, **params) -> set[int]:
    response = await get(client, user, "/incidents", **params)
    assert response.status_code == 200, response.text
    return {incident["id"] for incident in response.json()}

async def history(client, user, incident_id) -> list[tuple[str | None, str]]:
    rows = (await get(client, user, f"/incidents/{incident_id}/history")).json()
    return [(row["from_status"], row["to_status"]) for row in rows]


# ---------- visibility ----------

@pytest.fixture
async def tickets(client, world):
    """emp, emp2 and west_emp each report one ticket; emp's is assigned to eng."""
    mine = await report(client, world.emp, world.tower, title="Mine")
    other = await report(client, world.emp2, world.annex, title="Other")
    west = await report(client, world.west_emp, world.hall, title="West")
    await admin_patch(client, world.admin, mine["id"], assignee_id=world.eng.id)
    return {"mine": mine["id"], "other": other["id"], "west": west["id"]}

async def test_employees_only_see_their_own_incidents(client, world, tickets):
    assert await ids(client, world.emp) == {tickets["mine"]}
    assert await ids(client, world.emp2) == {tickets["other"]}
    assert await ids(client, world.west_emp) == {tickets["west"]}

async def test_engineers_see_tickets_assigned_to_or_reported_by_them(client, world, tickets):
    assert await ids(client, world.eng) == {tickets["mine"]}
    assert await ids(client, world.eng2) == set()
    own = await report(client, world.eng2, world.tower, title="Engineer's own report")
    assert await ids(client, world.eng2) == {own["id"]}

async def test_admins_see_every_incident(client, world, tickets):
    assert await ids(client, world.admin) == set(tickets.values())

@pytest.mark.parametrize("suffix", ["", "/history", "/notes"])
async def test_other_peoples_incidents_are_404_not_403(client, world, tickets, suffix):
    # 404 so ticket ids belonging to someone else can't be probed
    for user, ticket in ((world.emp, "other"), (world.emp, "west"), (world.eng2, "mine"), (world.west_eng, "mine")):
        response = await get(client, user, f"/incidents/{tickets[ticket]}{suffix}")
        assert response.status_code == 404, (user.username, ticket, suffix)

async def test_cannot_modify_incidents_you_cannot_see(client, world, tickets):
    response = await patch_incident(client, world.emp, tickets["other"], title="Hijacked")
    assert response.status_code == 404
    response = await patch_incident(client, world.eng2, tickets["mine"], status="Resolved")
    assert response.status_code == 404
    assert (await get(client, world.admin, f"/incidents/{tickets['other']}")).json()["title"] == "Other"

async def test_filters_cannot_widen_visibility(client, world, tickets):
    # an employee asking for someone else's tickets, or another campus, still only gets their own
    assert await ids(client, world.emp, reporter_id=world.emp2.id) == set()
    assert await ids(client, world.emp, facility_id=world.west.id) == {tickets["mine"]}
    assert await ids(client, world.eng2, assignee_id=world.eng.id) == set()


# ---------- reporting ----------

async def test_new_incident_is_open_unassigned_and_owned_by_the_caller(client, world):
    # extra fields an attacker might try to set on create are ignored
    incident = await report(
        client, world.emp, world.tower,
        status="Closed", assignee_id=world.eng.id, reporter_id=world.emp2.id, is_escalated=True,
    )
    assert incident["status"] == "Open"
    assert incident["assignee_id"] is None
    assert incident["reporter_id"] == world.emp.id
    assert incident["is_escalated"] is False
    assert incident["acknowledged_at"] is None and incident["assigned_at"] is None
    assert await history(client, world.emp, incident["id"]) == [(None, "Open")]

async def test_report_with_full_location(client, world):
    incident = await report(
        client, world.emp, world.tower, floor_id=world.tower_f1.id, seat_id=world.tower_f1_seat.id,
    )
    assert (incident["building_id"], incident["floor_id"], incident["seat_id"]) == (
        world.tower.id, world.tower_f1.id, world.tower_f1_seat.id,
    )

async def test_location_must_be_consistent(client, world):
    base = {"title": "x", "description": "y", "category": "Other"}
    cases = [
        {"building_id": world.tower.id, "floor_id": world.annex_f1.id},                                 # floor in another building
        {"building_id": world.tower.id, "floor_id": world.tower_f2.id, "seat_id": world.tower_f1_seat.id},  # seat on another floor
        {"building_id": world.tower.id, "seat_id": world.tower_f1_seat.id},                             # seat without floor
    ]
    for location in cases:
        response = await client.post("/incidents", json=base | location, headers=auth(world.emp))
        assert response.status_code == 400, location

async def test_employees_can_only_report_at_their_own_campus(client, world):
    body = {"title": "x", "description": "y", "category": "Other", "building_id": world.hall.id}
    assert (await client.post("/incidents", json=body, headers=auth(world.emp))).status_code == 400
    assert (await client.post("/incidents", json=body, headers=auth(world.eng))).status_code == 400
    # admins can report anywhere
    assert (await client.post("/incidents", json=body, headers=auth(world.admin))).status_code == 201

async def test_report_validates_input(client, world):
    headers = auth(world.emp)
    assert (await client.post("/incidents", json={"title": "x", "description": "y", "category": "Other", "building_id": 9999}, headers=headers)).status_code == 404
    assert (await client.post("/incidents", json={"title": "", "description": "y", "category": "Other", "building_id": world.tower.id}, headers=headers)).status_code == 422
    assert (await client.post("/incidents", json={"title": "x", "description": "y", "category": "Aliens", "building_id": world.tower.id}, headers=headers)).status_code == 422
    assert (await client.post("/incidents", json={"title": "x", "description": "y", "category": "Other", "building_id": world.tower.id, "priority": "Urgent!!"}, headers=headers)).status_code == 422


# ---------- who can edit which fields ----------

@pytest.fixture
async def assigned(client, world) -> int:
    """an incident reported by emp and assigned to eng"""
    incident = await report(client, world.emp, world.tower)
    await admin_patch(client, world.admin, incident["id"], assignee_id=world.eng.id)
    return incident["id"]

async def test_reporter_can_edit_details_but_not_assignment(client, world, assigned):
    response = await patch_incident(client, world.emp, assigned, title="Broken chair, seat 4", priority="High")
    assert response.status_code == 200
    assert response.json()["title"] == "Broken chair, seat 4"

    for field, value in (("assignee_id", world.emp2.id), ("assignee_id", None), ("blocked_reason", "nope")):
        response = await patch_incident(client, world.emp, assigned, **{field: value})
        assert response.status_code == 403, field

async def test_assigned_engineer_can_only_change_status(client, world, assigned):
    assert (await patch_incident(client, world.eng, assigned, status="In Progress")).status_code == 200
    for field, value in (
        ("title", "Engineer rename"), ("priority", "Low"), ("assignee_id", world.eng2.id),
        ("is_escalated", False), ("building_id", world.annex.id),
    ):
        response = await patch_incident(client, world.eng, assigned, **{field: value})
        assert response.status_code == 403, field

async def test_disallowed_field_rejects_the_whole_request(client, world, assigned):
    # a valid field alongside a forbidden one must not be partially applied
    response = await patch_incident(client, world.emp, assigned, title="Changed", assignee_id=None)
    assert response.status_code == 403
    incident = (await get(client, world.admin, f"/incidents/{assigned}")).json()
    assert incident["title"] == "Broken chair" and incident["assignee_id"] == world.eng.id

async def test_engineer_who_reported_but_is_not_assigned_acts_as_reporter(client, world):
    incident = await report(client, world.eng, world.tower)
    assert (await patch_incident(client, world.eng, incident["id"], title="Renamed")).status_code == 200
    assert (await patch_incident(client, world.eng, incident["id"], status="In Progress")).status_code == 403

async def test_admin_can_edit_every_field(client, world, assigned):
    response = await patch_incident(
        client, world.admin, assigned,
        title="Admin edit", priority="Critical", category="Electrical", assignee_id=world.eng2.id,
        building_id=world.annex.id, floor_id=world.annex_f1.id,
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["priority"], body["assignee_id"], body["building_id"]) == ("Critical", world.eng2.id, world.annex.id)


# ---------- escalation ----------

async def test_escalation_requires_a_reason_which_is_cleared_on_de_escalation(client, world, assigned):
    assert (await patch_incident(client, world.emp, assigned, is_escalated=True)).status_code == 400
    response = await patch_incident(client, world.emp, assigned, is_escalated=True, escalation_reason="Server room is overheating")
    assert response.status_code == 200 and response.json()["is_escalated"] is True

    response = await patch_incident(client, world.emp, assigned, is_escalated=False)
    assert response.json()["escalation_reason"] is None


# ---------- status workflow ----------

@pytest.mark.parametrize("start, target", [
    ("Blocked", "Open"),
    ("Blocked", "Closed"),
    ("In Progress", "Closed"),
    ("Closed", "Resolved"),
    ("Closed", "In Progress"),
    ("Closed", "Blocked"),
])
async def test_invalid_transitions_are_rejected_even_for_admins(client, world, assigned, start, target):
    reason = {"blocked_reason": "waiting on parts"} if start == "Blocked" else {}
    await admin_patch(client, world.admin, assigned, status=start, **reason)
    response = await patch_incident(client, world.admin, assigned, status=target)
    assert response.status_code == 400
    assert (await get(client, world.admin, f"/incidents/{assigned}")).json()["status"] == start

async def test_happy_path_lifecycle_and_audit_trail(client, world, assigned):
    assert (await patch_incident(client, world.eng, assigned, status="In Progress")).status_code == 200
    assert (await patch_incident(client, world.eng, assigned, status="Blocked", blocked_reason="Waiting on a part")).status_code == 200
    assert (await patch_incident(client, world.eng, assigned, status="In Progress")).status_code == 200
    assert (await patch_incident(client, world.eng, assigned, status="Resolved")).status_code == 200
    assert (await patch_incident(client, world.emp, assigned, status="Closed")).status_code == 200

    rows = (await get(client, world.admin, f"/incidents/{assigned}/history")).json()
    assert [(r["from_status"], r["to_status"]) for r in rows] == [
        (None, "Open"),
        ("Open", "In Progress"),
        ("In Progress", "Blocked"),
        ("Blocked", "In Progress"),
        ("In Progress", "Resolved"),
        ("Resolved", "Closed"),
    ]
    assert rows[2]["reason"] == "Waiting on a part"
    assert [r["changed_by"]["username"] for r in rows] == ["emp", "eng", "eng", "eng", "eng", "emp"]

async def test_blocked_requires_a_reason_which_is_cleared_when_unblocked(client, world, assigned):
    assert (await patch_incident(client, world.eng, assigned, status="Blocked")).status_code == 400
    response = await patch_incident(client, world.eng, assigned, status="Blocked", blocked_reason="Vendor visit Tuesday")
    assert response.json()["blocked_reason"] == "Vendor visit Tuesday"
    response = await patch_incident(client, world.eng, assigned, status="In Progress")
    assert response.json()["blocked_reason"] is None

async def test_setting_the_same_status_is_a_no_op(client, world, assigned):
    await patch_incident(client, world.eng, assigned, status="Open")
    assert await history(client, world.admin, assigned) == [(None, "Open")]

async def test_reporter_can_only_close_or_reopen_a_resolved_ticket(client, world, assigned):
    for target in ("In Progress", "Resolved", "Closed", "Blocked"):
        response = await patch_incident(client, world.emp, assigned, status=target, blocked_reason="x" if target == "Blocked" else None)
        assert response.status_code == 403, target

    await admin_patch(client, world.admin, assigned, status="Resolved")
    assert (await patch_incident(client, world.emp, assigned, status="In Progress")).status_code == 403
    assert (await patch_incident(client, world.emp, assigned, status="Open")).status_code == 200  # reopen

    await admin_patch(client, world.admin, assigned, status="Resolved")
    assert (await patch_incident(client, world.emp, assigned, status="Closed")).status_code == 200  # confirm

async def test_engineers_cannot_close_or_reopen_closed_tickets(client, world, assigned):
    await patch_incident(client, world.eng, assigned, status="Resolved")
    assert (await patch_incident(client, world.eng, assigned, status="Closed")).status_code == 403

    await admin_patch(client, world.admin, assigned, status="Closed")
    assert (await patch_incident(client, world.eng, assigned, status="Open")).status_code == 403

async def test_closed_tickets_are_read_only_for_reporters(client, world, assigned):
    await admin_patch(client, world.admin, assigned, status="Closed")
    assert (await patch_incident(client, world.emp, assigned, title="Late edit")).status_code == 400
    assert (await patch_incident(client, world.emp, assigned, status="Open")).status_code == 400
    # only an admin can reopen
    assert (await patch_incident(client, world.admin, assigned, status="Open")).status_code == 200

async def test_lifecycle_timestamps(client, world):
    incident = await report(client, world.emp, world.tower)
    incident_id = incident["id"]

    body = await admin_patch(client, world.admin, incident_id, assignee_id=world.eng.id)
    assert body["assigned_at"] is not None and body["acknowledged_at"] is None

    body = await admin_patch(client, world.admin, incident_id, status="In Progress")
    acknowledged = body["acknowledged_at"]
    assert acknowledged is not None

    body = await admin_patch(client, world.admin, incident_id, status="Resolved")
    assert body["resolved_at"] is not None and body["closed_at"] is None

    body = await admin_patch(client, world.admin, incident_id, status="Closed")
    assert body["closed_at"] is not None

    # reopening puts it back in the queue: no longer resolved or closed, first acknowledgement is kept
    body = await admin_patch(client, world.admin, incident_id, status="Open")
    assert body["resolved_at"] is None and body["closed_at"] is None
    assert body["acknowledged_at"] == acknowledged

    body = await admin_patch(client, world.admin, incident_id, assignee_id=None)
    assert body["assigned_at"] is None


# ---------- assignment ----------

async def test_can_only_assign_active_engineers_from_the_same_campus(client, world):
    incident = await report(client, world.emp, world.tower)
    for assignee in (world.emp2, world.admin, world.west_eng, world.inactive_eng):
        response = await patch_incident(client, world.admin, incident["id"], assignee_id=assignee.id)
        assert response.status_code == 400, assignee.username
    assert (await patch_incident(client, world.admin, incident["id"], assignee_id=world.eng.id)).status_code == 200

@pytest.mark.parametrize("field", ["assignee_id", "building_id", "floor_id", "seat_id"])
async def test_patching_a_nonexistent_id_is_404_and_changes_nothing(client, world, field):
    incident = await report(client, world.emp, world.tower)
    # a seat is only accepted together with a floor, so send a real one alongside the missing seat
    extra = {"floor_id": world.tower_f1.id} if field == "seat_id" else {}
    response = await patch_incident(client, world.admin, incident["id"], **{field: 99999}, **extra)
    assert response.status_code == 404, response.text
    after = (await get(client, world.admin, f"/incidents/{incident['id']}")).json()
    assert {k: after[k] for k in ("assignee_id", "building_id", "floor_id", "seat_id")} == {
        "assignee_id": None, "building_id": world.tower.id, "floor_id": None, "seat_id": None,
    }

async def test_moving_a_ticket_to_another_campus_rechecks_the_assignee(client, world, assigned):
    response = await patch_incident(client, world.admin, assigned, building_id=world.hall.id)
    assert response.status_code == 400
    response = await patch_incident(client, world.admin, assigned, building_id=world.hall.id, assignee_id=world.west_eng.id)
    assert response.status_code == 200

async def test_reporter_cannot_move_ticket_to_another_campus(client, world, assigned):
    assert (await patch_incident(client, world.emp, assigned, building_id=world.hall.id)).status_code == 400
    assert (await patch_incident(client, world.emp, assigned, building_id=world.annex.id)).status_code == 200


# ---------- delete ----------

async def test_deleting_an_incident_removes_its_notes_and_history(client, world, assigned):
    await client.post(f"/incidents/{assigned}/notes", json={"body": "hello"}, headers=auth(world.emp))
    assert (await client.delete(f"/incidents/{assigned}", headers=auth(world.admin))).status_code == 204
    assert (await get(client, world.admin, f"/incidents/{assigned}")).status_code == 404
    assert (await client.delete(f"/incidents/{assigned}", headers=auth(world.admin))).status_code == 404


# ---------- search + filters ----------

async def test_search_and_filters(client, world):
    wifi = await report(client, world.emp, world.tower, title="Wi-Fi drops", category="Network / Wi-Fi", priority="High")
    chair = await report(client, world.emp, world.annex, title="Chair", description="squeaky wheels")
    west = await report(client, world.admin, world.hall, title="Leak", category="Plumbing")
    await admin_patch(client, world.admin, chair["id"], assignee_id=world.eng.id, status="In Progress")

    admin = world.admin
    assert await ids(client, admin, q="wi-fi") == {wifi["id"]}
    assert await ids(client, admin, q="SQUEAKY") == {chair["id"]}  # case-insensitive, searches description too
    assert await ids(client, admin, status=["Open"]) == {wifi["id"], west["id"]}
    assert await ids(client, admin, status=["Open", "In Progress"]) == {wifi["id"], chair["id"], west["id"]}
    assert await ids(client, admin, priority="High") == {wifi["id"]}
    assert await ids(client, admin, category="Plumbing") == {west["id"]}
    assert await ids(client, admin, building_id=world.annex.id) == {chair["id"]}
    assert await ids(client, admin, unassigned="true") == {wifi["id"], west["id"]}
    assert await ids(client, admin, assignee_id=world.eng.id) == {chair["id"]}
    assert await ids(client, admin, facility_id=world.west.id) == {west["id"]}
    assert await ids(client, admin, facility_id=[world.hq.id, world.west.id]) == {wifi["id"], chair["id"], west["id"]}

async def test_search_input_is_not_interpreted_as_sql(client, world):
    await report(client, world.emp, world.tower)
    assert await ids(client, world.admin, q="' OR 1=1 --") == set()
    assert await ids(client, world.emp, q="%") != set()  # wildcards only match within the user's own tickets

async def test_pagination_limits_are_enforced(client, world):
    assert (await get(client, world.admin, "/incidents", limit=1001)).status_code == 422
    assert (await get(client, world.admin, "/incidents", offset=-1)).status_code == 422
