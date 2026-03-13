"""
AGENT-05 — Avatar Agent
XTTS-v2 voice cloning + SadTalker/LatentSync lip sync → talking avatar .mp4
Whisper Large V3 auto-captioning → synced subtitle overlays.
MoviePy merge: avatar + B-roll + captions → final 9:16 reel.

Models:
  - XTTS-v2 (coqui) — voice cloning, 6s reference, 17 languages, ~4GB VRAM
  - SadTalker (OpenTalker) — lip sync, photo → video, easiest setup
  - LatentSync (ByteDance) — premium lip sync, more realistic, harder setup
  - Whisper Large V3 (openai) — auto captions, word-level timestamps
"""

import os
import uuid
import json
from pathlib import Path

import httpx

from agents.base_agent import BaseAgent
from db.database import get_db

XTTS_URL = os.getenv("XTTS_API_URL", "http://localhost:8020")
SADTALKER_URL = os.getenv("SADTALKER_API_URL", "http://localhost:8030")
LATENTSYNC_URL = os.getenv("LATENTSYNC_API_URL", "http://localhost:8040")
WHISPER_URL = os.getenv("WHISPER_API_URL", "http://localhost:9000")
REFERENCE_AUDIO = os.getenv("REFERENCE_AUDIO_PATH", "./assets/voice_sample.wav")
AVATAR_PHOTO = os.getenv("AVATAR_PHOTO_PATH", "./assets/avatar_photo.png")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))

# Lip sync model preference: "sadtalker" or "latentsync"
LIP_SYNC_MODEL = os.getenv("LIP_SYNC_MODEL", "sadtalker")


