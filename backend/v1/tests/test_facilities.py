# facility > building > floor > seat: campus scoping, delete safety, and the bulk setup wizard
import pytest

from tests.helpers import auth, report


async def names(client, user, path, key="name", **params) -> set[str]:
    response = await client.get(path, params=params, headers=auth(user))
    assert response.status_code == 200, response.text
    return {item[key] for item in response.json()}


# ---------- campus scoping ----------

@pytest.mark.parametrize("role", ["emp", "eng"])
async def test_non_admins_only_see_their_own_campus(client, world, role):
    user = getattr(world, role)
    assert await names(client, user, "/facilities") == {"HQ Campus"}
    assert await names(client, user, "/buildings") == {"Tower", "Annex"}
    assert await names(client, user, "/seats", key="code") == {"T-1-01", "T-2-01"}
    assert len((await client.get("/floors", headers=auth(user))).json()) == 3

async def test_admins_see_every_campus_and_can_narrow_it(client, world):
    assert await names(client, world.admin, "/facilities") == {"HQ Campus", "West Campus"}
    assert await names(client, world.admin, "/buildings") == {"Tower", "Annex", "Hall"}
    assert await names(client, world.admin, "/buildings", facility_id=world.west.id) == {"Hall"}
    assert await names(client, world.admin, "/seats", key="code", facility_id=world.west.id) == {"H-1-01"}

async def test_facility_filter_cannot_widen_a_non_admins_view(client, world):
    # on /buildings facility_id doubles as the parent filter, so asking for West gives nothing rather than HQ.
    # either way, nothing from the other campus comes back
    assert await names(client, world.emp, "/buildings", facility_id=world.west.id) == set()
    assert await names(client, world.emp, "/seats", key="code", facility_id=world.west.id) == {"T-1-01", "T-2-01"}
    assert await names(client, world.emp, "/facilities", facility_id=world.west.id) == {"HQ Campus"}

async def test_other_campus_locations_are_404(client, world):
    for path in (f"/facilities/{world.west.id}", f"/buildings/{world.hall.id}", f"/floors/{world.hall_f1.id}", f"/seats/{world.hall_f1_seat.id}"):
        assert (await client.get(path, headers=auth(world.emp))).status_code == 404, path
        assert (await client.get(path, headers=auth(world.admin))).status_code == 200, path

async def test_parent_filter(client, world):
    assert await names(client, world.admin, "/floors", building_id=world.tower.id) == {"Floor 1", "Floor 2"}
    assert await names(client, world.admin, "/seats", key="code", floor_id=world.tower_f2.id) == {"T-2-01"}

async def test_users_left_without_a_facility_see_nothing(client, world):
    # deleting a campus orphans its users; they must not fall back to seeing every campus
    assert (await client.delete(f"/facilities/{world.west.id}", headers=auth(world.admin))).status_code == 204
    assert (await client.get("/auth/me", headers=auth(world.west_emp))).json()["facility_id"] is None
    for path in ("/facilities", "/buildings", "/floors", "/seats"):
        assert (await client.get(path, headers=auth(world.west_emp))).json() == [], path


# ---------- CRUD + delete safety ----------

async def test_admin_crud_on_each_level(client, world):
    headers = auth(world.admin)
    facility = (await client.post("/facilities", json={"name": "North Campus"}, headers=headers)).json()
    building = (await client.post("/buildings", json={"facility_id": facility["id"], "name": "Depot"}, headers=headers)).json()
    floor = (await client.post("/floors", json={"building_id": building["id"], "name": "Ground"}, headers=headers)).json()
    seat = await client.post("/seats", json={"floor_id": floor["id"], "code": "D-G-01"}, headers=headers)
    assert seat.status_code == 201

    response = await client.patch(f"/buildings/{building['id']}", json={"name": "Main Depot"}, headers=headers)
    assert response.json()["name"] == "Main Depot"

async def test_children_need_an_existing_parent(client, world):
    headers = auth(world.admin)
    assert (await client.post("/buildings", json={"facility_id": 99999, "name": "X"}, headers=headers)).status_code == 404
    assert (await client.post("/floors", json={"building_id": 99999, "name": "X"}, headers=headers)).status_code == 404
    assert (await client.post("/seats", json={"floor_id": 99999, "code": "X"}, headers=headers)).status_code == 404
    assert (await client.patch(f"/floors/{world.tower_f1.id}", json={"building_id": 99999}, headers=headers)).status_code == 404

