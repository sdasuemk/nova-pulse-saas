import re
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.exceptions import ConflictException, UnauthorizedException, NotFoundException
from app.models.user import User
from app.models.tenant import Tenant
from app.models.membership import TenantMember, TenantRole
from app.models.audit_log import AuditLog
from app.schemas.auth import RegisterRequest, Token


class AuthService:
    @staticmethod
    def _slugify(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        return re.sub(r"[-\s]+", "-", text)

    @classmethod
    async def register(cls, db: AsyncSession, data: RegisterRequest) -> tuple[User, Token]:
        # Check if email is already taken
        query = select(User).where(User.email == data.email)
        res = await db.execute(query)
        if res.scalar_one_or_none():
            raise ConflictException(f"User with email '{data.email}' already exists.")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.flush()  # Populates user.id

        # If user provided a workspace_name, or default workspace
        ws_name = data.workspace_name or f"{data.full_name}'s Workspace"
        base_slug = cls._slugify(ws_name)
        slug = f"{base_slug}-{user.id[:6]}"

        tenant = Tenant(
            name=ws_name,
            slug=slug,
            is_active=True,
            plan="free",
        )
        db.add(tenant)
        await db.flush()

        # Add user as OWNER of this tenant
        membership = TenantMember(
            user_id=user.id,
            tenant_id=tenant.id,
            role=TenantRole.OWNER,
        )
        db.add(membership)

        # Log workspace creation audit event
        audit = AuditLog(
            tenant_id=tenant.id,
            user_id=user.id,
            action="workspace.created",
            entity_type="tenant",
            entity_id=tenant.id,
            details=f"Workspace '{tenant.name}' initialized upon user registration",
        )
        db.add(audit)
        await db.flush()

        tokens = Token(
            access_token=create_access_token(user.id, extra_claims={"tenant_id": tenant.id}),
            refresh_token=create_refresh_token(user.id),
        )

        return user, tokens

    @classmethod
    async def authenticate(cls, db: AsyncSession, email: str, password: str) -> User:
        query = select(User).where(User.email == email)
        res = await db.execute(query)
        user = res.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedException("Your account has been deactivated.")

        return user

    @classmethod
    async def refresh_tokens(cls, db: AsyncSession, refresh_token: str) -> Token:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise UnauthorizedException("Invalid or expired refresh token.")

        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type. Expected refresh token.")

        user_id = payload.get("sub")
        query = select(User).where(User.id == user_id)
        res = await db.execute(query)
        user = res.scalar_one_or_none()

        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive.")

        return Token(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )
