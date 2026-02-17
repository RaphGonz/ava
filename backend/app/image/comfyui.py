import asyncio

import httpx

from app.core.config import settings


class ComfyUIClient:
    def __init__(self):
        self._base_url = settings.comfyui_url

    async def submit_workflow(self, workflow: dict) -> str:
        """Submit a workflow to ComfyUI. Returns prompt_id."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/prompt",
                json={"prompt": workflow},
                timeout=settings.comfyui_submit_timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data["prompt_id"]

    async def poll_result(self, prompt_id: str) -> dict:
        """Poll until the workflow completes. Returns the history entry."""
        deadline = asyncio.get_event_loop().time() + settings.comfyui_poll_timeout
        async with httpx.AsyncClient() as client:
            while asyncio.get_event_loop().time() < deadline:
                response = await client.get(
                    f"{self._base_url}/history/{prompt_id}",
                    timeout=settings.comfyui_request_timeout,
                )
                response.raise_for_status()
                history = response.json()
                if prompt_id in history:
                    return history[prompt_id]
                await asyncio.sleep(settings.comfyui_poll_interval)
        raise TimeoutError(
            f"ComfyUI workflow {prompt_id} did not complete in {settings.comfyui_poll_timeout}s"
        )

    async def download_image(self, filename: str, subfolder: str = "") -> bytes:
        """Download a generated image from ComfyUI."""
        async with httpx.AsyncClient() as client:
            params: dict[str, str] = {"filename": filename}
            if subfolder:
                params["subfolder"] = subfolder
            response = await client.get(
                f"{self._base_url}/view",
                params=params,
                timeout=settings.comfyui_download_timeout,
            )
            response.raise_for_status()
            return response.content

    async def generate_and_download(self, workflow: dict) -> list[bytes]:
        """Submit workflow, wait for completion, download all output images."""
        prompt_id = await self.submit_workflow(workflow)
        result = await self.poll_result(prompt_id)

        images = []
        outputs = result.get("outputs", {})
        for node_output in outputs.values():
            for image_info in node_output.get("images", []):
                image_bytes = await self.download_image(
                    filename=image_info["filename"],
                    subfolder=image_info.get("subfolder", ""),
                )
                images.append(image_bytes)
        return images


comfyui_client = ComfyUIClient()
