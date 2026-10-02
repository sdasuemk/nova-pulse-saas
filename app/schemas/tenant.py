from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.membership import TenantRole
from app.schemas.user import UserResponse


class TenantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    plan: str = "free"


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    plan: Optional[str] = None
    is_active: Optional[bool] = None


class TenantMemberAdd(BaseModel):
    email: str
    role: TenantRole = TenantRole.MEMBER


class TenantMemberUpdate(BaseModel):
    role: TenantRole


class TenantMemberResponse(BaseModel):
    id: str
    user_id: str
    tenant_id: str
    role: TenantRole
    created_at: datetime
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TenantResponse(TenantBase):
    id: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantDetailResponse(TenantResponse):
    members: List[TenantMemberResponse] = []
