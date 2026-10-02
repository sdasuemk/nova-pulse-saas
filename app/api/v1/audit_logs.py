from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import (
    get_current_membership,
    require_role,
)
from app.models.membership import TenantMember, TenantRole
from app.schemas.audit_log import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "",
    response_model=List[AuditLogResponse],
    dependencies=[Depends(require_role(TenantRole.ADMIN))],
)
async def list_workspace_audit_logs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    membership: TenantMember = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve security and activity audit logs for the workspace.
    (Requires ADMIN or OWNER role).
    """
    return await AuditService.get_tenant_audit_logs(
        db, tenant_id=membership.tenant_id, limit=limit, offset=offset
    )
