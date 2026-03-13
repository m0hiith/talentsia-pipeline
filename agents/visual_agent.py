"""
AGENT-04 — Visual Agent
Converts scripts into visual prompts, generates images via FLUX.1 Schnell (ComfyUI)
and B-roll video clips via CogVideoX-5B or Wan2.1.

Models:
  - FLUX.1 Schnell (black-forest-labs) — 4x faster, Apache 2.0
  - CogVideoX-5B (THUDM) — text-to-video, 6s clips
  - Wan2.1 (wan-ai) — cinematic B-roll, high motion quality

All models run as separate services, called via REST API.
"""

import os
import uuid
from pathlib import Path

import httpx

from agents.base_agent import BaseAgent
from db.database import get_db
from prompts.visual_prompts import script_to_visual_prompts

COMFYUI_URL = os.getenv("COMFYUI_API_URL", "http://localhost:8188")
COGVIDEO_URL = os.getenv("COGVIDEO_API_URL", "http://localhost:8100")
WAN21_URL = os.getenv("WAN21_API_URL", "http://localhost:8200")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))

# Preferred video model (cogvideox or wan21)
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "cogvideox")


class VisualAgent(BaseAgent):
    name = "visual"
    description = "Script → FLUX.1 images + CogVideoX/Wan2.1 B-roll clips."

    async def execute(self, script_id: str = None, **kwargs) -> dict:
        # Get draft scripts that need visuals
        with get_db() as conn:
            if script_id:
                rows = conn.execute(
                    """SELECT s.*, st.title as story_title FROM scripts s
                       JOIN stories st ON s.story_id = st.id
                       WHERE s.id = ?""",
                    (script_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT s.*, st.title as story_title FROM scripts s
                       JOIN stories st ON s.story_id = st.id
                       WHERE s.status = 'draft'
                       ORDER BY s.created_at DESC LIMIT 3"""
                ).fetchall()

        scripts = [dict(r) for r in rows]
        if not scripts:
            return {"generated": 0, "message": "No scripts need visuals"}

        results = []
        for script in scripts:
            # Generate visual prompts from script
            prompts = script_to_visual_prompts(script["full_text"], script["story_title"])

            media_items = []

            # ── Generate thumbnail via FLUX.1 Schnell ──────
            thumb_path = await self._generate_flux_image(
                prompts["thumbnail"],
                script["id"],
                "thumbnail",
            )
            if thumb_path:
                media_items.append({
                    "type": "thumbnail",
                    "path": thumb_path,
                    "prompt": prompts["thumbnail"],
                })

            # ── Generate key frame images ──────────
            for i, img_prompt in enumerate(prompts.get("images", [])):
                img_path = await self._generate_flux_image(
                    img_prompt,
                    script["id"],
                    f"image_{i}",
                )
                if img_path:
                    media_items.append({
                        "type": "image",
                        "path": img_path,
                        "prompt": img_prompt,
                    })

            # ── Generate B-roll video clips ────────
            for i, vid_prompt in enumerate(prompts.get("broll", [])):
                if VIDEO_MODEL == "wan21":
                    vid_path = await self._generate_wan21_video(
                        vid_prompt, script["id"], f"broll_{i}"
                    )
                else:
                    vid_path = await self._generate_cogvideo(
                        vid_prompt, script["id"], f"broll_{i}"
                    )
                if vid_path:
                    media_items.append({
                        "type": "broll",
                        "path": vid_path,
                        "prompt": vid_prompt,
                    })

            # Store media records in DB
            with get_db() as conn:
                for item in media_items:
                    model_name = "flux.1-schnell"
                    if item["type"] == "broll":
                        model_name = "wan2.1" if VIDEO_MODEL == "wan21" else "cogvideox-5b"
                    conn.execute(
                        """INSERT INTO media (id, script_id, media_type, file_path, prompt_used, model_used)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            str(uuid.uuid4()),
                            script["id"],
                            item["type"],
                            item["path"],
                            item["prompt"],
                            model_name,
                        ),
                    )

            results.append({
                "script_id": script["id"],
                "story": script["story_title"][:50],
                "media_count": len(media_items),
            })

        self.logger.info(f"🎨 Generated visuals for {len(results)} scripts")
        return {"generated": len(results), "details": results}

    async def _generate_flux_image(self, prompt: str, script_id: str, name: str) -> str | None:
        """Generate image via ComfyUI running FLUX.1 Schnell.

        FLUX.1 Schnell specs:
          - 4x faster than FLUX.1 (standard)
          - 128 params, Apache 2.0 license
          - Best for: thumbnails, key frames, scene images
          - VRAM: ~12GB (fp16) or ~6GB (fp8)
        """
        output_path = OUTPUT_DIR / "images" / script_id
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = str(output_path / f"{name}.png")

        try:
            # FLUX.1 Schnell workflow for ComfyUI
            workflow = {
                "prompt": {
                    "3": {
                        "class_type": "CLIPTextEncode",
                        "inputs": {
                            "text": prompt,
                            "clip": ["4", 0],
                        },
                    },
                    "4": {
                        "class_type": "CheckpointLoaderSimple",
                        "inputs": {
                            "ckpt_name": "flux1-schnell.safetensors",
                        },
                    },
                    "5": {
                        "class_type": "KSampler",
                        "inputs": {
                            "seed": hash(prompt) % (2**32),
                            "steps": 4,  # Schnell = fast (4 steps)
                            "cfg": 1.0,  # Schnell uses low CFG
                            "sampler_name": "euler",
                            "scheduler": "normal",
                            "denoise": 1.0,
                            "model": ["4", 0],
                            "positive": ["3", 0],
                            "negative": ["6", 0],
                            "latent_image": ["7", 0],
                        },
                    },
                    "6": {
                        "class_type": "CLIPTextEncode",
                        "inputs": {
                            "text": "",
                            "clip": ["4", 1],
                        },
                    },
                    "7": {
                        "class_type": "EmptyLatentImage",
                        "inputs": {
                            "width": 1024,
                            "height": 1024,
                            "batch_size": 1,
                        },
                    },
                    "8": {
                        "class_type": "VAEDecode",
                        "inputs": {
                            "samples": ["5", 0],
                            "vae": ["4", 2],
                        },
                    },
                    "9": {
                        "class_type": "SaveImage",
                        "inputs": {
                            "filename_prefix": f"{script_id}_{name}",
                            "images": ["8", 0],
                        },
                    },
                },
            }

            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{COMFYUI_URL}/prompt",
                    json=workflow,
                )
                if resp.status_code == 200:
                    self.logger.info(f"🖼️ FLUX.1 image queued: {name}")
                    return file_path

        except Exception as e:
            self.logger.warning(f"ComfyUI/FLUX.1 unavailable for {name}: {e}")
            # Create placeholder
            output_path.mkdir(parents=True, exist_ok=True)
            Path(file_path).write_text(f"PLACEHOLDER — FLUX.1 Schnell prompt: {prompt[:200]}")
            return file_path

        return None

    async def _generate_cogvideo(self, prompt: str, script_id: str, name: str) -> str | None:
        """Generate B-roll video via CogVideoX-5B API.

        CogVideoX-5B specs:
          - 5B params, text-to-video
          - Supports text→video and image→video
          - ~6 second clips, 480p
          - VRAM: ~24GB (fp16) or ~16GB (int8)
          - Apache 2.0 license
        """
        output_path = OUTPUT_DIR / "videos" / script_id
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = str(output_path / f"{name}.mp4")

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{COGVIDEO_URL}/generate",
                    json={
                        "prompt": prompt,
                        "num_frames": 49,  # ~6 seconds at 8fps
                        "guidance_scale": 6.0,
                        "num_inference_steps": 50,
                        "width": 720,
                        "height": 480,
                    },
                )
                if resp.status_code == 200:
                    # Save video bytes
                    video_data = resp.content
                    Path(file_path).write_bytes(video_data)
                    self.logger.info(f"🎬 CogVideoX clip generated: {name}")
                    return file_path

        except Exception as e:
            self.logger.warning(f"CogVideoX unavailable for {name}: {e}")
            Path(file_path).write_text(f"PLACEHOLDER — CogVideoX-5B prompt: {prompt[:200]}")
            return file_path

        return None

    async def _generate_wan21_video(self, prompt: str, script_id: str, name: str) -> str | None:
        """Generate B-roll video via Wan2.1 API.

        Wan2.1 specs:
          - Alibaba's latest (14B version)
          - Extremely high-quality motion
          - Best for cinematic B-roll
          - VRAM: ~24GB (fp16), longer generation time
          - Apache 2.0 license
        """
        output_path = OUTPUT_DIR / "videos" / script_id
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = str(output_path / f"{name}.mp4")

        try:
            async with httpx.AsyncClient(timeout=600) as client:
                resp = await client.post(
                    f"{WAN21_URL}/generate",
                    json={
                        "prompt": prompt,
                        "negative_prompt": "blurry, low quality, watermark, text overlay",
                        "num_frames": 81,  # ~5 seconds at 16fps
                        "guidance_scale": 5.0,
                        "num_inference_steps": 50,
                        "width": 832,
                        "height": 480,
                        "fps": 16,
                    },
                )
                if resp.status_code == 200:
                    video_data = resp.content
                    Path(file_path).write_bytes(video_data)
                    self.logger.info(f"🎬 Wan2.1 clip generated: {name}")
                    return file_path

        except Exception as e:
            self.logger.warning(f"Wan2.1 unavailable for {name}: {e}")
            Path(file_path).write_text(f"PLACEHOLDER — Wan2.1 prompt: {prompt[:200]}")
            return file_path

        return None


visual = VisualAgent()
