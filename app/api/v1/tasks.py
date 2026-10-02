from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import (
    get_current_user,
    get_current_membership,
    require_role,
)
from app.models.user import User
from app.models.membership import TenantMember, TenantRole
from app.models.project import TaskStatus
from app.schemas.project import TaskCreate, TaskUpdate, TaskResponse
from app.services.project_service import ProjectService
from app.services.notification_service import ws_manager
from app.services.audit_service import AuditService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(TenantRole.MEMBER))],
)
async def create_task(
    project_id: str,
    data: TaskCreate,
    membership: TenantMember = Depends(get_current_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task within a workspace project (Requires MEMBER+ role)."""
    task = await ProjectService.create_task(db, membership.tenant_id, project_id, data)

    # Real-time WebSocket broadcast to all connected workspace members
    await ws_manager.broadcast_to_tenant(
        tenant_id=membership.tenant_id,
        event_type="task.created",
        data={
            "task_id": task.id,
            "title": task.title,
            "project_id": task.project_id,
            "status": task.status.value,
            "created_by": current_user.email,
        },
    )

    await AuditService.log_event(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        action="task.created",
        entity_type="task",
        entity_id=task.id,
        details=f"Task '{task.title}' created in project {project_id}",
    )
    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    project_id: Optional[str] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    membership: TenantMember = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
):
    """List tasks in the workspace with optional project and status filters."""
    return await ProjectService.list_tasks(
        db, tenant_id=membership.tenant_id, project_id=project_id, status=status
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    membership: TenantMember = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
):
    """Get single task details."""
    return await ProjectService.get_task(db, membership.tenant_id, task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(require_role(TenantRole.MEMBER))],
)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    membership: TenantMember = Depends(get_current_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update task details (e.g. status transition, assignee)."""
    task = await ProjectService.update_task(db, membership.tenant_id, task_id, data)

    # Broadcast task update (e.g. kanban card drag-and-drop)
    await ws_manager.broadcast_to_tenant(
        tenant_id=membership.tenant_id,
        event_type="task.updated",
        data={
            "task_id": task.id,
            "title": task.title,
            "status": task.status.value,
            "updated_by": current_user.email,
        },
    )

    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(TenantRole.ADMIN))],
)
async def delete_task(
    task_id: str,
    membership: TenantMember = Depends(get_current_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task (Requires ADMIN+ role)."""
    await ProjectService.delete_task(db, membership.tenant_id, task_id)

    await ws_manager.broadcast_to_tenant(
        tenant_id=membership.tenant_id,
        event_type="task.deleted",
        data={"task_id": task_id, "deleted_by": current_user.email},
    )
