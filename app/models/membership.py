from enum import Enum
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String, UniqueConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedBase

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.tenant import Tenant


class TenantRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

    @classmethod
    def role_hierarchy(cls) -> dict:
        """Numeric rank for permission comparison (higher = more privileges)."""
        return {
            cls.VIEWER: 1,
            cls.MEMBER: 2,
            cls.ADMIN: 3,
            cls.OWNER: 4,
        }

    def has_privilege_of(self, required_role: "TenantRole") -> bool:
        hierarchy = self.role_hierarchy()
        current_rank = hierarchy.get(self, 0)
        required_rank = hierarchy.get(required_role, 0)
        return current_rank >= required_rank


class TenantMember(TimestampedBase):
    __tablename__ = "tenant_members"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[TenantRole] = mapped_column(
        SAEnum(TenantRole, native_enum=False, length=20),
        default=TenantRole.MEMBER,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant_membership"),
    )
