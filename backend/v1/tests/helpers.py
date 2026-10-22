# shared helpers for calling the API as a given user
from httpx import AsyncClient

from app.models import Building, User
from app.security import create_access_token

# same claims the login endpoint issues (see routers/auth.py)
def token_for(user: User, **overrides) -> str:
    claims = {"sub": user.username, "uid": user.id, "role": user.role.value, **overrides}
    return create_access_token(data=claims)

def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user)}"}

def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

# reports an incident as `reporter` and returns the created ticket
async def report(client: AsyncClient, reporter: User, building: Building, **fields) -> dict:
    body = {"title": "Broken chair", "description": "The seat wobbles", "category": "Furniture", "building_id": building.id}
    response = await client.post("/incidents", json=body | fields, headers=auth(reporter))
    assert response.status_code == 201, response.text
    return response.json()

async def patch_incident(client: AsyncClient, user: User, incident_id: int, **fields):
    return await client.patch(f"/incidents/{incident_id}", json=fields, headers=auth(user))

# admin-driven setup step, e.g. assign an engineer or move a ticket into a status. asserts it worked
async def admin_patch(client: AsyncClient, admin: User, incident_id: int, **fields) -> dict:
    response = await patch_incident(client, admin, incident_id, **fields)
    assert response.status_code == 200, response.text
    return response.json()
