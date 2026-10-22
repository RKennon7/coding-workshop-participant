# engineer profiles: self-service limits, campus scoping, and admin-side validation
import pytest

from tests.helpers import auth


async def test_engineers_only_see_colleagues_at_their_campus(client, world):
    response = await client.get("/engineers", headers=auth(world.eng))
    assert {p["display_name"] for p in response.json()} == {"Eng One", "Eng Two"}
    assert (await client.get(f"/engineers/{world.west_eng_profile.id}", headers=auth(world.eng))).status_code == 404

async def test_admins_see_all_engineers_and_can_filter(client, world):
    headers = auth(world.admin)
    assert len((await client.get("/engineers", headers=headers)).json()) == 3
    west = (await client.get("/engineers", params={"facility_id": world.west.id}, headers=headers)).json()
    assert [p["display_name"] for p in west] == ["West Eng"]
    hvac = (await client.get("/engineers", params={"specialty": "HVAC"}, headers=headers)).json()
    assert [p["display_name"] for p in hvac] == ["Eng One"]

async def test_engineer_can_update_own_contact_and_availability(client, world):
    path = f"/engineers/{world.eng_profile.id}"
    response = await client.patch(path, json={"phone": "555-0100", "is_available": False}, headers=auth(world.eng))
    assert response.status_code == 200
    assert response.json()["phone"] == "555-0100" and response.json()["is_available"] is False

@pytest.mark.parametrize("field, value", [
    ("max_open_tickets", 99),
    ("display_name", "Senior Eng"),
    ("specialty", "Electrical"),
])
async def test_engineer_cannot_change_admin_managed_fields(client, world, field, value):
    response = await client.patch(f"/engineers/{world.eng_profile.id}", json={field: value}, headers=auth(world.eng))
    assert response.status_code == 403

async def test_engineer_cannot_edit_a_colleagues_profile(client, world):
    response = await client.patch(f"/engineers/{world.eng2_profile.id}", json={"is_available": False}, headers=auth(world.eng))
    assert response.status_code == 403

async def test_admin_manages_profiles(client, world):
    headers = auth(world.admin)
    response = await client.patch(f"/engineers/{world.eng_profile.id}", json={"max_open_tickets": 4, "specialty": "Plumbing"}, headers=headers)
    assert response.status_code == 200 and response.json()["max_open_tickets"] == 4

    assert (await client.delete(f"/engineers/{world.eng2_profile.id}", headers=headers)).status_code == 204
    response = await client.post("/engineers", json={"user_id": world.eng2.id, "display_name": "Eng Two again"}, headers=headers)
    assert response.status_code == 201 and response.json()["facility_id"] == world.hq.id

async def test_profiles_are_only_for_engineers_and_one_each(client, world):
    headers = auth(world.admin)
    assert (await client.post("/engineers", json={"user_id": world.emp.id, "display_name": "Not an engineer"}, headers=headers)).status_code == 400
    assert (await client.post("/engineers", json={"user_id": world.eng.id, "display_name": "Duplicate"}, headers=headers)).status_code == 409
    assert (await client.post("/engineers", json={"user_id": 99999, "display_name": "Nobody"}, headers=headers)).status_code == 404

async def test_capacity_must_be_positive(client, world):
    response = await client.patch(f"/engineers/{world.eng_profile.id}", json={"max_open_tickets": 0}, headers=auth(world.admin))
    assert response.status_code == 422
