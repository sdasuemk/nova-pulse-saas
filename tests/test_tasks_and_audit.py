import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_task_crud_and_audit_logging(client: AsyncClient):
    # 1. Register user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dev@company.com",
            "password": "ProductionPassword123!",
            "full_name": "Lead Architect",
            "workspace_name": "Core Dev Workspace",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["data"]["tokens"]["access_token"]
    user_id = reg_res.json()["data"]["user"]["id"]

    # 2. Get workspace ID
    ws_res = await client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    tenant_id = ws_res.json()[0]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    # 3. Create project
    proj_res = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "SaaS Platform v1", "description": "Production MVP"},
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 4. Create task
    task_res = await client.post(
        f"/api/v1/tasks?project_id={project_id}",
        headers=headers,
        json={
            "title": "Implement Redis Cache",
            "description": "Cache frequent workspace queries",
            "status": "todo",
            "priority": "high",
            "assignee_id": user_id,
        },
    )
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    # 5. Move task status to in_progress
    update_res = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "in_progress"

    # 6. Verify audit logs (Owner/Admin can view workspace audit trail)
    audit_res = await client.get("/api/v1/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    actions = [log["action"] for log in logs]
    assert "workspace.created" in actions
    assert "project.created" in actions
    assert "task.created" in actions
