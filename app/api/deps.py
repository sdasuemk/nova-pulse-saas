from typing import Optional, Callable
from fastapi import Depends, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException, ForbiddenException, NotFoundException
from app.models.user import User
from app.models.tenant import Tenant
from app.models.membership import TenantMember, TenantRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decodes the JWT access token and retrieves the current authenticated user.
    """
    try:
        payload = decode_token(token)
    except Exception:
        raise UnauthorizedException("Invalid or expired authentication token.")

    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type. Expected access token.")

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Token payload missing subject identifier.")

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User associated with token does not exist.")
    if not user.is_active:
        raise UnauthorizedException("User account is deactivated.")

    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Requires the current user to be a system superuser."""
    if not current_user.is_superuser:
        raise ForbiddenException("Superuser privileges required for this action.")
    return current_user


async def get_tenant_id_from_request(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> str:
    """
    Resolves the target tenant ID from 'X-Tenant-ID' header, route path params, or query params.
    """
    if x_tenant_id:
        return x_tenant_id

    # Check path parameters (e.g. /workspaces/{tenant_id})
    path_tid = request.path_params.get("tenant_id")
    if path_tid:
        return path_tid

    # Check query parameters (e.g. ?tenant_id=...)
    query_tid = request.query_params.get("tenant_id")
    if query_tid:
        return query_tid

    raise ForbiddenException("Missing tenant context. Provide 'X-Tenant-ID' header.")


async def get_current_membership(
    tenant_id: str = Depends(get_tenant_id_from_request),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TenantMember:
    """
    Enforces that the authenticated user is a verified member of the requested tenant.
    Returns the user's TenantMember record containing their assigned role.
    """
    query = select(TenantMember).where(
        TenantMember.tenant_id == tenant_id,
        TenantMember.user_id == current_user.id,
    )
    res = await db.execute(query)
    membership = res.scalar_one_or_none()

    if not membership:
        raise ForbiddenException("You are not a member of this workspace.")

    return membership


def require_role(min_role: TenantRole) -> Callable:
    """
    FastAPI Dependency Factory that enforces Role-Based Access Control (RBAC).
    Usage:
        @router.delete("/resource", dependencies=[Depends(require_role(TenantRole.ADMIN))])
    """
    async def role_checker(
        membership: TenantMember = Depends(get_current_membership),
    ) -> TenantMember:
        user_role = (
            TenantRole(membership.role)
            if isinstance(membership.role, str)
            else membership.role
        )
        if not user_role.has_privilege_of(min_role):
            raise ForbiddenException(
                f"Action requires minimum role '{min_role.value}', but your role is '{user_role.value}'."
            )
        return membership

    return role_checker
