import asyncio
import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """HTTP client for ComfyUI Cloud API (https://cloud.comfy.org)."""

    def __init__(self):
        self._base_url = settings.comfyui_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": settings.comfyui_api_key}

    async def submit_workflow(self, workflow: dict) -> str:
        """Submit a workflow to ComfyUI Cloud. Returns prompt_id."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/api/prompt",
                json={"prompt": workflow},
                headers=self._headers(),
                timeout=settings.comfyui_submit_timeout,
            )
            response.raise_for_status()
            data = response.json()
            prompt_id = data["prompt_id"]
            logger.info("Workflow submitted: prompt_id=%s", prompt_id)
            return prompt_id

    async def poll_result(self, prompt_id: str) -> dict:
        """Poll until the workflow completes. Returns the history entry."""
        deadline = asyncio.get_event_loop().time() + settings.comfyui_poll_timeout
        poll_count = 0
        async with httpx.AsyncClient() as client:
            while asyncio.get_event_loop().time() < deadline:
                response = await client.get(
                    f"{self._base_url}/api/job/{prompt_id}/status",
                    headers=self._headers(),
                    timeout=settings.comfyui_request_timeout,
                )
                response.raise_for_status()
                data = response.json()
                job_status = data.get("status", "")

                logger.info("Job %s status: %s (poll #%d)", prompt_id, job_status, poll_count)

                if job_status in ("completed", "success", "complete"):
                    logger.info("Job %s completed via status", prompt_id)
                    return await self._fetch_history(prompt_id)
                elif job_status in ("failed", "error", "cancelled"):
                    raise RuntimeError(
                        f"ComfyUI Cloud job {prompt_id} {job_status}: {data}"
                    )

                # Fallback: if status stays "executing" for a while,
                # try fetching history directly — the job may have finished
                # but the status endpoint is stale.
                poll_count += 1
                if poll_count >= 10 and poll_count % 5 == 0 and job_status == "executing":
                    try:
                        history = await self._fetch_history(prompt_id)
                        outputs = history.get("outputs", {})
                        if not outputs and isinstance(history, dict):
                            for _k, entry in history.items():
                                if isinstance(entry, dict) and "outputs" in entry:
                                    outputs = entry["outputs"]
                                    break
                        if outputs:
                            logger.info(
                                "Job %s completed (detected via history fallback)", prompt_id
                            )
                            return history
                    except httpx.HTTPStatusError:
                        logger.debug("Job %s history not ready yet", prompt_id)

                await asyncio.sleep(settings.comfyui_poll_interval)

        raise TimeoutError(
            f"ComfyUI Cloud job {prompt_id} did not complete in {settings.comfyui_poll_timeout}s"
        )

    async def _fetch_history(self, prompt_id: str) -> dict:
        """Fetch the full history entry for a completed job."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._base_url}/api/history_v2/{prompt_id}",
                headers=self._headers(),
                timeout=settings.comfyui_request_timeout,
            )
            response.raise_for_status()
            data = response.json()
            logger.info("History response keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))
            logger.info("History response (truncated): %.2000s", json.dumps(data, default=str))
            return data

    async def download_image(self, filename: str, subfolder: str = "") -> bytes:
        """Download a generated image from ComfyUI Cloud."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            params: dict[str, str] = {"filename": filename, "type": "output"}
            if subfolder:
                params["subfolder"] = subfolder
            response = await client.get(
                f"{self._base_url}/api/view",
                params=params,
                headers=self._headers(),
                timeout=settings.comfyui_download_timeout,
            )
            response.raise_for_status()
            return response.content

    async def generate_and_download(self, workflow: dict) -> list[dict]:
        """Submit workflow, wait for completion, download all output images.

        Returns list of {"bytes": bytes, "filename": str} dicts.
        """
        prompt_id = await self.submit_workflow(workflow)
        result = await self.poll_result(prompt_id)

        images: list[dict] = []
        # history_v2 wraps the result under a prompt_id key:
        # {"<prompt_id>": {"outputs": {"<node_id>": {"images": [...]}}}}
        # Unwrap the first (only) entry to get the inner dict.
        outputs = result.get("outputs", {})
        if not outputs and isinstance(result, dict):
            for key, entry in result.items():
                if isinstance(entry, dict) and "outputs" in entry:
                    outputs = entry["outputs"]
                    break

        for node_id, node_output in outputs.items():
            for image_info in node_output.get("images", []):
                filename = image_info.get("filename", "")
                logger.info("Downloading image: %s", filename)
                image_bytes = await self.download_image(
                    filename=filename,
                    subfolder=image_info.get("subfolder", ""),
                )
                images.append({"bytes": image_bytes, "filename": filename})

        if not images:
            logger.warning("No images found in job outputs: %s", result)

        return images


comfyui_client = ComfyUIClient()