async def test_names_are_unique_within_their_parent(client, world):
    headers = auth(world.admin)
    assert (await client.post("/facilities", json={"name": "HQ Campus"}, headers=headers)).status_code == 409
    assert (await client.post("/buildings", json={"facility_id": world.hq.id, "name": "Tower"}, headers=headers)).status_code == 409
    # the same name at a different campus is fine
    assert (await client.post("/buildings", json={"facility_id": world.west.id, "name": "Tower"}, headers=headers)).status_code == 201

async def test_locations_with_incidents_cannot_be_deleted_only_deactivated(client, world):
    await report(client, world.emp, world.tower, floor_id=world.tower_f1.id, seat_id=world.tower_f1_seat.id)
    headers = auth(world.admin)
    for path in (f"/facilities/{world.hq.id}", f"/buildings/{world.tower.id}", f"/floors/{world.tower_f1.id}", f"/seats/{world.tower_f1_seat.id}"):
        assert (await client.delete(path, headers=headers)).status_code == 409, path

    response = await client.patch(f"/buildings/{world.tower.id}", json={"is_active": False}, headers=headers)
    assert response.status_code == 200 and response.json()["is_active"] is False
    assert await names(client, world.emp, "/buildings", is_active="true") == {"Annex"}

async def test_delete_impact_and_cascading_delete(client, world):
    headers = auth(world.admin)
    impact = (await client.get(f"/facilities/{world.hq.id}/delete-impact", headers=headers)).json()
    assert impact == {"buildings": 2, "floors": 3, "seats": 2, "incidents": 0, "users": 6}

    assert (await client.delete(f"/buildings/{world.tower.id}", headers=headers)).status_code == 204
    assert await names(client, world.admin, "/buildings", facility_id=world.hq.id) == {"Annex"}
    assert (await client.get(f"/floors/{world.tower_f1.id}", headers=headers)).status_code == 404
    assert (await client.get(f"/seats/{world.tower_f1_seat.id}", headers=headers)).status_code == 404


# ---------- setup wizard ----------

async def test_setup_wizard_creates_a_whole_campus(client, world):
    response = await client.post("/facilities/setup", headers=auth(world.admin), json={
        "name": "  East Campus ", "address": "9 River Rd",
        "buildings": [
            {"name": "North Tower", "code": "nt", "floors": 3, "seats_per_floor": 2},
            {"name": "Annex", "code": "AN", "floors": 1, "seats_per_floor": 0},
        ],
    })
    assert response.status_code == 201
    body = response.json()
    assert body["facility"]["name"] == "East Campus"
    assert (body["buildings"], body["floors"], body["seats"]) == (2, 4, 6)

    facility_id = body["facility"]["id"]
    assert await names(client, world.admin, "/buildings", facility_id=facility_id) == {"North Tower", "Annex"}
    codes = await names(client, world.admin, "/seats", key="code", facility_id=facility_id)
    assert codes == {"NT-1-01", "NT-1-02", "NT-2-01", "NT-2-02", "NT-3-01", "NT-3-02"}

async def test_setup_wizard_rejects_duplicates(client, world):
    plan = [{"name": "A", "code": "A", "floors": 1, "seats_per_floor": 1}]
    headers = auth(world.admin)
    assert (await client.post("/facilities/setup", json={"name": "hq campus", "buildings": plan}, headers=headers)).status_code == 409
    response = await client.post(f"/facilities/{world.hq.id}/buildings/bulk", headers=headers, json={
        "buildings": [{"name": "TOWER", "code": "T2", "floors": 1, "seats_per_floor": 1}],
    })
    assert response.status_code == 409

@pytest.mark.parametrize("buildings", [
    [],
    [{"name": "A", "code": "A", "floors": 1, "seats_per_floor": 1}, {"name": "a", "code": "B", "floors": 1, "seats_per_floor": 1}],
    [{"name": "A", "code": "X", "floors": 1, "seats_per_floor": 1}, {"name": "B", "code": "x", "floors": 1, "seats_per_floor": 1}],
    [{"name": "A", "code": "A-1", "floors": 1, "seats_per_floor": 1}],            # code must be alphanumeric
    [{"name": "A", "code": "A", "floors": 0, "seats_per_floor": 1}],
    [{"name": "A", "code": "A", "floors": 101, "seats_per_floor": 1}],
    [{"name": f"B{i}", "code": f"B{i}", "floors": 100, "seats_per_floor": 200} for i in range(2)],  # over the seat cap
])
async def test_setup_wizard_validates_the_plan(client, world, buildings):
    response = await client.post("/facilities/setup", json={"name": "Bad Plan", "buildings": buildings}, headers=auth(world.admin))
    assert response.status_code == 422
