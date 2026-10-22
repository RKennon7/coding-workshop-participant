# admin user management: invites, validation, and the guards that stop an admin locking themselves out
import pytest

from tests.helpers import auth, report


async def create_user(client, admin, **fields):
    return await client.post("/users", json=fields, headers=auth(admin))


async def test_admin_invites_a_user_who_then_registers(client, world):
    response = await create_user(client, world.admin, username="newhire", email="NewHire@acme.inc", facility_id=world.hq.id)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "newhire@acme.inc"
    assert body["role"] == "Employee" and body["is_registered"] is False
    assert "password_hash" not in body

    response = await client.post("/auth/register", json={"email": "newhire@acme.inc", "password": "first-password"})
    assert response.status_code == 201

async def test_admin_can_create_a_user_with_a_password(client, world):
    response = await create_user(
        client, world.admin, username="tech", email="tech@acme.inc", role="Engineer",
        facility_id=world.hq.id, password="temporary-pass",
    )
    assert response.status_code == 201 and response.json()["is_registered"] is True
    login = await client.post("/auth/token", data={"username": "tech", "password": "temporary-pass"})
    assert login.status_code == 200

async def test_user_list_never_exposes_password_hashes(client, world):
    response = await client.get("/users", headers=auth(world.admin))
    assert response.status_code == 200
    assert len(response.json()) == 9
    assert all("password_hash" not in user for user in response.json())

async def test_user_list_filters(client, world):
    headers = auth(world.admin)
    engineers = (await client.get("/users", params={"role": "Engineer"}, headers=headers)).json()
    assert {u["username"] for u in engineers} == {"eng", "eng2", "westeng", "inactive"}
    west = (await client.get("/users", params={"facility_id": world.west.id}, headers=headers)).json()
    assert {u["username"] for u in west} == {"westeng", "westemp"}
    found = (await client.get("/users", params={"q": "EMP2"}, headers=headers)).json()
    assert [u["username"] for u in found] == ["emp2"]
    inactive = (await client.get("/users", params={"is_active": "false"}, headers=headers)).json()
    assert [u["username"] for u in inactive] == ["inactive"]

@pytest.mark.parametrize("fields", [
    {"username": "outsider", "email": "outsider@gmail.com"},
    {"username": "ab", "email": "ab@acme.inc"},                                 # username too short
    {"username": "weakpass", "email": "weakpass@acme.inc", "password": "short"},
    {"username": "badrole", "email": "badrole@acme.inc", "role": "Superuser"},
])
async def test_create_user_validates_input(client, world, fields):
    assert (await create_user(client, world.admin, facility_id=world.hq.id, **fields)).status_code == 422

async def test_usernames_and_emails_are_unique(client, world):
    response = await create_user(client, world.admin, username="emp", email="someone@acme.inc", facility_id=world.hq.id)
    assert response.status_code == 409
    # emails are compared after lowercasing
    response = await create_user(client, world.admin, username="someone", email="EMP@acme.inc", facility_id=world.hq.id)
    assert response.status_code == 409
    response = await client.patch(f"/users/{world.emp2.id}", json={"email": "emp@acme.inc"}, headers=auth(world.admin))
    assert response.status_code == 409

async def test_non_admins_need_a_facility(client, world):
    for role in ("Employee", "Engineer"):
        response = await create_user(client, world.admin, username=f"no{role.lower()}", email=f"no{role.lower()}@acme.inc", role=role)
        assert response.status_code == 400, role
    response = await create_user(client, world.admin, username="admin2", email="admin2@acme.inc", role="Facility Admin")
    assert response.status_code == 201
    response = await create_user(client, world.admin, username="ghost", email="ghost@acme.inc", facility_id=99999)
    assert response.status_code == 404

async def test_demoting_an_admin_without_a_facility_is_rejected(client, world):
    second = (await create_user(client, world.admin, username="admin2", email="admin2@acme.inc", role="Facility Admin")).json()
    response = await client.patch(f"/users/{second['id']}", json={"role": "Employee"}, headers=auth(world.admin))
    assert response.status_code == 400
    response = await client.patch(f"/users/{second['id']}", json={"role": "Employee", "facility_id": world.hq.id}, headers=auth(world.admin))
    assert response.status_code == 200

async def test_promoting_a_user_takes_effect_immediately(client, world):
    headers = auth(world.emp)  # issued while they were an Employee
    assert (await client.get("/users", headers=headers)).status_code == 403
    await client.patch(f"/users/{world.emp.id}", json={"role": "Facility Admin"}, headers=auth(world.admin))
    assert (await client.get("/users", headers=headers)).status_code == 200

async def test_admin_cannot_lock_themselves_out(client, world):
    path = f"/users/{world.admin.id}"
    headers = auth(world.admin)
    assert (await client.patch(path, json={"is_active": False}, headers=headers)).status_code == 400
    assert (await client.patch(path, json={"role": "Employee", "facility_id": world.hq.id}, headers=headers)).status_code == 400
    assert (await client.delete(path, headers=headers)).status_code == 400
    assert (await client.get("/auth/me", headers=headers)).json()["role"] == "Facility Admin"

async def test_users_with_history_cannot_be_deleted_only_deactivated(client, world):
    await report(client, world.emp2, world.tower)
    response = await client.delete(f"/users/{world.emp2.id}", headers=auth(world.admin))
    assert response.status_code == 409
    # the error response doesn't leak database internals
    assert "incidents" not in response.text.lower() and "violates" not in response.text.lower()

    response = await client.patch(f"/users/{world.emp2.id}", json={"is_active": False}, headers=auth(world.admin))
    assert response.status_code == 200 and response.json()["is_active"] is False

async def test_users_without_history_can_be_deleted(client, world):
    assert (await client.delete(f"/users/{world.invited.id}", headers=auth(world.admin))).status_code == 204
    assert (await client.get(f"/users/{world.invited.id}", headers=auth(world.admin))).status_code == 404
