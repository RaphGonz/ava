import copy
import json
import logging
import uuid
from pathlib import Path

from app.core.config import settings
from app.image.comfyui import comfyui_client
from app.models.user import User

logger = logging.getLogger(__name__)

_WORKFLOWS_DIR = Path(__file__).parent / "workflows"


class ImageGenerator:
    def __init__(self):
        self._template_cache: dict[str, dict] = {}

    def _load_template(self, template_name: str) -> dict:
        if template_name not in self._template_cache:
            path = _WORKFLOWS_DIR / template_name
            self._template_cache[template_name] = json.loads(
                path.read_text(encoding="utf-8")
            )
            logger.info("Loaded workflow template: %s", template_name)
        return self._template_cache[template_name]

    def _apply_replacements(self, obj: object, replacements: dict) -> object:
        """Recursively walk dict/list and replace {{TOKEN}} strings.

        Handles both exact matches (entire value is a token) and substring
        replacements (token appears within a longer string).
        """
        if isinstance(obj, dict):
            return {k: self._apply_replacements(v, replacements) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._apply_replacements(item, replacements) for item in obj]
        elif isinstance(obj, str):
            # Exact match — allows replacing with non-string types (int, float)
            if obj in replacements:
                return replacements[obj]
            # Substring replacements — only for tokens embedded in longer strings
            result = obj
            for token, value in replacements.items():
                if token in result:
                    result = result.replace(token, str(value))
            return result
        return obj

    def build_workflow(
        self,
        prompt: str,
        reference_image_url: str | None = None,
        width: int | None = None,
        height: int | None = None,
        workflow_template: str | None = None,
        extra_replacements: dict | None = None,
    ) -> dict:
        """Build a ComfyUI workflow from a template, filling in dynamic values."""
        template_name = workflow_template or settings.comfyui_workflow_template
        template = copy.deepcopy(self._load_template(template_name))

        replacements = {
            "{{POSITIVE_PROMPT}}": prompt,
            "{{NEGATIVE_PROMPT}}": settings.image_negative_prompt,
            "{{SEED}}": hash(uuid.uuid4()) % (2**32),
            "{{STEPS}}": settings.image_sampler_steps,
            "{{CFG}}": settings.image_cfg_scale,
            "{{SAMPLER}}": settings.image_sampler_name,
            "{{SCHEDULER}}": settings.image_scheduler,
            "{{CHECKPOINT}}": settings.image_checkpoint_name,
            "{{WIDTH}}": width or settings.image_default_width,
            "{{HEIGHT}}": height or settings.image_default_height,
            "{{FILENAME_PREFIX}}": settings.image_filename_prefix,
            "{{REFERENCE_IMAGE_PATH}}": reference_image_url or "",
        }
        if extra_replacements:
            replacements.update(extra_replacements)

        workflow = self._apply_replacements(template, replacements)

        # Remove the _comment key if present
        if isinstance(workflow, dict):
            workflow.pop("_comment", None)

        return workflow

    async def generate(
        self,
        prompt: str,
        user: User,
        style: str = "photographic",
        workflow_template: str | None = None,
        extra_replacements: dict | None = None,
    ) -> list[dict]:
        """Generate images for a user using the workflow template.

        Returns list of {"bytes": bytes, "filename": str} dicts.
        """
        # Use ComfyUI Cloud filename for the LoadImage node (not local URL)
        reference_image_url = None
        if user.avatar_config:
            reference_image_url = user.avatar_config.get("comfyui_reference_filename")

        logger.info(
            "[user:%s] generating image (ref=%s, template=%s, prompt=%.80s...)",
            str(user.id)[:8],
            reference_image_url or "none",
            workflow_template or settings.comfyui_workflow_template,
            prompt,
        )

        workflow = self.build_workflow(
            prompt=prompt,
            reference_image_url=reference_image_url,
            workflow_template=workflow_template,
            extra_replacements=extra_replacements,
        )
        return await comfyui_client.generate_and_download(workflow)


image_generator = ImageGenerator()
