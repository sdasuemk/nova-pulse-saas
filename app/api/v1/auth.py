from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, RefreshTokenRequest, Token
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.core.security import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.
    Automatically creates a default workspace and assigns the user as OWNER.
    """
    user, tokens = await AuthService.register(db, data)
    return {
        "success": True,
        "message": "User registered successfully",
        "data": {
            "user": UserResponse.model_validate(user),
            "tokens": tokens,
        },
    }


@router.post("/login", response_model=Token)
async def login_json(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Standard JSON login endpoint."""
    user = await AuthService.authenticate(db, data.email, data.password)
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login/oauth2", response_model=Token)
async def login_oauth2(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 compatible token login, for Swagger UI 'Authorize' button.
    (Username field accepts the user's email).
    """
    user = await AuthService.authenticate(db, form_data.username, form_data.password)
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a fresh token pair."""
    return await AuthService.refresh_tokens(db, data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Fetch profile of the currently logged-in user."""
    return current_user
