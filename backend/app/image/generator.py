import uuid

from app.image.comfyui import comfyui_client
from app.models.user import User


class ImageGenerator:
    def build_workflow(
        self,
        prompt: str,
        reference_images: dict | None = None,
        style: str = "photographic",
        width: int = 768,
        height: int = 1024,
    ) -> dict:
        """Build a ComfyUI workflow JSON.

        This is a PLACEHOLDER structure. The actual workflow will be designed
        in ComfyUI's visual editor and exported as JSON. This method fills in
        the dynamic values (prompt, seed, dimensions, reference image paths).

        For reference-image-based character consistency, nodes like
        IPAdapter or InstantID will be added to the workflow template.
        """
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": hash(uuid.uuid4()) % (2**32),
                    "steps": 25,
                    "cfg": 7.0,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors",
                },
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "ugly, blurry, deformed, low quality",
                    "clip": ["4", 1],
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "ava_gen", "images": ["8", 0]},
            },
        }

        # TODO: When reference_images are provided, inject IPAdapter/InstantID
        # nodes into the workflow for character consistency.
        # The workflow template will be loaded from a JSON file exported
        # from ComfyUI's visual editor.

        return workflow

    async def generate(
        self,
        prompt: str,
        user: User,
        style: str = "photographic",
    ) -> list[bytes]:
        """Generate images for a user, incorporating their reference images."""
        reference_images = None
        if user.avatar_config and "reference_images" in user.avatar_config:
            reference_images = user.avatar_config["reference_images"]

        workflow = self.build_workflow(
            prompt=prompt,
            reference_images=reference_images,
            style=style,
        )
        return await comfyui_client.generate_and_download(workflow)


image_generator = ImageGenerator()
