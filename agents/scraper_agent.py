"""
AGENT-01 — Scraper Agent
Fetches trending stories from Reddit, RSS, HackerNews, X/Twitter.
Deduplicates by URL hash and stores to SQLite.
Runs every 2 hours via Celery.

Sources:
  - Reddit (PRAW JSON API) — r/AINews, r/technology, r/jobs, r/singularity
  - RSS — TechCrunch, The Verge, Wired, Ars Technica
  - HackerNews — Top + Best stories via Firebase API
  - X/Twitter — Bearer token v2 search (disabled by default, requires API key)
  - WorldMonitor — Fork of koala73/worldmonitor REST endpoint
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

import feedparser
import httpx
import yaml

from agents.base_agent import BaseAgent
from db.database import get_db

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"


def load_sources() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


class ScraperAgent(BaseAgent):
    name = "scraper"
    description = "Fetches Reddit, RSS, HackerNews, X/Twitter every 2hrs. Deduplicates & stores."

    async def execute(self, **kwargs) -> dict:
        config = load_sources()
        stories = []

        # ── Reddit ────────────────────────────
        if config.get("reddit", {}).get("enabled"):
            reddit_stories = await self._scrape_reddit(config["reddit"])
            stories.extend(reddit_stories)

        # ── RSS Feeds ─────────────────────────
        if config.get("rss", {}).get("enabled"):
            rss_stories = await self._scrape_rss(config["rss"])
            stories.extend(rss_stories)

        # ── HackerNews ────────────────────────
        if config.get("hackernews", {}).get("enabled"):
            hn_stories = await self._scrape_hackernews(config["hackernews"])
            stories.extend(hn_stories)

        # ── X / Twitter ───────────────────────
        if config.get("twitter", {}).get("enabled"):
            twitter_stories = await self._scrape_twitter(config["twitter"])
            stories.extend(twitter_stories)

        # ── WorldMonitor ──────────────────────
        if config.get("worldmonitor", {}).get("enabled"):
            wm_stories = await self._scrape_worldmonitor(config["worldmonitor"])
            stories.extend(wm_stories)

        # ── Deduplicate & Store ───────────────
        stored = self._store_stories(stories)

        return {
            "scraped": len(stories),
            "stored": stored,
            "sources": {
                "reddit": len([s for s in stories if s["source"] == "reddit"]),
                "rss": len([s for s in stories if s["source"] == "rss"]),
                "hackernews": len([s for s in stories if s["source"] == "hackernews"]),
                "twitter": len([s for s in stories if s["source"] == "twitter"]),
                "worldmonitor": len([s for s in stories if s["source"] == "worldmonitor"]),
            },
        }

    async def _scrape_reddit(self, config: dict) -> list[dict]:
        """Scrape Reddit using JSON API (no auth needed for public subreddits)."""
        stories = []
        async with httpx.AsyncClient() as client:
            for sub in config.get("subreddits", []):
                try:
                    url = f"https://www.reddit.com/r/{sub}/{config.get('sort', 'hot')}.json"
                    headers = {"User-Agent": "talentsia-scraper/1.0"}
                    resp = await client.get(
                        url, headers=headers, params={"limit": config.get("limit", 20)}
                    )
                    if resp.status_code != 200:
                        self.logger.warning(f"Reddit r/{sub} returned {resp.status_code}")
                        continue
                    data = resp.json()
                    for post in data.get("data", {}).get("children", []):
                        p = post["data"]
                        if p.get("score", 0) < config.get("min_score", 0):
                            continue
                        stories.append({
                            "url": f"https://reddit.com{p['permalink']}",
                            "title": p["title"],
                            "source": "reddit",
                            "source_detail": f"r/{sub}",
                            "content": p.get("selftext", "")[:2000],
                            "author": p.get("author", ""),
                            "score": p.get("score", 0),
                            "published_at": datetime.fromtimestamp(p["created_utc"]).isoformat(),
                        })
                except Exception as e:
                    self.logger.error(f"Error scraping r/{sub}: {e}")
        return stories

    async def _scrape_rss(self, config: dict) -> list[dict]:
        """Scrape RSS feeds using feedparser."""
        stories = []
        for feed_cfg in config.get("feeds", []):
            try:
                feed = feedparser.parse(feed_cfg["url"])
                for entry in feed.entries[:20]:
                    stories.append({
                        "url": entry.get("link", ""),
                        "title": entry.get("title", ""),
                        "source": "rss",
                        "source_detail": feed_cfg["name"],
                        "content": entry.get("summary", "")[:2000],
                        "author": entry.get("author", ""),
                        "score": 0,
                        "published_at": entry.get("published", datetime.utcnow().isoformat()),
                    })
            except Exception as e:
                self.logger.error(f"Error scraping RSS {feed_cfg['name']}: {e}")
        return stories

    async def _scrape_hackernews(self, config: dict) -> list[dict]:
        """Scrape HackerNews top/best stories via Firebase API."""
        stories = []
        async with httpx.AsyncClient() as client:
            for category in config.get("categories", ["topstories"]):
                try:
                    resp = await client.get(f"https://hacker-news.firebaseio.com/v0/{category}.json")
                    ids = resp.json()[:config.get("limit", 30)]

                    for story_id in ids[:15]:
                        item_resp = await client.get(
                            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                        )
                        item = item_resp.json()
                        if not item or item.get("score", 0) < config.get("min_score", 0):
                            continue
                        stories.append({
                            "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                            "title": item.get("title", ""),
                            "source": "hackernews",
                            "source_detail": category,
                            "content": item.get("text", "")[:2000] if item.get("text") else "",
                            "author": item.get("by", ""),
                            "score": item.get("score", 0),
                            "published_at": datetime.fromtimestamp(item.get("time", 0)).isoformat(),
                        })
                except Exception as e:
                    self.logger.error(f"Error scraping HN {category}: {e}")
        return stories

    async def _scrape_twitter(self, config: dict) -> list[dict]:
        """Scrape X/Twitter using v2 API with Bearer token.

        Requires: TWITTER_BEARER_TOKEN in .env
        Uses: GET /2/tweets/search/recent endpoint
        """
        import os
        bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
        if not bearer:
            self.logger.warning("X/Twitter: TWITTER_BEARER_TOKEN not set — skipping")
            return []

        stories = []
        hashtags = config.get("hashtags", ["AI", "TechJobs"])
        query = " OR ".join(f"#{tag}" for tag in hashtags) + " -is:retweet lang:en"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.twitter.com/2/tweets/search/recent",
                    headers={"Authorization": f"Bearer {bearer}"},
                    params={
                        "query": query,
                        "max_results": min(config.get("limit", 20), 100),
                        "tweet.fields": "created_at,public_metrics,author_id",
                        "expansions": "author_id",
                        "user.fields": "username",
                    },
                )
                if resp.status_code != 200:
                    self.logger.warning(f"Twitter API returned {resp.status_code}: {resp.text[:200]}")
                    return []

                data = resp.json()
                users = {
                    u["id"]: u["username"]
                    for u in data.get("includes", {}).get("users", [])
                }

                for tweet in data.get("data", []):
                    metrics = tweet.get("public_metrics", {})
                    stories.append({
                        "url": f"https://x.com/i/status/{tweet['id']}",
                        "title": tweet["text"][:120],
                        "source": "twitter",
                        "source_detail": f"@{users.get(tweet.get('author_id'), 'unknown')}",
                        "content": tweet["text"][:2000],
                        "author": users.get(tweet.get("author_id"), ""),
                        "score": metrics.get("like_count", 0) + metrics.get("retweet_count", 0),
                        "published_at": tweet.get("created_at", datetime.utcnow().isoformat()),
                    })

        except Exception as e:
            self.logger.error(f"Error scraping Twitter: {e}")

        return stories

    async def _scrape_worldmonitor(self, config: dict) -> list[dict]:
        """Scrape WorldMonitor fork for AI/Tech/Jobs category feeds.

        Uses: REST endpoint from local WorldMonitor instance or public API.
        Fork of koala73/worldmonitor — expose REST endpoint for local use.
        """
        stories = []
        base_url = config.get("base_url", "http://localhost:3001")

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                for category in config.get("categories", ["ai", "tech", "jobs"]):
                    try:
                        resp = await client.get(
                            f"{base_url}/api/stories",
                            params={"category": category, "limit": config.get("limit", 20)},
                        )
                        if resp.status_code != 200:
                            continue
                        for item in resp.json().get("stories", []):
                            stories.append({
                                "url": item.get("url", ""),
                                "title": item.get("title", ""),
                                "source": "worldmonitor",
                                "source_detail": category,
                                "content": item.get("summary", "")[:2000],
                                "author": item.get("source", ""),
                                "score": item.get("engagement", 0),
                                "published_at": item.get("published_at", datetime.utcnow().isoformat()),
                            })
                    except Exception as e:
                        self.logger.warning(f"WorldMonitor {category}: {e}")
        except Exception as e:
            self.logger.error(f"WorldMonitor connection failed: {e}")

        return stories

    def _store_stories(self, stories: list[dict]) -> int:
        """Deduplicate and store stories to SQLite."""
        stored = 0
        with get_db() as conn:
            for story in stories:
                h = url_hash(story["url"])
                existing = conn.execute(
                    "SELECT id FROM stories WHERE url_hash = ?", (h,)
                ).fetchone()
                if existing:
                    continue

                conn.execute(
                    """INSERT INTO stories (id, url, url_hash, title, source, source_detail,
                       content, author, score, published_at, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                    (
                        str(uuid.uuid4()),
                        story["url"],
                        h,
                        story["title"],
                        story["source"],
                        story.get("source_detail", ""),
                        story.get("content", ""),
                        story.get("author", ""),
                        story.get("score", 0),
                        story.get("published_at"),
                    ),
                )
                stored += 1

        self.logger.info(f"📦 Stored {stored} new stories (skipped {len(stories) - stored} dupes)")
        return stored


scraper = ScraperAgent()
