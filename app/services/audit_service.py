from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.audit_log import AuditLog
from app.core.logging import logger


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        tenant_id: str,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(audit)
        logger.info(f"Audit: [{action}] by user {user_id} on tenant {tenant_id}")
        return audit

    @staticmethod
    async def get_tenant_audit_logs(
        db: AsyncSession,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AuditLog]:
        query = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .options(selectinload(AuditLog.user))
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await db.execute(query)
        return list(res.scalars().all())
