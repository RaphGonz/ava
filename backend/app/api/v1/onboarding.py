import base64
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.postgres import get_db
from app.image.generator import image_generator
from app.models.user import User
from app.orchestrator.guardian import Guardian

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])
guardian = Guardian()

_AVATARS_DIR = Path(__file__).parent.parent.parent.parent / "uploads" / "avatars"
_AVATARS_DIR.mkdir(parents=True, exist_ok=True)


class OnboardingRequest(BaseModel):
    username: str
    is_age_verified: bool
    safe_word: str | None = None
    preferences: dict | None = None


class AvatarGenerateRequest(BaseModel):
    gender: str       # "woman" | "man"
    nation: str       # free text, e.g. "African American", "Japanese"
    description: str  # freeform appearance details


class AvatarValidateRequest(BaseModel):
    comfyui_filename: str  # ComfyUI Cloud filename from generate-avatar


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

    avatar_config = dict(user.avatar_config or {})
    if body.preferences:
        avatar_config["preferences"] = body.preferences
    user.avatar_config = avatar_config
    flag_modified(user, "avatar_config")

    user.is_onboarded = True
    await db.commit()

    return {
        "status": "ok",
        "message": "Onboarding complete",
        "username": user.username,
        "is_age_verified": user.is_age_verified,
    }


@router.post("/generate-avatar")
async def generate_avatar(
    body: AvatarGenerateRequest,
    user: User = Depends(get_current_user),
):
    # Content filter on the description
    filter_result = await guardian.pre_filter(body.description)
    if filter_result.blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=filter_result.reason or "Content blocked by filter",
        )

    user_id_short = str(user.id)[:8]
    logger.info(
        "[user:%s] generating avatar: gender=%s, nation=%s, desc=%.80s...",
        user_id_short, body.gender, body.nation, body.description,
    )

    # The T2I workflow template has {{NATION}}, {{GENDER}}, {{DESCRIPTION}}
    # embedded in the prompt node — pass them as extra replacements.
    extra = {
        "{{NATION}}": body.nation,
        "{{GENDER}}": body.gender,
        "{{DESCRIPTION}}": body.description,
    }

    try:
        results = await image_generator.generate(
            prompt="",  # prompt is baked into the T2I workflow template
            user=user,
            workflow_template=settings.comfyui_t2i_workflow_template,
            extra_replacements=extra,
        )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Avatar generation timed out")
    except Exception as e:
        logger.error("[user:%s] avatar generation failed: %s", user_id_short, e)
        raise HTTPException(status_code=502, detail=f"Image generation failed: {e}")

    if not results:
        raise HTTPException(status_code=502, detail="No image returned from generator")

    # Save first image to disk (overwrite on regenerate)
    first = results[0]
    filename = f"{user.id}.png"
    filepath = _AVATARS_DIR / filename
    filepath.write_bytes(first["bytes"])
    avatar_url = f"/uploads/avatars/{filename}"
    comfyui_filename = first["filename"]
    logger.info("[user:%s] avatar saved: %s (comfyui: %s)", user_id_short, avatar_url, comfyui_filename)

    return {"avatar_url": avatar_url, "comfyui_filename": comfyui_filename}


@router.post("/validate-avatar")
async def validate_avatar(
    body: AvatarValidateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = f"{user.id}.png"
    filepath = _AVATARS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="No avatar generated yet")

    avatar_url = f"/uploads/avatars/{filename}"

    avatar_config = dict(user.avatar_config or {})
    avatar_config["reference_images"] = [avatar_url]
    avatar_config["comfyui_reference_filename"] = body.comfyui_filename
    user.avatar_config = avatar_config
    flag_modified(user, "avatar_config")
    await db.commit()

    logger.info(
        "[user:%s] avatar validated: %s (comfyui: %s)",
        str(user.id)[:8], avatar_url, body.comfyui_filename,
    )
    return {"status": "ok", "avatar_url": avatar_url}


@router.get("/status")
async def onboarding_status(user: User = Depends(get_current_user)):
    return {
        "is_onboarded": user.is_onboarded,
        "username": user.username,
        "is_age_verified": user.is_age_verified,
    }
