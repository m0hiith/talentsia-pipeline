"""
Celery application for the Talentsia pipeline.
Manages background tasks and scheduled agent runs.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Redis broker
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "talentsia",
    broker=REDIS_URL,
    backend=REDIS_URL.replace("/0", "/1"),
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,       # 10 min max per task
    task_soft_time_limit=540,  # 9 min soft limit
    worker_max_tasks_per_child=50,
    worker_prefetch_multiplier=1,
)

# ── Beat Schedule ─────────────────────────────────
app.conf.beat_schedule = {
    # Scrape all sources every 2 hours
    "scrape-sources": {
        "task": "tasks.run_scraper",
        "schedule": 7200.0,  # 2 hours in seconds
    },
    # Run full pipeline daily at 6:00 AM IST (prep for 7 AM post)
    "daily-pipeline": {
        "task": "tasks.run_full_pipeline",
        "schedule": crontab(hour=6, minute=0),
    },
    # Post scheduler checks 3x daily (7AM, 12PM, 7PM IST)
    "morning-post": {
        "task": "tasks.check_and_publish",
        "schedule": crontab(hour=7, minute=0),
    },
    "afternoon-post": {
        "task": "tasks.check_and_publish",
        "schedule": crontab(hour=12, minute=0),
    },
    "evening-post": {
        "task": "tasks.check_and_publish",
        "schedule": crontab(hour=19, minute=0),
    },
}


# ── Task Definitions ──────────────────────────────

@app.task(name="tasks.run_scraper")
def run_scraper():
    """Run the scraper agent."""
    import asyncio
    from agents.scraper_agent import scraper
    return asyncio.get_event_loop().run_until_complete(scraper.run())


@app.task(name="tasks.run_ranker")
def run_ranker():
    """Run the ranker agent."""
    import asyncio
    from agents.ranker_agent import ranker
    return asyncio.get_event_loop().run_until_complete(ranker.run())


@app.task(name="tasks.run_writer")
def run_writer(story_id=None):
    """Run the writer agent."""
    import asyncio
    from agents.writer_agent import writer
    return asyncio.get_event_loop().run_until_complete(writer.run(story_id=story_id))


@app.task(name="tasks.run_visual")
def run_visual(script_id=None):
    """Run the visual agent."""
    import asyncio
    from agents.visual_agent import visual
    return asyncio.get_event_loop().run_until_complete(visual.run(script_id=script_id))


@app.task(name="tasks.run_avatar")
def run_avatar(script_id=None):
    """Run the avatar agent."""
    import asyncio
    from agents.avatar_agent import avatar
    return asyncio.get_event_loop().run_until_complete(avatar.run(script_id=script_id))


@app.task(name="tasks.run_publisher")
def run_publisher(reel_id=None, action="preview"):
    """Run the publisher agent."""
    import asyncio
    from agents.publisher_agent import publisher
    return asyncio.get_event_loop().run_until_complete(
        publisher.run(reel_id=reel_id, action=action)
    )


@app.task(name="tasks.run_full_pipeline")
def run_full_pipeline():
    """Run the complete pipeline: scrape → rank → write → visuals → avatar."""
    import asyncio
    from agents.scraper_agent import scraper
    from agents.ranker_agent import ranker
    from agents.writer_agent import writer
    from agents.visual_agent import visual
    from agents.avatar_agent import avatar

    async def _pipeline():
        results = {}
        results["scraper"] = await scraper.run()
        results["ranker"] = await ranker.run()
        results["writer"] = await writer.run()
        results["visual"] = await visual.run()
        results["avatar"] = await avatar.run()
        return results

    return asyncio.get_event_loop().run_until_complete(_pipeline())


@app.task(name="tasks.check_and_publish")
def check_and_publish():
    """Check for approved reels and publish at scheduled times."""
    import asyncio
    from agents.publisher_agent import publisher
    from agents.notification_agent import notifier

    async def _check():
        # First send previews for any ready reels
        preview_result = await publisher.run(action="preview")
        # Then send notification
        await notifier.run(action="daily_summary")
        return preview_result

    return asyncio.get_event_loop().run_until_complete(_check())
