from typing import List
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import (
    get_current_user,
    get_current_membership,
    require_role,
)
from app.models.user import User
from app.models.membership import TenantMember, TenantRole
from app.schemas.tenant import (
    TenantCreate,
    TenantResponse,
    TenantDetailResponse,
    TenantMemberAdd,
    TenantMemberResponse,
)
from app.services.tenant_service import TenantService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/workspaces", tags=["Workspaces (Tenants)"])


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: TenantCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workspace/tenant. The creator becomes OWNER."""
    tenant = await TenantService.create_tenant(db, current_user, data)
    await AuditService.log_event(
        db=db,
        tenant_id=tenant.id,
        user_id=current_user.id,
        action="workspace.created",
        entity_type="tenant",
        entity_id=tenant.id,
        details=f"Workspace '{tenant.name}' created by {current_user.email}",
    )
    return tenant


@router.get("", response_model=List[TenantResponse])
async def list_my_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all workspaces the current user is a member of."""
    return await TenantService.get_user_tenants(db, current_user.id)


@router.get("/{tenant_id}", response_model=TenantDetailResponse)
async def get_workspace_details(
    tenant_id: str,
    membership: TenantMember = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a specific workspace, including its members."""
    return await TenantService.get_tenant_by_id(db, tenant_id)


@router.post(
    "/{tenant_id}/members",
    response_model=TenantMemberResponse,
    dependencies=[Depends(require_role(TenantRole.ADMIN))],
)
async def add_workspace_member(
    tenant_id: str,
    data: TenantMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add or update a workspace member (Requires ADMIN or OWNER role)."""
    membership = await TenantService.add_or_update_member(
        db=db,
        tenant_id=tenant_id,
        email=data.email,
        role=data.role,
    )
    await AuditService.log_event(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="member.added",
        entity_type="tenant_member",
        entity_id=membership.id,
        details=f"Added/updated member {data.email} with role {data.role.value}",
    )
    return membership


@router.delete(
    "/{tenant_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(TenantRole.ADMIN))],
)
async def remove_workspace_member(
    tenant_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the workspace (Requires ADMIN or OWNER role)."""
    await TenantService.remove_member(db, tenant_id, user_id)
    await AuditService.log_event(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="member.removed",
        entity_type="tenant_member",
        entity_id=user_id,
        details=f"Removed user {user_id} from workspace",
    )
