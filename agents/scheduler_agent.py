"""
Scheduler Agent — APScheduler-based posting scheduler.
Manages optimal post times (7AM, 12PM, 7PM IST).
Tracks schedule slots and ensures max_posts_per_day compliance.
"""

import os
from datetime import datetime
from pathlib import Path

import yaml

from agents.base_agent import BaseAgent
from db.database import get_db

CONFIG_PATH = Path(__file__).parent.parent / "config" / "schedule.yaml"


def load_schedule() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class SchedulerAgent(BaseAgent):
    name = "scheduler"
    description = "APScheduler for cron jobs. Post at optimal times (7AM, 12PM, 7PM IST)."

    async def execute(self, action: str = "check", **kwargs) -> dict:
        config = load_schedule()
        schedule_config = config.get("schedule", {})

        if action == "check":
            return await self._check_schedule(schedule_config)
        elif action == "next_slot":
            return self._get_next_slot(schedule_config)
        elif action == "stats":
            return self._get_daily_stats()
        else:
            return {"error": f"Unknown action: {action}"}

    async def _check_schedule(self, config: dict) -> dict:
        """Check if now is a valid post time and if daily limit allows it."""
        now = datetime.utcnow()
        max_posts = config.get("max_posts_per_day", 3)

        # Count today's published posts
        today_start = now.replace(hour=0, minute=0, second=0).isoformat()
        with get_db() as conn:
            rows = conn.execute(
                """SELECT COUNT(*) as count FROM publish_history
                   WHERE published_at >= ? AND status = 'published'""",
                (today_start,),
            ).fetchone()
            today_count = dict(rows)["count"] if rows else 0

        can_post = today_count < max_posts
        post_times = config.get("post_times", ["07:00", "12:00", "19:00"])

        # Check if we're near a scheduled post time (within 30 min window)
        current_hour_min = now.strftime("%H:%M")
        near_schedule = any(
            abs(int(t.split(":")[0]) * 60 + int(t.split(":")[1])
                - int(current_hour_min.split(":")[0]) * 60
                - int(current_hour_min.split(":")[1])) <= 30
            for t in post_times
        )

        return {
            "can_post": can_post,
            "near_schedule": near_schedule,
            "today_count": today_count,
            "max_posts": max_posts,
            "remaining": max_posts - today_count,
            "post_times": post_times,
            "timezone": config.get("timezone", "Asia/Kolkata"),
        }

    def _get_next_slot(self, config: dict) -> dict:
        """Get the next available posting slot."""
        post_times = config.get("post_times", ["07:00", "12:00", "19:00"])
        now = datetime.utcnow()
        current_minutes = now.hour * 60 + now.minute

        for t in post_times:
            h, m = map(int, t.split(":"))
            slot_minutes = h * 60 + m
            if slot_minutes > current_minutes:
                return {
                    "next_slot": t,
                    "minutes_until": slot_minutes - current_minutes,
                    "timezone": config.get("timezone", "Asia/Kolkata"),
                }

        # All slots passed, next is tomorrow's first slot
        first = post_times[0]
        h, m = map(int, first.split(":"))
        return {
            "next_slot": f"tomorrow {first}",
            "minutes_until": (24 * 60 - current_minutes) + h * 60 + m,
            "timezone": config.get("timezone", "Asia/Kolkata"),
        }

    def _get_daily_stats(self) -> dict:
        """Get today's publishing stats."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0).isoformat()

        with get_db() as conn:
            published = conn.execute(
                "SELECT COUNT(*) as c FROM publish_history WHERE published_at >= ? AND status = 'published'",
                (today_start,),
            ).fetchone()
            pending = conn.execute(
                "SELECT COUNT(*) as c FROM reels WHERE status IN ('ready', 'pending_approval')"
            ).fetchone()
            approved = conn.execute(
                "SELECT COUNT(*) as c FROM reels WHERE status = 'approved'"
            ).fetchone()

        return {
            "published_today": dict(published)["c"] if published else 0,
            "pending_approval": dict(pending)["c"] if pending else 0,
            "approved_queue": dict(approved)["c"] if approved else 0,
            "date": now.strftime("%Y-%m-%d"),
        }


scheduler = SchedulerAgent()
