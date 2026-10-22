# the dashboard endpoint: every number must be limited to what the caller is allowed to see
from datetime import datetime, timedelta, timezone

import pytest

from tests.helpers import admin_patch, auth, report


@pytest.fixture
async def tickets(client, world):
    """emp: 1 ticket assigned to eng. emp2: 2 tickets, one Critical and unassigned. west_emp: 1 at West."""
    mine = await report(client, world.emp, world.tower, category="HVAC")
    await admin_patch(client, world.admin, mine["id"], assignee_id=world.eng.id, status="In Progress")
    await report(client, world.emp2, world.tower, priority="Critical")
    other = await report(client, world.emp2, world.annex, category="Plumbing")
    await admin_patch(client, world.admin, other["id"], status="Resolved")
    await report(client, world.west_emp, world.hall)
    return mine

async def dashboard(client, user, **params) -> dict:
    response = await client.get("/analytics/dashboard", params=params, headers=auth(user))
    assert response.status_code == 200, response.text
    return response.json()

async def attention_page(client, user, **params) -> dict:
    response = await client.get("/analytics/attention", params=params, headers=auth(user))
    assert response.status_code == 200, response.text
    return response.json()


async def test_admin_sees_everything(client, world, tickets):
    body = await dashboard(client, world.admin)
    assert body["scope"] == "all"
    assert body["current"]["active"] == 3
    assert body["current"]["awaiting_reporter"] == 1
    assert body["current"]["unassigned"] == 2
    assert body["period"]["created"] == 4
    assert body["my_tickets"] is None
    assert {row["display_name"] for row in body["workload"]} == {"Eng One", "Eng Two", "West Eng"}

async def test_admin_can_narrow_to_a_campus(client, world, tickets):
    body = await dashboard(client, world.admin, facility_id=world.west.id)
    assert body["current"]["active"] == 1
    assert body["facility_ids"] == [world.west.id]
    assert {row["display_name"] for row in body["workload"]} == {"West Eng"}

async def test_employee_dashboard_only_counts_their_own_tickets(client, world, tickets):
    body = await dashboard(client, world.emp)
    assert body["scope"] == "reported"
    assert body["current"]["active"] == 1
    assert body["period"]["created"] == 1
    assert [t["id"] for t in body["my_tickets"]] == [tickets["id"]]
    assert body["workload"] is None  # engineer workload isn't for employees

    body = await dashboard(client, world.emp2)
    assert body["current"]["active"] == 1 and body["current"]["critical_or_high"] == 1
    assert body["current"]["awaiting_reporter"] == 1

async def test_engineer_dashboard_only_counts_assigned_tickets(client, world, tickets):
    body = await dashboard(client, world.eng)
    assert body["scope"] == "assigned"
    assert body["current"]["active"] == 1
    attention = await attention_page(client, world.eng, limit=100)
    assert {t["id"] for t in attention["items"]} <= {tickets["id"]}
    # the team workload stays within their campus
    assert {row["display_name"] for row in body["workload"]} == {"Eng One", "Eng Two"}
    assert (await dashboard(client, world.eng2))["current"]["active"] == 0

async def test_non_admins_cannot_widen_scope_with_filters(client, world, tickets):
    body = await dashboard(client, world.emp, facility_id=world.west.id)
    assert body["current"]["active"] == 1 and body["facility_ids"] is None
    body = await dashboard(client, world.west_eng, facility_id=world.hq.id)
    assert {row["display_name"] for row in body["workload"]} == {"West Eng"}

async def test_attention_list_never_leaks_other_peoples_tickets(client, world, tickets):
    # emp2's unassigned Critical ticket is flagged for the admin, but must never reach emp
    assert any(t["reporter"]["id"] == world.emp2.id for t in (await attention_page(client, world.admin, limit=100))["items"])
    body = await attention_page(client, world.emp, limit=100)
    assert all(t["reporter"]["id"] == world.emp.id for t in body["items"])
    assert body["counts"]["total"] == len(body["items"])
    # and the dashboard's flag counts match the same scope
    assert (await dashboard(client, world.emp))["attention_counts"] == body["counts"]

async def test_attention_filters_cannot_widen_scope(client, world, tickets):
    body = await attention_page(client, world.emp, facility_id=world.west.id, limit=100)
    assert all(t["reporter"]["id"] == world.emp.id for t in body["items"])
    body = await attention_page(client, world.admin, facility_id=world.west.id, limit=100)
    assert all(t["location"]["facility"] == "West Campus" for t in body["items"])

async def test_attention_is_paged_and_filterable(client, world, tickets):
    everything = await attention_page(client, world.admin, limit=100)
    first = await attention_page(client, world.admin, limit=1)
    assert first["total"] == everything["total"] and first["items"] == everything["items"][:1]
    unassigned = await attention_page(client, world.admin, kind="unassigned", limit=100)
    assert unassigned["items"] and all(any(f["kind"] == "unassigned" for f in t["flags"]) for t in unassigned["items"])
    response = await client.get("/analytics/attention", params={"limit": 101}, headers=auth(world.admin))
    assert response.status_code == 422

async def test_date_range_and_timezone_validation(client, world, tickets):
    now = datetime.now(timezone.utc)
    headers = auth(world.admin)
    response = await client.get("/analytics/dashboard", params={"start": now.isoformat(), "end": (now - timedelta(days=1)).isoformat()}, headers=headers)
    assert response.status_code == 400
    response = await client.get("/analytics/dashboard", params={"tz": "Mars/Olympus_Mons"}, headers=headers)
    assert response.status_code == 400

    # a window in the past contains nothing
    body = await dashboard(client, world.admin, start=(now - timedelta(days=30)).isoformat(), end=(now - timedelta(days=29)).isoformat())
    assert body["period"]["created"] == 0
    body = await dashboard(client, world.admin, start=(now - timedelta(days=7)).isoformat(), tz="America/New_York")
    assert body["period"]["created"] == 4
