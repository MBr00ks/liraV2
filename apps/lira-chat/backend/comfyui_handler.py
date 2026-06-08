import asyncio
import json
import logging
import random
import uuid
from pathlib import Path

import httpx

logger = logging.getLogger("comfyui")

COMFYUI_PLACEHOLDERS = {
    "%seed%": lambda: str(random.randint(0, 2 ** 32 - 1)),
    "%steps%": lambda: "20",
    "%width%": lambda: "896",
    "%height%": lambda: "896",
    "%scale%": lambda: "5",
    "%sampler%": lambda: "dpmpp_2m",
    "%scheduler%": lambda: "karras",
    "%denoise%": lambda: "1",
    "%model%": lambda: "unrealvisionXLPhotoreal_realismUniversal.safetensors",
    "%negative_prompt%": lambda: "worst quality, low quality, bad anatomy, deformed, blurry, watermark, text, signature, extra limbs, ugly, poorly drawn, asian, monolids, flat nose",
}

DEFAULT_NEGATIVE = "worst quality, low quality, bad anatomy, deformed, blurry, watermark, text, signature, extra limbs, ugly, poorly drawn"


class ComfyUIGenerator:
    def __init__(self, base_url: str, workflow_path: str, output_dir: str):
        self.base_url = base_url.rstrip("/")
        self.workflow_path = workflow_path
        self.output_dir = Path(output_dir)

    def _substitute(self, template: str, prompt: str, seed: int | None = None) -> str:
        if seed is None:
            seed = random.randint(0, 2 ** 32 - 1)

        s = template.replace("%prompt%", prompt)
        s = s.replace("%seed%", str(seed))

        for key, fn in COMFYUI_PLACEHOLDERS.items():
            if key != "%seed%":
                s = s.replace(key, fn())

        return s

    async def generate(
        self, prompt: str, seed: int | None = None
    ) -> tuple[bytes, str]:
        raw = Path(self.workflow_path).read_text(encoding="utf-8")
        substituted = self._substitute(raw, prompt, seed)
        workflow = json.loads(substituted)

        async with httpx.AsyncClient(timeout=30) as client:
            # Clear any stale queue entries first
            try:
                await client.post(f"{self.base_url}/interrupt")
                await client.post(
                    f"{self.base_url}/queue",
                    json={"clear": True},
                )
            except Exception:
                pass

            logger.info("submitting prompt to ComfyUI")
            resp = await client.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow, "client_id": "lira-chat"},
            )
            if resp.is_error:
                raise RuntimeError(
                    f"ComfyUI prompt error: {resp.status_code} {resp.text[:500]}"
                )
            data = resp.json()
            prompt_id = data.get("prompt_id", "")
            if not prompt_id:
                raise RuntimeError("ComfyUI did not return a prompt_id")
            logger.info(f"prompt queued: {prompt_id}")

        deadline = asyncio.get_event_loop().time() + 300
        poll_count = 0
        async with httpx.AsyncClient(timeout=10) as client:
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    raise TimeoutError(
                        "ComfyUI generation timed out after 300s"
                    )

                await asyncio.sleep(2)
                poll_count += 1

                hist_resp = await client.get(
                    f"{self.base_url}/history/{prompt_id}"
                )
                if hist_resp.is_error:
                    logger.warning(f"history poll error: {hist_resp.status_code}")
                    continue

                history = hist_resp.json()
                node_history = history.get(prompt_id)

                if node_history is None:
                    logger.debug(f"poll {poll_count}: not yet in history")
                    continue

                logger.info(f"found in history after {poll_count} polls")

                status = node_history.get("status", {})
                if status.get("completed", False):
                    logger.info("prompt completed")
                    break
                if status.get("error"):
                    raise RuntimeError(
                        f"ComfyUI prompt failed: {status['error']}"
                    )

                logger.debug("prompt still running, waiting...")

        outputs = node_history.get("outputs", {})
        logger.info(f"output nodes: {list(outputs.keys())}")
        for node_id, node_output in outputs.items():
            images = node_output.get("images", [])
            if images:
                filename = images[0].get("filename", "")
                filepath = self.output_dir / filename
                logger.info(f"found image: {filename}")
                if filepath.exists():
                    return filepath.read_bytes(), filename
                logger.warning(f"image file not found at {filepath}")

        raise RuntimeError(
            f"Image not found in ComfyUI output (prompt_id={prompt_id})"
        )
