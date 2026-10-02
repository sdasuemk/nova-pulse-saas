import re
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException, AppException
from app.models.tenant import Tenant
from app.models.membership import TenantMember, TenantRole
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    @staticmethod
    def _slugify(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        return re.sub(r"[-\s]+", "-", text)

    @classmethod
    async def create_tenant(cls, db: AsyncSession, user: User, data: TenantCreate) -> Tenant:
        base_slug = data.slug or cls._slugify(data.name)
        slug = f"{base_slug}-{user.id[:6]}"

        # Check slug conflict
        exists = await db.execute(select(Tenant).where(Tenant.slug == slug))
        if exists.scalar_one_or_none():
            slug = f"{slug}-{int(user.created_at.timestamp())}"

        tenant = Tenant(
            name=data.name,
            slug=slug,
            plan=data.plan,
            is_active=True,
        )
        db.add(tenant)
        await db.flush()

        # Add current user as OWNER
        member = TenantMember(
            user_id=user.id,
            tenant_id=tenant.id,
            role=TenantRole.OWNER,
        )
        db.add(member)
        await db.flush()

        return tenant

    @classmethod
    async def get_user_tenants(cls, db: AsyncSession, user_id: str) -> List[Tenant]:
        query = (
            select(Tenant)
            .join(TenantMember, TenantMember.tenant_id == Tenant.id)
            .where(TenantMember.user_id == user_id, Tenant.is_active == True)
            .order_by(Tenant.name)
        )
        res = await db.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def get_tenant_by_id(cls, db: AsyncSession, tenant_id: str) -> Tenant:
        query = (
            select(Tenant)
            .options(
                selectinload(Tenant.memberships).selectinload(TenantMember.user)
            )
            .where(Tenant.id == tenant_id)
        )
        res = await db.execute(query)
        tenant = res.scalar_one_or_none()
        if not tenant:
            raise NotFoundException("Tenant", tenant_id)
        return tenant

    @classmethod
    async def add_or_update_member(
        cls, db: AsyncSession, tenant_id: str, email: str, role: TenantRole
    ) -> TenantMember:
        # Find user by email
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalar_one_or_none()
        if not user:
            raise NotFoundException("User with email", email)

        # Check existing membership
        query = select(TenantMember).where(
            TenantMember.tenant_id == tenant_id,
            TenantMember.user_id == user.id,
        )
        res = await db.execute(query)
        membership = res.scalar_one_or_none()

        if membership:
            membership.role = role
        else:
            membership = TenantMember(
                tenant_id=tenant_id,
                user_id=user.id,
                role=role,
            )
            db.add(membership)

        await db.flush()
        # Eager load user relationship for response
        await db.refresh(membership, ["user"])
        return membership

    @classmethod
    async def remove_member(cls, db: AsyncSession, tenant_id: str, user_id: str) -> None:
        query = select(TenantMember).where(
            TenantMember.tenant_id == tenant_id,
            TenantMember.user_id == user_id,
        )
        res = await db.execute(query)
        membership = res.scalar_one_or_none()

        if not membership:
            raise NotFoundException("TenantMember", user_id)

        # Guard: Cannot remove last owner
        if membership.role == TenantRole.OWNER:
            owners_query = select(TenantMember).where(
                TenantMember.tenant_id == tenant_id,
                TenantMember.role == TenantRole.OWNER,
            )
            owners = (await db.execute(owners_query)).scalars().all()
            if len(owners) <= 1:
                raise ForbiddenException("Cannot remove the only owner of this workspace.")

        await db.delete(membership)
