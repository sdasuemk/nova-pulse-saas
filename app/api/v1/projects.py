from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import (
    get_current_user,
    get_current_membership,
    require_role,
)
from app.models.user import User
from app.models.membership import TenantMember, TenantRole
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
)
from app.services.project_service import ProjectService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(TenantRole.MEMBER))],
)
async def create_project(
    data: ProjectCreate,
    membership: TenantMember = Depends(get_current_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a project inside the current workspace (Requires MEMBER+ role)."""
    project = await ProjectService.create_project(db, membership.tenant_id, data)
    await AuditService.log_event(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        action="project.created",
        entity_type="project",
        entity_id=project.id,
        details=f"Project '{project.name}' created",
    )
    return project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    membership: TenantMember = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
):
    """List all projects in the workspace."""
    return await ProjectService.list_projects(db, membership.tenant_id)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    membership: TenantMember = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
):
    """Get project details along with its tasks."""
    return await ProjectService.get_project(db, membership.tenant_id, project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(require_role(TenantRole.ADMIN))],
)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    membership: TenantMember = Depends(get_current_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update project details (Requires ADMIN+ role)."""
    project = await ProjectService.update_project(db, membership.tenant_id, project_id, data)
    await AuditService.log_event(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        action="project.updated",
        entity_type="project",
        entity_id=project.id,
        details=f"Project '{project.name}' updated",
    )
    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(TenantRole.ADMIN))],
)
async def delete_project(
    project_id: str,
    membership: TenantMember = Depends(get_current_membership),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project and its tasks (Requires ADMIN+ role)."""
    await ProjectService.delete_project(db, membership.tenant_id, project_id)
    await AuditService.log_event(
        db=db,
        tenant_id=membership.tenant_id,
        user_id=current_user.id,
        action="project.deleted",
        entity_type="project",
        entity_id=project_id,
    )
