import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.db.postgres import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str | None
    current_mode: str
    is_age_verified: bool
    is_onboarded: bool
    safe_word: str | None
    exit_word: str | None
    avatar_config: dict | None

    model_config = {"from_attributes": True}


class SettingsRequest(BaseModel):
    username: str | None = None
    safe_word: str | None = None
    exit_word: str | None = None
    avatar_style: str | None = None
    character_description: str | None = None


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        username=body.username,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        current_mode=user.current_mode,
        is_age_verified=user.is_age_verified,
        is_onboarded=getattr(user, "is_onboarded", False),
        safe_word=user.safe_word,
        exit_word=user.exit_word,
        avatar_config=user.avatar_config,
    )


@router.put("/settings", response_model=UserResponse)
async def update_settings(
    body: SettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.username is not None:
        user.username = body.username.strip()
    if body.safe_word is not None:
        user.safe_word = body.safe_word.strip() if body.safe_word.strip() else None
    if body.exit_word is not None:
        user.exit_word = body.exit_word.strip() if body.exit_word.strip() else None

    # Update avatar_config fields (copy dict so SQLAlchemy detects the mutation)
    if body.avatar_style is not None or body.character_description is not None:
        avatar_config = dict(user.avatar_config or {})
        if body.avatar_style is not None:
            avatar_config["style"] = body.avatar_style
        if body.character_description is not None:
            avatar_config["character_description"] = body.character_description
        user.avatar_config = avatar_config
        flag_modified(user, "avatar_config")

    await db.commit()
    await db.refresh(user)

    logger.info("[user:%s] settings updated", str(user.id)[:8])

    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        current_mode=user.current_mode,
        is_age_verified=user.is_age_verified,
        is_onboarded=getattr(user, "is_onboarded", False),
        safe_word=user.safe_word,
        exit_word=user.exit_word,
        avatar_config=user.avatar_config,
    )
