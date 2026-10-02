import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["database"] == "healthy"


@pytest.mark.asyncio
async def test_user_registration_and_login(client: AsyncClient):
    payload = {
        "email": "sarah.connor@example.com",
        "password": "Password123!",
        "full_name": "Sarah Connor",
        "workspace_name": "Resistance HQ",
    }
    # 1. Register
    reg_res = await client.post("/api/v1/auth/register", json=payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["success"] is True
    assert reg_data["data"]["user"]["email"] == payload["email"]
    assert "access_token" in reg_data["data"]["tokens"]

    # 2. Login with valid credentials
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    access_token = token_data["access_token"]
    assert access_token is not None

    # 3. Access protected /me endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == payload["email"]

    # 4. Login with invalid password
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401
