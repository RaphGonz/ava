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
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["prompt_id"]

    async def poll_result(self, prompt_id: str, timeout: float = 120.0) -> dict:
        """Poll until the workflow completes. Returns the history entry."""
        deadline = asyncio.get_event_loop().time() + timeout
        async with httpx.AsyncClient() as client:
            while asyncio.get_event_loop().time() < deadline:
                response = await client.get(
                    f"{self._base_url}/history/{prompt_id}",
                    timeout=10.0,
                )
                response.raise_for_status()
                history = response.json()
                if prompt_id in history:
                    return history[prompt_id]
                await asyncio.sleep(2.0)
        raise TimeoutError(
            f"ComfyUI workflow {prompt_id} did not complete in {timeout}s"
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
                timeout=30.0,
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
