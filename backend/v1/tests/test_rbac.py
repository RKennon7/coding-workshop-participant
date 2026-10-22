# endpoint-level role checks: who may call what at all. per-ticket and per-field rules live in test_incidents.py
import pytest

from app.database import AsyncSessionLocal
from app.models import Facility, User
from tests.helpers import auth, report

# (method, path, body) built from the seeded world. every one of these must be Facility Admin only
ADMIN_ONLY = {
    "list users": lambda w: ("GET", "/users", None),
    "get user": lambda w: ("GET", f"/users/{w.emp2.id}", None),
    "create user": lambda w: ("POST", "/users", {"username": "sneaky", "email": "sneaky@acme.inc", "role": "Facility Admin"}),
    "update user": lambda w: ("PATCH", f"/users/{w.emp2.id}", {"role": "Facility Admin"}),
    "delete user": lambda w: ("DELETE", f"/users/{w.emp2.id}", None),
    "create facility": lambda w: ("POST", "/facilities", {"name": "Rogue Campus"}),
    "update facility": lambda w: ("PATCH", f"/facilities/{w.hq.id}", {"name": "Renamed"}),
    "delete facility": lambda w: ("DELETE", f"/facilities/{w.hq.id}", None),
    "facility delete impact": lambda w: ("GET", f"/facilities/{w.hq.id}/delete-impact", None),
    "facility setup wizard": lambda w: ("POST", "/facilities/setup", {
        "name": "Rogue Campus", "buildings": [{"name": "A", "code": "A", "floors": 1, "seats_per_floor": 1}],
    }),
    "bulk add buildings": lambda w: ("POST", f"/facilities/{w.hq.id}/buildings/bulk", {
        "buildings": [{"name": "B", "code": "B", "floors": 1, "seats_per_floor": 1}],
    }),
    "create building": lambda w: ("POST", "/buildings", {"facility_id": w.hq.id, "name": "Shed"}),
    "update building": lambda w: ("PATCH", f"/buildings/{w.tower.id}", {"is_active": False}),
    "delete building": lambda w: ("DELETE", f"/buildings/{w.annex.id}", None),
    "create floor": lambda w: ("POST", "/floors", {"building_id": w.tower.id, "name": "Roof"}),
    "delete floor": lambda w: ("DELETE", f"/floors/{w.tower_f2.id}", None),
    "create seat": lambda w: ("POST", "/seats", {"floor_id": w.tower_f1.id, "code": "T-1-99"}),
    "delete seat": lambda w: ("DELETE", f"/seats/{w.tower_f1_seat.id}", None),
    "create engineer profile": lambda w: ("POST", "/engineers", {"user_id": w.inactive_eng.id, "display_name": "X"}),
    "delete engineer profile": lambda w: ("DELETE", f"/engineers/{w.eng2_profile.id}", None),
}

@pytest.mark.parametrize("role", ["eng", "emp"])
@pytest.mark.parametrize("case", ADMIN_ONLY.values(), ids=ADMIN_ONLY.keys())
async def test_admin_only_endpoints_reject_engineers_and_employees(client, world, role, case):
    method, path, body = case(world)
    response = await client.request(method, path, json=body, headers=auth(getattr(world, role)))
    assert response.status_code == 403, response.text

@pytest.mark.parametrize("case", ADMIN_ONLY.values(), ids=ADMIN_ONLY.keys())
async def test_admin_only_endpoints_reject_anonymous_callers(client, world, case):
    method, path, body = case(world)
    assert (await client.request(method, path, json=body)).status_code == 401

async def test_admin_can_use_admin_endpoints(client, world):
    # positive control, so the 403s above can't come from the endpoints simply being broken
    headers = auth(world.admin)
    assert (await client.get("/users", headers=headers)).status_code == 200
    assert (await client.post("/facilities", json={"name": "New Campus"}, headers=headers)).status_code == 201
    assert (await client.delete(f"/seats/{world.tower_f1_seat.id}", headers=headers)).status_code == 204

async def test_rejected_requests_change_nothing(client, world):
    await client.delete(f"/facilities/{world.hq.id}", headers=auth(world.emp))
    await client.patch(f"/users/{world.emp2.id}", json={"role": "Facility Admin"}, headers=auth(world.eng))
    async with AsyncSessionLocal() as db:
        assert await db.get(Facility, world.hq.id) is not None
        assert (await db.get(User, world.emp2.id)).role.value == "Employee"

async def test_only_admins_can_delete_incidents(client, world):
    incident = await report(client, world.emp, world.tower)
    # not even the reporter
    assert (await client.delete(f"/incidents/{incident['id']}", headers=auth(world.emp))).status_code == 403
    assert (await client.delete(f"/incidents/{incident['id']}", headers=auth(world.eng))).status_code == 403
    assert (await client.delete(f"/incidents/{incident['id']}", headers=auth(world.admin))).status_code == 204
    assert (await client.get(f"/incidents/{incident['id']}", headers=auth(world.admin))).status_code == 404

async def test_engineer_roster_is_hidden_from_employees(client, world):
    assert (await client.get("/engineers", headers=auth(world.emp))).status_code == 403
    assert (await client.get(f"/engineers/{world.eng_profile.id}", headers=auth(world.emp))).status_code == 403
    assert (await client.patch(f"/engineers/{world.eng_profile.id}", json={"is_available": False}, headers=auth(world.emp))).status_code == 403
    assert (await client.get("/engineers", headers=auth(world.eng))).status_code == 200

@pytest.mark.parametrize("path", [
    "/auth/me", "/users", "/facilities", "/buildings", "/floors", "/seats",
    "/engineers", "/incidents", "/incidents/1", "/incidents/1/notes", "/incidents/1/history", "/analytics/dashboard",
])
async def test_every_data_endpoint_requires_login(client, path):
    response = await client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
