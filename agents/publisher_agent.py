"""
AGENT-06 — Publisher Agent
Telegram preview → human approval → Instagram Graph API publish.
Auto hashtags, caption gen, cover photo crop.

Flow:
  1. Send reel preview to Telegram with approve/reject buttons
  2. Wait for human approval
  3. On approval: publish to Instagram via Graph API
  4. Record publish history and update status
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

import httpx

from agents.base_agent import BaseAgent
from db.database import get_db

IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
IG_BUSINESS_ID = os.getenv("IG_BUSINESS_ACCOUNT_ID", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")


class PublisherAgent(BaseAgent):
    name = "publisher"
    description = "Telegram preview → approval → Instagram Graph API post."

    async def execute(self, reel_id: str = None, action: str = "preview", **kwargs) -> dict:
        if action == "preview":
            return await self._send_preview(reel_id)
        elif action == "publish":
            return await self._publish_to_instagram(reel_id)
        elif action == "reject":
            return await self._reject_reel(reel_id)
        else:
            return {"error": f"Unknown action: {action}"}

    async def _send_preview(self, reel_id: str = None) -> dict:
        """Send reel preview to Telegram for approval."""
        with get_db() as conn:
            if reel_id:
                rows = conn.execute(
                    """SELECT r.*, s.caption, s.hashtags, s.full_text, s.hook, s.body, s.cta,
                       st.title as story_title, st.source
                       FROM reels r
                       JOIN scripts s ON r.script_id = s.id
                       JOIN stories st ON s.story_id = st.id
                       WHERE r.id = ?""",
                    (reel_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT r.*, s.caption, s.hashtags, s.full_text, s.hook, s.body, s.cta,
                       st.title as story_title, st.source
                       FROM reels r
                       JOIN scripts s ON r.script_id = s.id
                       JOIN stories st ON s.story_id = st.id
                       WHERE r.status = 'ready'
                       ORDER BY r.created_at DESC LIMIT 3"""
                ).fetchall()

        reels = [dict(r) for r in rows]
        if not reels:
            return {"sent": 0, "message": "No reels ready for preview"}

        sent = []
        for reel in reels:
            message = self._format_preview_message(reel)
            success = await self._send_telegram(message)

            if success:
                with get_db() as conn:
                    conn.execute(
                        "UPDATE reels SET status = 'pending_approval' WHERE id = ?",
                        (reel["id"],),
                    )
                sent.append({"reel_id": reel["id"], "story": reel["story_title"][:50]})

        self.logger.info(f"📬 Sent {len(sent)} previews to Telegram")
        return {"sent": len(sent), "details": sent}

    def _format_preview_message(self, reel: dict) -> str:
        """Format a rich preview message for Telegram."""
        return (
            f"📹 *NEW REEL READY*\n\n"
            f"📰 *Story:* {reel['story_title']}\n"
            f"📡 *Source:* {reel.get('source', 'unknown')}\n\n"
            f"🪝 *Hook:*\n{reel.get('hook', '')}\n\n"
            f"📝 *Body:*\n{reel.get('body', '')}\n\n"
            f"🎯 *CTA:*\n{reel.get('cta', '')}\n\n"
            f"📸 *Caption:*\n{reel.get('caption', 'No caption')}\n\n"
            f"🏷️ *Hashtags:* {reel.get('hashtags', '')}\n\n"
            f"─────────────────────\n"
            f"✅ `/approve {reel['id'][:8]}` to publish\n"
            f"❌ `/reject {reel['id'][:8]}` to skip\n"
            f"✏️ `/edit {reel['id'][:8]}` to revise"
        )

    async def _publish_to_instagram(self, reel_id: str) -> dict:
        """Publish an approved reel to Instagram via Graph API."""
        with get_db() as conn:
            rows = conn.execute(
                """SELECT r.*, s.caption, s.hashtags
                   FROM reels r
                   JOIN scripts s ON r.script_id = s.id
                   WHERE r.id = ? AND r.status IN ('approved', 'pending_approval')""",
                (reel_id,),
            ).fetchall()

        if not rows:
            return {"error": "Reel not found or not approved"}

        reel = dict(rows[0])

        # Build Instagram caption with hashtags
        caption = reel.get("caption", "")
        if reel.get("hashtags"):
            hashtag_str = " ".join(
                tag if tag.startswith("#") else f"#{tag}"
                for tag in reel["hashtags"].split(",")
            )
            caption += f"\n\n{hashtag_str}"

        # Add @talentsia mention
        if "@talentsia" not in caption.lower():
            caption += "\n\n@talentsia"

        try:
            if not IG_ACCESS_TOKEN or not IG_BUSINESS_ID:
                self.logger.warning("Instagram credentials not configured — stub mode")
                # Record as stub publish
                with get_db() as conn:
                    conn.execute(
                        """INSERT INTO publish_history
                           (id, reel_id, platform, caption, hashtags, status)
                           VALUES (?, ?, 'instagram', ?, ?, 'stub')""",
                        (str(uuid.uuid4()), reel_id, caption, reel.get("hashtags", "")),
                    )
                    conn.execute(
                        "UPDATE reels SET status = 'stub_published' WHERE id = ?",
                        (reel_id,),
                    )
                return {"published": False, "mode": "stub", "caption": caption}

            async with httpx.AsyncClient(timeout=60) as client:
                # Step 1: Create media container
                create_resp = await client.post(
                    f"https://graph.facebook.com/v19.0/{IG_BUSINESS_ID}/media",
                    data={
                        "media_type": "REELS",
                        "video_url": reel.get("final_video", ""),
                        "caption": caption,
                        "share_to_feed": "true",
                        "access_token": IG_ACCESS_TOKEN,
                    },
                )

                if create_resp.status_code != 200:
                    return {"error": f"IG create failed: {create_resp.text}"}

                container_id = create_resp.json().get("id")

                # Step 2: Publish the container
                publish_resp = await client.post(
                    f"https://graph.facebook.com/v19.0/{IG_BUSINESS_ID}/media_publish",
                    data={
                        "creation_id": container_id,
                        "access_token": IG_ACCESS_TOKEN,
                    },
                )

                if publish_resp.status_code == 200:
                    post_id = publish_resp.json().get("id")

                    with get_db() as conn:
                        conn.execute(
                            """INSERT INTO publish_history
                               (id, reel_id, platform, post_id, caption, hashtags, published_at, status)
                               VALUES (?, ?, 'instagram', ?, ?, ?, ?, 'published')""",
                            (
                                str(uuid.uuid4()),
                                reel_id,
                                post_id,
                                caption,
                                reel.get("hashtags", ""),
                                datetime.utcnow().isoformat(),
                            ),
                        )
                        conn.execute(
                            "UPDATE reels SET status = 'published' WHERE id = ?",
                            (reel_id,),
                        )

                    self.logger.info(f"📱 Published to Instagram: {post_id}")
                    return {"published": True, "post_id": post_id, "reel_id": reel_id}
                else:
                    return {"error": f"IG publish failed: {publish_resp.text}"}

        except Exception as e:
            self.logger.error(f"Instagram publish failed: {e}")
            return {"error": str(e)}

    async def _reject_reel(self, reel_id: str) -> dict:
        """Reject a reel — mark as rejected."""
        with get_db() as conn:
            conn.execute(
                "UPDATE reels SET status = 'rejected' WHERE id = ?", (reel_id,)
            )
        self.logger.info(f"❌ Reel {reel_id[:8]} rejected")
        return {"rejected": True, "reel_id": reel_id}

    async def _send_telegram(self, message: str) -> bool:
        """Send a message to Telegram channel."""
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
            self.logger.warning("Telegram not configured — logging preview instead")
            self.logger.info(f"PREVIEW:\n{message}")
            return True

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={
                        "chat_id": TELEGRAM_CHAT,
                        "text": message,
                        "parse_mode": "Markdown",
                    },
                )
                return resp.status_code == 200
        except Exception as e:
            self.logger.error(f"Telegram send failed: {e}")
            return False


publisher = PublisherAgent()
