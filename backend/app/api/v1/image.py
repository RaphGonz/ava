import base64

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.image.generator import image_generator
from app.models.user import User
from app.orchestrator.guardian import Guardian

router = APIRouter(prefix="/image", tags=["image"])
guardian = Guardian()


class ImageRequest(BaseModel):
    prompt: str
    style: str = "photographic"


class ImageResponse(BaseModel):
    images: list[str]  # base64-encoded


@router.post("/generate", response_model=ImageResponse)
async def generate_image(
    body: ImageRequest,
    user: User = Depends(get_current_user),
):
    # Pre-filter the prompt
    filter_result = await guardian.pre_filter(body.prompt)
    if filter_result.blocked:
        raise HTTPException(status_code=400, detail=filter_result.reason or "Blocked")

    try:
        image_bytes_list = await image_generator.generate(
            prompt=body.prompt,
            user=user,
            style=body.style,
        )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Image generation timed out")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ComfyUI unavailable: {e}")

    encoded = [base64.b64encode(img).decode("utf-8") for img in image_bytes_list]
    return ImageResponse(images=encoded)
