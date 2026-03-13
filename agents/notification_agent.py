"""
Notification Agent — Telegram bot notification system.
Sends daily summaries, approval prompts, and status updates.
Also handles incoming Telegram commands for approve/reject.
"""

import os
from datetime import datetime

import httpx

from agents.base_agent import BaseAgent
from db.database import get_db

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")


class NotificationAgent(BaseAgent):
    name = "notifier"
    description = "Telegram bot. Sends previews + approval prompts. Optional manual override."

    async def execute(self, action: str = "daily_summary", **kwargs) -> dict:
        if action == "daily_summary":
            return await self._send_daily_summary()
        elif action == "pipeline_status":
            return await self._send_pipeline_status()
        elif action == "alert":
            message = kwargs.get("message", "Alert from Talentsia pipeline")
            return await self._send_alert(message)
        else:
            return {"error": f"Unknown action: {action}"}

    async def _send_daily_summary(self) -> dict:
        """Send daily pipeline summary to Telegram."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0).isoformat()

        with get_db() as conn:
            stories_today = conn.execute(
                "SELECT COUNT(*) as c FROM stories WHERE scraped_at >= ?",
                (today_start,),
            ).fetchone()
            ranked = conn.execute(
                "SELECT COUNT(*) as c FROM stories WHERE status = 'ranked'"
            ).fetchone()
            scripts = conn.execute(
                "SELECT COUNT(*) as c FROM scripts WHERE created_at >= ?",
                (today_start,),
            ).fetchone()
            reels_ready = conn.execute(
                "SELECT COUNT(*) as c FROM reels WHERE status = 'ready'"
            ).fetchone()
            published = conn.execute(
                "SELECT COUNT(*) as c FROM publish_history WHERE published_at >= ? AND status = 'published'",
                (today_start,),
            ).fetchone()

        stats = {
            "stories": dict(stories_today)["c"] if stories_today else 0,
            "ranked": dict(ranked)["c"] if ranked else 0,
            "scripts": dict(scripts)["c"] if scripts else 0,
            "reels_ready": dict(reels_ready)["c"] if reels_ready else 0,
            "published": dict(published)["c"] if published else 0,
        }

        message = (
            f"📊 *TALENTSIA DAILY SUMMARY*\n"
            f"📅 {now.strftime('%B %d, %Y')}\n\n"
            f"📥 Stories scraped: *{stats['stories']}*\n"
            f"🏆 Top ranked: *{stats['ranked']}*\n"
            f"✍️ Scripts generated: *{stats['scripts']}*\n"
            f"🎬 Reels ready: *{stats['reels_ready']}*\n"
            f"📱 Published today: *{stats['published']}*\n\n"
        )

        if stats["reels_ready"] > 0:
            message += f"⚡ *{stats['reels_ready']} reels waiting for approval!*\n"
            message += "Use `/approve` to review and publish.\n"

        success = await self._send_telegram(message)
        return {"sent": success, "stats": stats}

    async def _send_pipeline_status(self) -> dict:
        """Send current pipeline status to Telegram."""
        from agents import ALL_AGENTS

        status_parts = ["🤖 *PIPELINE STATUS*\n"]
        for name, agent in ALL_AGENTS.items():
            status = agent.get_status()
            emoji = {"idle": "⚪", "running": "🔵", "success": "🟢", "failed": "🔴"}.get(
                status["status"], "⚫"
            )
            status_parts.append(
                f"{emoji} *{name}*: {status['status']} "
                f"(runs: {status['run_count']}, "
                f"rate: {status['success_rate']}%)"
            )

        message = "\n".join(status_parts)
        success = await self._send_telegram(message)
        return {"sent": success}

    async def _send_alert(self, message: str) -> dict:
        """Send an alert message to Telegram."""
        alert_message = f"🚨 *TALENTSIA ALERT*\n\n{message}"
        success = await self._send_telegram(alert_message)
        return {"sent": success, "message": message}

    async def _send_telegram(self, message: str) -> bool:
        """Send a message to Telegram channel."""
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
            self.logger.warning("Telegram not configured — logging instead")
            self.logger.info(f"NOTIFICATION:\n{message}")
            return True

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={
                        "chat_id": TELEGRAM_CHAT,
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                )
                if resp.status_code == 200:
                    self.logger.info("📤 Telegram notification sent")
                    return True
                else:
                    self.logger.error(f"Telegram API error: {resp.status_code}")
                    return False
        except Exception as e:
            self.logger.error(f"Telegram send failed: {e}")
            return False


notifier = NotificationAgent()
