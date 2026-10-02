import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_multi_tenant_isolation_and_rbac(client: AsyncClient):
    # 1. Register User Alice
    alice_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@startup.io",
            "password": "SuperSecretPassword1!",
            "full_name": "Alice Founder",
            "workspace_name": "Acme SaaS",
        },
    )
    assert alice_res.status_code == 201
    alice_token = alice_res.json()["data"]["tokens"]["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    # Alice fetches her workspaces
    alice_ws_res = await client.get("/api/v1/workspaces", headers=alice_headers)
    assert alice_ws_res.status_code == 200
    workspaces = alice_ws_res.json()
    assert len(workspaces) >= 1
    acme_id = workspaces[0]["id"]

    # 2. Alice creates a Project in Acme SaaS
    alice_headers_with_tenant = {
        "Authorization": f"Bearer {alice_token}",
        "X-Tenant-ID": acme_id,
    }
    proj_res = await client.post(
        "/api/v1/projects",
        headers=alice_headers_with_tenant,
        json={"name": "Billing Engine v2", "description": "Core subscription engine"},
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # Alice creates a Task in that project
    task_res = await client.post(
        f"/api/v1/tasks?project_id={project_id}",
        headers=alice_headers_with_tenant,
        json={
            "title": "Setup Stripe Webhooks",
            "description": "Handle invoice.paid events",
            "priority": "high",
        },
    )
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    # 3. Register User Bob (Belongs to his own workspace)
    bob_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@outsider.io",
            "password": "BobSecretPassword1!",
            "full_name": "Bob Outsider",
            "workspace_name": "Bob Corp",
        },
    )
    assert bob_res.status_code == 201
    bob_token = bob_res.json()["data"]["tokens"]["access_token"]

    # 4. Bob tries to access Alice's Acme workspace project -> MUST RETURN 403 FORBIDDEN
    bob_sneaky_headers = {
        "Authorization": f"Bearer {bob_token}",
        "X-Tenant-ID": acme_id,
    }
    forbidden_res = await client.get(
        f"/api/v1/projects/{project_id}",
        headers=bob_sneaky_headers,
    )
    assert forbidden_res.status_code == 403
    assert "not a member" in forbidden_res.json()["error"]["message"]

    # 5. Alice invites Bob to Acme SaaS as 'viewer'
    invite_res = await client.post(
        f"/api/v1/workspaces/{acme_id}/members",
        headers=alice_headers_with_tenant,
        json={"email": "bob@outsider.io", "role": "viewer"},
    )
    assert invite_res.status_code == 200

    # 6. Now Bob can view the project
    bob_view_res = await client.get(
        f"/api/v1/projects/{project_id}",
        headers=bob_sneaky_headers,
    )
    assert bob_view_res.status_code == 200
    assert bob_view_res.json()["name"] == "Billing Engine v2"

    # But Bob as 'viewer' CANNOT create tasks (requires MEMBER) -> 403
    bob_blocked_task = await client.post(
        f"/api/v1/tasks?project_id={project_id}",
        headers=bob_sneaky_headers,
        json={"title": "Unauthorized Task", "priority": "low"},
    )
    assert bob_blocked_task.status_code == 403

    # 7. Alice promotes Bob to 'admin'
    promote_res = await client.post(
        f"/api/v1/workspaces/{acme_id}/members",
        headers=alice_headers_with_tenant,
        json={"email": "bob@outsider.io", "role": "admin"},
    )
    assert promote_res.status_code == 200

    # Bob can now delete tasks (Requires ADMIN)
    bob_delete_task = await client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=bob_sneaky_headers,
    )
    assert bob_delete_task.status_code == 204