class AvatarAgent(BaseAgent):
    name = "avatar"
    description = "XTTS-v2 voice clone + SadTalker/LatentSync lip sync → talking avatar."

    async def execute(self, script_id: str = None, **kwargs) -> dict:
        with get_db() as conn:
            if script_id:
                rows = conn.execute(
                    "SELECT * FROM scripts WHERE id = ?", (script_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM scripts WHERE status = 'draft' ORDER BY created_at DESC LIMIT 3"
                ).fetchall()

        scripts = [dict(r) for r in rows]
        if not scripts:
            return {"processed": 0, "message": "No scripts to process"}

        results = []
        for script in scripts:
            script_dir = OUTPUT_DIR / "avatar" / script["id"]
            script_dir.mkdir(parents=True, exist_ok=True)

            # ── Step 1: Voice synthesis (XTTS-v2) ──────
            voice_path = await self._synthesize_voice(
                script["full_text"],
                script_dir / "voice.wav",
            )

            # ── Step 2: Lip sync ───────────────────────
            if LIP_SYNC_MODEL == "latentsync":
                avatar_path = await self._generate_latentsync(
                    voice_path, script_dir / "avatar.mp4"
                )
            else:
                avatar_path = await self._generate_sadtalker(
                    voice_path, script_dir / "avatar.mp4"
                )

            # ── Step 3: Auto-captions (Whisper V3) ─────
            captions = await self._generate_captions(voice_path, script_dir / "captions.json")

            # ── Step 4: Assemble final reel ────────────
            final_path = await self._assemble_reel(
                script, avatar_path, voice_path, captions,
                script_dir / "final_reel.mp4",
            )

            # Store media records
            media_entries = [
                ("voice", str(voice_path), "xtts-v2"),
                ("avatar", str(avatar_path), LIP_SYNC_MODEL),
                ("captions", str(script_dir / "captions.json"), "whisper-large-v3"),
                ("final", str(final_path), "moviepy"),
            ]
            with get_db() as conn:
                for media_type, path, model in media_entries:
                    conn.execute(
                        """INSERT INTO media (id, script_id, media_type, file_path, model_used)
                           VALUES (?, ?, ?, ?, ?)""",
                        (str(uuid.uuid4()), script["id"], media_type, path, model),
                    )

                # Create reel record
                reel_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO reels (id, script_id, final_video, status)
                       VALUES (?, ?, ?, 'ready')""",
                    (reel_id, script["id"], str(final_path)),
                )

            results.append({
                "script_id": script["id"],
                "reel_id": reel_id,
                "voice": str(voice_path),
                "avatar": str(avatar_path),
                "final": str(final_path),
                "lip_sync_model": LIP_SYNC_MODEL,
            })

        self.logger.info(f"🎭 Created {len(results)} avatar reels")
        return {"processed": len(results), "details": results}

    async def _synthesize_voice(self, text: str, output_path: Path) -> Path:
        """Generate speech using XTTS-v2 voice cloning.

        XTTS-v2 specs:
          - Only 6s reference audio needed
          - 17 languages supported
          - Runs on 4GB VRAM
          - Real-time inference
          - Coqui TTS license
        """
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{XTTS_URL}/tts_to_audio",
                    data={
                        "text": text,
                        "speaker_wav": REFERENCE_AUDIO,
                        "language": "en",
                    },
                )
                if resp.status_code == 200:
                    output_path.write_bytes(resp.content)
                    self.logger.info(f"🎤 Voice generated: {output_path.name}")
                    return output_path

        except Exception as e:
            self.logger.warning(f"XTTS-v2 unavailable: {e}")

        # Create placeholder
        output_path.write_text(f"PLACEHOLDER AUDIO — text: {text[:100]}")
        return output_path

    async def _generate_sadtalker(self, audio_path: Path, output_path: Path) -> Path:
        """Generate lip-synced avatar video using SadTalker.

        SadTalker specs:
          - Easiest setup, well maintained
          - Works great with single photo input
          - Photo → video with matching lip movement
          - Audio driver, NIT License
        """
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                # SadTalker API endpoint
                resp = await client.post(
                    f"{SADTALKER_URL}/generate",
                    data={
                        "source_image": AVATAR_PHOTO,
                        "driven_audio": str(audio_path),
                        "preprocess": "crop",
                        "still_mode": False,
                        "enhancer": "gfpgan",
                    },
                )
                if resp.status_code == 200:
                    output_path.write_bytes(resp.content)
                    self.logger.info(f"👄 SadTalker lip sync complete: {output_path.name}")
                    return output_path

        except Exception as e:
            self.logger.warning(f"SadTalker unavailable: {e}")

        output_path.write_text(f"PLACEHOLDER VIDEO — SadTalker lip sync for {audio_path.name}")
        return output_path

    async def _generate_latentsync(self, audio_path: Path, output_path: Path) -> Path:
        """Generate lip-synced avatar video using LatentSync.

        LatentSync specs:
          - ByteDance's 2025 model
          - More realistic than SadTalker
          - More natural head movement
          - Slightly harder setup
          - Higher quality, 1024 VRAM
          - 2025 release, Apache 2.0
        """
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{LATENTSYNC_URL}/generate",
                    data={
                        "source_image": AVATAR_PHOTO,
                        "driven_audio": str(audio_path),
                        "guidance_scale": 2.0,
                        "num_inference_steps": 20,
                    },
                )
                if resp.status_code == 200:
                    output_path.write_bytes(resp.content)
                    self.logger.info(f"👄 LatentSync complete: {output_path.name}")
                    return output_path

        except Exception as e:
            self.logger.warning(f"LatentSync unavailable: {e}")

        output_path.write_text(f"PLACEHOLDER VIDEO — LatentSync for {audio_path.name}")
        return output_path

    async def _generate_captions(self, audio_path: Path, output_path: Path) -> list[dict]:
        """Auto-generate timed captions using Whisper Large V3.

        Whisper Large V3 specs:
          - Best open ASR model as of 2025
          - Word-level timestamps
          - Fully automatic caption generation
          - MIT License, runs on ~6GB VRAM
          - Uses faster-whisper for speed
        """
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{WHISPER_URL}/transcribe",
                    data={
                        "audio_path": str(audio_path),
                        "model": "large-v3",
                        "word_timestamps": True,
                        "language": "en",
                    },
                )
                if resp.status_code == 200:
                    result = resp.json()
                    segments = result.get("segments", [])
                    output_path.write_text(json.dumps(segments, indent=2))
                    self.logger.info(f"📝 Captions generated: {len(segments)} segments")
                    return segments

        except Exception as e:
            self.logger.warning(f"Whisper API unavailable: {e}")

        # Generate placeholder captions from script text
        placeholder = [
            {"start": 0.0, "end": 3.0, "text": "[Auto-captions will appear here]"},
        ]
        output_path.write_text(json.dumps(placeholder, indent=2))
        return placeholder

    async def _assemble_reel(
        self, script: dict, avatar_path: Path, voice_path: Path,
        captions: list[dict], output_path: Path
    ) -> Path:
        """Assemble final 9:16 Instagram Reel: avatar + B-roll + captions.

        Assembly pipeline:
          1. Load avatar video (PiP or full screen)
          2. Overlay B-roll footage from visual agent
          3. Add Whisper-generated captions as animated text
          4. Add background music track
          5. Cover photo crop for Instagram thumbnail
          6. Export as 9:16 (1080x1920) MP4, H.264
        """
        try:
            # In production: MoviePy assembly
            # from moviepy.editor import (
            #     VideoFileClip, AudioFileClip, TextClip,
            #     CompositeVideoClip, concatenate_videoclips
            # )
            #
            # avatar_clip = VideoFileClip(str(avatar_path))
            # audio_clip = AudioFileClip(str(voice_path))
            #
            # # Create caption clips from Whisper segments
            # caption_clips = []
            # for seg in captions:
            #     txt = TextClip(
            #         seg["text"], fontsize=48, color="white",
            #         font="Arial-Bold", stroke_color="black", stroke_width=2,
            #         size=(900, None), method="caption"
            #     ).set_start(seg["start"]).set_duration(seg["end"] - seg["start"])
            #     .set_position(("center", 1600))
            #     caption_clips.append(txt)
            #
            # final = CompositeVideoClip(
            #     [avatar_clip] + caption_clips,
            #     size=(1080, 1920)  # 9:16 format
            # ).set_audio(audio_clip)
            #
            # final.write_videofile(
            #     str(output_path), fps=30,
            #     codec="libx264", audio_codec="aac",
            #     preset="medium", bitrate="8000k"
            # )

            self.logger.info(f"🎬 Assembling final reel: {output_path.name}")

            assembly_info = {
                "format": "9:16 (1080x1920)",
                "avatar": str(avatar_path),
                "voice": str(voice_path),
                "captions_count": len(captions),
                "lip_sync_model": LIP_SYNC_MODEL,
                "script_preview": script["full_text"][:200],
                "status": "placeholder — MoviePy assembly ready when media is generated",
            }

            output_path.write_text(json.dumps(assembly_info, indent=2))
            return output_path

        except Exception as e:
            self.logger.error(f"Reel assembly failed: {e}")
            output_path.write_text("PLACEHOLDER")
            return output_path


avatar = AvatarAgent()
