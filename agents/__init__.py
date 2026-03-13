from agents.scraper_agent import scraper
from agents.ranker_agent import ranker
from agents.writer_agent import writer
from agents.visual_agent import visual
from agents.avatar_agent import avatar
from agents.publisher_agent import publisher
from agents.scheduler_agent import scheduler
from agents.notification_agent import notifier

ALL_AGENTS = {
    "scraper": scraper,
    "ranker": ranker,
    "writer": writer,
    "visual": visual,
    "avatar": avatar,
    "publisher": publisher,
    "scheduler": scheduler,
    "notifier": notifier,
}

PIPELINE_ORDER = ["scraper", "ranker", "writer", "visual", "avatar", "publisher"]

__all__ = [
    "scraper", "ranker", "writer", "visual", "avatar",
    "publisher", "scheduler", "notifier",
    "ALL_AGENTS", "PIPELINE_ORDER",
]
