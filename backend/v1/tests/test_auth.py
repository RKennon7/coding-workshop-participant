# login, invite-based registration, password changes, and how bearer tokens are validated
from datetime import timedelta

import pytest

from app.database import AsyncSessionLocal
from app.models import User
from app.routers import auth as auth_router
from app.security import DUMMY_PASSWORD_HASH, create_access_token, decode_access_token
from tests.conftest import PASSWORD
from tests.helpers import auth, bearer, token_for


async def login(client, username: str, password: str = PASSWORD):
    return await client.post("/auth/token", data={"username": username, "password": password})


# ---------- login ----------

async def test_login_with_username_returns_token_for_that_user(client, world):
    response = await login(client, "emp")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    claims = decode_access_token(body["access_token"])
    assert claims["uid"] == world.emp.id and claims["role"] == "Employee"

async def test_login_with_email_is_case_insensitive(client, world):
    response = await login(client, "  EMP@ACME.INC ")
    assert response.status_code == 200

@pytest.mark.parametrize("username, password", [
    ("emp", "wrong-password"),
    ("nobody", PASSWORD),     # unknown user
    ("invited", PASSWORD),    # invited but never registered (no password set)
    ("inactive", PASSWORD),   # deactivated account
])
async def test_failed_logins_all_look_the_same(client, world, username, password):
    response = await login(client, username, password)
    assert response.status_code == 401
    # one message for every failure, so the response doesn't reveal which accounts exist
    assert response.json()["detail"] == "incorrect username or password"
    assert response.headers["www-authenticate"] == "Bearer"

async def test_login_runs_bcrypt_even_for_unknown_users(client, world, monkeypatch):
    # skipping the hash check for unknown users would make them measurably faster to reject
    checked = []
    monkeypatch.setattr(auth_router, "verify_password", lambda plain, hashed: checked.append(hashed) or False)
    await login(client, "nobody")
    assert checked == [DUMMY_PASSWORD_HASH]

async def test_login_requires_form_fields(client, world):
    response = await client.post("/auth/token", json={"username": "emp", "password": PASSWORD})
    assert response.status_code == 422


# ---------- registration ----------

async def test_invited_user_can_register_and_is_logged_in(client, world):
    response = await client.post("/auth/register", json={"email": "Invited@acme.inc", "password": "my-new-password"})
    assert response.status_code == 201
    token = response.json()["access_token"]

    me = await client.get("/auth/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.json()["username"] == "invited" and me.json()["is_registered"] is True
    assert (await login(client, "invited", "my-new-password")).status_code == 200

async def test_register_keeps_the_role_the_admin_chose(client, world):
    # the request can't smuggle in a role: RegisterRequest has no such field
    response = await client.post(
        "/auth/register", json={"email": "invited@acme.inc", "password": "my-new-password", "role": "Facility Admin"},
    )
    assert decode_access_token(response.json()["access_token"])["role"] == "Employee"

async def test_cannot_register_an_email_no_admin_invited(client, world):
    response = await client.post("/auth/register", json={"email": "stranger@acme.inc", "password": "my-new-password"})
    assert response.status_code == 400

async def test_cannot_take_over_an_already_registered_account(client, world):
    response = await client.post("/auth/register", json={"email": "emp@acme.inc", "password": "attacker-password"})
    assert response.status_code == 409
    assert (await login(client, "emp")).status_code == 200  # original password still works

async def test_deactivated_invite_cannot_register(client, world):
    async with AsyncSessionLocal() as db:
        invited = await db.get(User, world.invited.id)
        invited.is_active = False
        await db.commit()
    response = await client.post("/auth/register", json={"email": "invited@acme.inc", "password": "my-new-password"})
    assert response.status_code == 400

@pytest.mark.parametrize("body", [
    {"email": "invited@gmail.com", "password": "my-new-password"},
    {"email": "invited@acme.inc", "password": "short"},
    {"email": "invited@acme.inc"},
])
async def test_register_validates_input(client, world, body):
    assert (await client.post("/auth/register", json=body)).status_code == 422


# ---------- current user + password change ----------

async def test_me_returns_profile_without_password_hash(client, world):
    response = await client.get("/auth/me", headers=auth(world.emp))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == world.emp.id
    assert body["facility_name"] == "HQ Campus"
    assert "password_hash" not in body and "password" not in body

async def test_change_password(client, world):
    response = await client.post(
        "/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "brand-new-password"},
        headers=auth(world.emp),
    )
    assert response.status_code == 204
    assert (await login(client, "emp", "brand-new-password")).status_code == 200
    assert (await login(client, "emp", PASSWORD)).status_code == 401

async def test_change_password_requires_current_password(client, world):
    response = await client.post(
        "/auth/change-password",
        json={"current_password": "not-my-password", "new_password": "brand-new-password"},
        headers=auth(world.emp),
    )
    assert response.status_code == 400
    assert (await login(client, "emp")).status_code == 200


# ---------- bearer token validation ----------

async def test_missing_token_is_rejected(client, world):
    response = await client.get("/auth/me")
    assert response.status_code == 401

@pytest.mark.parametrize("header", [
    "Bearer not-a-jwt",
    "Bearer ",
    "Basic ZW1wOnBhc3N3b3Jk",
    "",
])
async def test_malformed_authorization_header_is_rejected(client, world, header):
    response = await client.get("/auth/me", headers={"Authorization": header})
    assert response.status_code == 401

async def test_expired_token_is_rejected(client, world):
    token = create_access_token({"sub": "emp", "uid": world.emp.id}, expires_delta=timedelta(seconds=-1))
    assert (await client.get("/auth/me", headers=bearer(token))).status_code == 401

async def test_token_without_integer_uid_is_rejected(client, world):
    # older tokens identified users by username only; they must not work any more
    assert (await client.get("/auth/me", headers=bearer(create_access_token({"sub": "emp"})))).status_code == 401
    assert (await client.get("/auth/me", headers=bearer(token_for(world.emp, uid=str(world.emp.id))))).status_code == 401

async def test_token_for_deleted_user_is_rejected(client, world):
    assert (await client.get("/auth/me", headers=bearer(token_for(world.emp, uid=99999)))).status_code == 401

async def test_deactivated_user_is_locked_out_even_with_a_valid_token(client, world):
    headers = auth(world.emp)
    assert (await client.get("/auth/me", headers=headers)).status_code == 200
    response = await client.patch(f"/users/{world.emp.id}", json={"is_active": False}, headers=auth(world.admin))
    assert response.status_code == 200
    assert (await client.get("/auth/me", headers=headers)).status_code == 401

async def test_role_and_username_claims_are_not_trusted(client, world):
    # a token claiming to be the admin, but for the employee's uid, is the employee: the user comes from the db
    forged = token_for(world.emp, sub="admin", role="Facility Admin")
    me = await client.get("/auth/me", headers=bearer(forged))
    assert me.json()["username"] == "emp"
    assert (await client.get("/users", headers=bearer(forged))).status_code == 403

async def test_health_check_is_public(client):
    response = await client.get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
