from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.models.user import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class OnboardingRequest(BaseModel):
    username: str
    is_age_verified: bool
    safe_word: str | None = None
    avatar_style: str = "photographic"
    character_description: str | None = None
    preferences: dict | None = None


@router.post("/complete")
async def complete_onboarding(
    body: OnboardingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.is_onboarded:
        raise HTTPException(status_code=400, detail="Already onboarded")

    user.username = body.username
    user.is_age_verified = body.is_age_verified

    if body.safe_word:
        user.safe_word = body.safe_word.strip()

    avatar_config = user.avatar_config or {}
    avatar_config["style"] = body.avatar_style
    if body.character_description:
        avatar_config["character_description"] = body.character_description
    if body.preferences:
        avatar_config["preferences"] = body.preferences
    user.avatar_config = avatar_config

    user.is_onboarded = True
    await db.commit()

    return {
        "status": "ok",
        "message": "Onboarding complete",
        "username": user.username,
        "is_age_verified": user.is_age_verified,
    }


@router.get("/status")
async def onboarding_status(user: User = Depends(get_current_user)):
    return {
        "is_onboarded": user.is_onboarded,
        "username": user.username,
        "is_age_verified": user.is_age_verified,
    }
