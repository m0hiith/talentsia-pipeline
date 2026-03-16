"""
╔══════════════════════════════════════════════════════════════════╗
║          TALENTSIA — NEWS INTELLIGENCE AGENT                     ║
║          Paste this entire file into Antigravity                 ║
║                                                                  ║
║  STEP 1: Fill in your API keys in the CONFIG block below        ║
║  STEP 2: Paste into Antigravity                                  ║
║  STEP 3: Antigravity installs deps + runs automatically          ║
║  STEP 4: Open the dashboard URL it gives you                     ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ════════════════════════════════════════════════════════════════════
#  ██████╗ ██████╗ ███╗   ██╗███████╗██╗ ██████╗
# ██╔════╝██╔═══██╗████╗  ██║██╔════╝██║██╔════╝
# ██║     ██║   ██║██╔██╗ ██║█████╗  ██║██║  ███╗
# ██║     ██║   ██║██║╚██╗██║██╔══╝  ██║██║   ██║
# ╚██████╗╚██████╔╝██║ ╚████║██║     ██║╚██████╔╝
#  ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝     ╚═╝ ╚═════╝
#
#  PASTE YOUR API KEYS BELOW — EVERYTHING ELSE IS READY
# ════════════════════════════════════════════════════════════════════

CONFIG = {

    # ── REDDIT API (optional but recommended for more posts) ──────────
    # Get free keys at: https://www.reddit.com/prefs/apps
    # Click "Create App" → choose "script" → fill any name + redirect URI
    # Without these keys: Reddit still works via public JSON (limited to 15 posts/subreddit)
    "REDDIT_CLIENT_ID":     "",      # paste here  e.g. "aBcDeFgHiJ1234"
    "REDDIT_CLIENT_SECRET": "",      # paste here  e.g. "xYzAbCdEfG567890HIJKLM"
    "REDDIT_USERNAME":      "",      # your Reddit username  e.g. "talentsia"
    "REDDIT_PASSWORD":      "",      # your Reddit password

    # ── TELEGRAM BOT (optional — for approval notifications in Week 4) ──
    # Get free bot token at: https://t.me/BotFather → /newbot
    # Get your chat ID at: https://t.me/userinfobot
    "TELEGRAM_BOT_TOKEN":   "",      # e.g. "7123456789:AAFxxxxxxxxxxxxxxxxxxxx"
    "TELEGRAM_CHAT_ID":     "",      # e.g. "123456789"

    # ── X / TWITTER API (optional — adds Twitter as a news source) ───
    # Get free tier at: https://developer.twitter.com/en/portal
    # Basic tier via GitHub Student Pack = free
    "TWITTER_BEARER_TOKEN": "",      # e.g. "AAAAAAAAAAAAAAAAAAAAAxxxx..."

    # ── EVERYTHING BELOW IS ALREADY CONFIGURED — DO NOT CHANGE ──────
    "DB_PATH":              "talentsia.db",
    "PORT":                 8000,
    "SCRAPE_INTERVAL_HOURS": 2,
    "RSS_TIMEOUT_SECONDS":  10,
    "REDDIT_POSTS_PER_SUB": 15,
    "HN_STORIES_TO_SCAN":   60,
    "MIN_VIRALITY_FOR_REEL": 7.0,
}

# ════════════════════════════════════════════════════════════════════
# DEPENDENCIES — Antigravity installs these automatically
# ════════════════════════════════════════════════════════════════════
# fastapi==0.115.0
# uvicorn[standard]==0.30.6
# feedparser==6.0.11
# requests==2.32.3
# apscheduler==3.10.4
# python-multipart==0.0.9

# ════════════════════════════════════════════════════════════════════
# IMPORTS
# ════════════════════════════════════════════════════════════════════

import hashlib
import sqlite3
import time
import logging
import math
import re
import os
import threading
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

import requests as http_requests
import feedparser
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s — %(message)s"
)
log = logging.getLogger("talentsia")

DB_PATH = CONFIG["DB_PATH"]

# ════════════════════════════════════════════════════════════════════
# SCRAPER — DATA SOURCES
# ════════════════════════════════════════════════════════════════════

RSS_FEEDS = [
    {"name": "TechCrunch AI",   "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "AI"},
    {"name": "TechCrunch",      "url": "https://techcrunch.com/feed/",                                  "category": "Tech"},
    {"name": "The Verge",       "url": "https://www.theverge.com/rss/index.xml",                        "category": "Tech"},
    {"name": "Wired",           "url": "https://www.wired.com/feed/rss",                                "category": "Tech"},
    {"name": "VentureBeat AI",  "url": "https://venturebeat.com/category/ai/feed/",                     "category": "AI"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/",                        "category": "AI"},
    {"name": "AI News",         "url": "https://artificialintelligence-news.com/feed/",                  "category": "AI"},
]

SUBREDDITS = [
    {"name": "r/AINews",           "url": "https://www.reddit.com/r/AINews/hot.json?limit=15",           "category": "AI"},
    {"name": "r/technology",       "url": "https://www.reddit.com/r/technology/hot.json?limit=15",       "category": "Tech"},
    {"name": "r/artificial",       "url": "https://www.reddit.com/r/artificial/hot.json?limit=15",       "category": "AI"},
    {"name": "r/MachineLearning",  "url": "https://www.reddit.com/r/MachineLearning/hot.json?limit=10",  "category": "AI"},
    {"name": "r/cscareerquestions","url": "https://www.reddit.com/r/cscareerquestions/hot.json?limit=10","category": "Jobs"},
    {"name": "r/datascience",      "url": "https://www.reddit.com/r/datascience/hot.json?limit=10",      "category": "AI"},
]

HN_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "openai", "anthropic",
    "machine learning", "neural", "jobs", "hiring", "layoffs",
    "tech", "startup", "automation", "robotics", "model",
]

KEYWORD_WEIGHTS = {
    "ai jobs": 3.0,       "tech jobs": 2.5,     "hiring": 2.0,
    "laid off": 2.5,      "layoffs": 2.5,       "job market": 2.0,
    "remote jobs": 2.0,   "salary": 1.8,        "tech salary": 2.5,
    "ai engineer": 3.0,   "ml engineer": 2.8,   "openai": 2.5,
    "anthropic": 2.5,     "claude": 2.0,        "chatgpt": 2.5,
    "gpt-4": 2.0,         "gemini": 2.0,        "llm": 2.5,
    "gpt": 2.0,           "artificial intelligence": 2.0,
    "machine learning": 2.0, "deep learning": 1.8, "neural network": 1.8,
    "transformer": 1.8,   "fine-tuning": 2.0,   "rlhf": 2.0,
    "agents": 2.2,        "agi": 2.5,           "nvidia": 2.0,
    "automation": 1.8,    "robotics": 1.8,      "startup": 1.5,
    "funding": 1.5,       "open source": 1.5,   "new model": 2.5,
    "just released": 2.0, "launches": 1.8,      "first ever": 2.0,
}

NEGATIVE_KEYWORDS = [
    "sponsored", "advertisement", "buy now", "subscribe",
    "weekly digest", "roundup", "podcast episode", "newsletter",
]

HEADERS = {"User-Agent": "Talentsia News Bot 1.0 (content pipeline)"}

# ════════════════════════════════════════════════════════════════════
# DATABASE
# ════════════════════════════════════════════════════════════════════

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash     TEXT    UNIQUE NOT NULL,
            title        TEXT    NOT NULL,
            url          TEXT    NOT NULL,
            source       TEXT,
            category     TEXT    DEFAULT 'Tech',
            summary      TEXT,
            score        INTEGER DEFAULT 0,
            upvotes      INTEGER DEFAULT 0,
            comments     INTEGER DEFAULT 0,
            virality     REAL    DEFAULT 0.0,
            fetched_at   TEXT    NOT NULL,
            published_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    log.info("DB ready")

def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\s+', ' ', text).strip()[:500]

def save(conn, story: dict) -> bool:
    try:
        conn.execute("""
            INSERT INTO stories
            (url_hash,title,url,source,category,summary,score,upvotes,comments,fetched_at,published_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            story["url_hash"], story["title"], story["url"],
            story.get("source",""), story.get("category","Tech"),
            story.get("summary",""), story.get("score",0),
            story.get("upvotes",0), story.get("comments",0),
            story["fetched_at"], story.get("published_at","")
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# ════════════════════════════════════════════════════════════════════
# SCRAPERS
# ════════════════════════════════════════════════════════════════════

def scrape_rss() -> dict:
    conn = sqlite3.connect(DB_PATH)
    new_count, errors = 0, []
    for feed_cfg in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_cfg["url"])
            for entry in feed.entries[:10]:
                url = entry.get("link","")
                if not url:
                    continue
                story = {
                    "url_hash":     url_hash(url),
                    "title":        clean(entry.get("title","")),
                    "url":          url,
                    "source":       feed_cfg["name"],
                    "category":     feed_cfg["category"],
                    "summary":      clean(entry.get("summary", entry.get("description","")))[:400],
                    "upvotes":      0,
                    "comments":     0,
                    "fetched_at":   datetime.now(timezone.utc).isoformat(),
                    "published_at": str(entry.get("published", entry.get("updated","")))[:50],
                }
                if save(conn, story):
                    new_count += 1
            time.sleep(0.5)
        except Exception as e:
            errors.append(f"RSS [{feed_cfg['name']}]: {e}")
    conn.close()
    log.info(f"RSS done — {new_count} new")
    return {"new": new_count, "errors": errors}


def scrape_hackernews() -> dict:
    conn = sqlite3.connect(DB_PATH)
    new_count, errors = 0, []
    try:
        resp = http_requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10, headers=HEADERS
        )
        story_ids = resp.json()[:CONFIG["HN_STORIES_TO_SCAN"]]
        for sid in story_ids:
            try:
                s = http_requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=8, headers=HEADERS
                ).json()
                if not s or s.get("type") != "story":
                    continue
                title = s.get("title","")
                if not any(kw in title.lower() for kw in HN_KEYWORDS):
                    continue
                url = s.get("url", f"https://news.ycombinator.com/item?id={sid}")
                story = {
                    "url_hash":     url_hash(url),
                    "title":        title,
                    "url":          url,
                    "source":       "HackerNews",
                    "category":     "Tech",
                    "summary":      f"HN — {s.get('descendants',0)} comments · {s.get('score',0)} pts",
                    "upvotes":      s.get("score",0),
                    "comments":     s.get("descendants",0),
                    "fetched_at":   datetime.now(timezone.utc).isoformat(),
                    "published_at": datetime.fromtimestamp(
                        s.get("time",0), tz=timezone.utc
                    ).isoformat(),
                }
                if save(conn, story):
                    new_count += 1
                time.sleep(0.1)
            except Exception as e:
                errors.append(f"HN item {sid}: {e}")
    except Exception as e:
        errors.append(f"HN fetch: {e}")
    conn.close()
    log.info(f"HackerNews done — {new_count} new")
    return {"new": new_count, "errors": errors}


def scrape_reddit() -> dict:
    conn = sqlite3.connect(DB_PATH)
    new_count, errors = 0, []

    # Use PRAW if credentials provided, else public JSON
    use_praw = all([
        CONFIG["REDDIT_CLIENT_ID"],
        CONFIG["REDDIT_CLIENT_SECRET"],
        CONFIG["REDDIT_USERNAME"],
        CONFIG["REDDIT_PASSWORD"],
    ])

    if use_praw:
        try:
            import praw
            reddit = praw.Reddit(
                client_id=CONFIG["REDDIT_CLIENT_ID"],
                client_secret=CONFIG["REDDIT_CLIENT_SECRET"],
                username=CONFIG["REDDIT_USERNAME"],
                password=CONFIG["REDDIT_PASSWORD"],
                user_agent="Talentsia Bot 1.0",
            )
            for sub_cfg in SUBREDDITS:
                sub_name = sub_cfg["name"].replace("r/","")
                try:
                    for post in reddit.subreddit(sub_name).hot(limit=CONFIG["REDDIT_POSTS_PER_SUB"]):
                        url = post.url if not post.is_self else f"https://reddit.com{post.permalink}"
                        story = {
                            "url_hash":     url_hash(url),
                            "title":        post.title,
                            "url":          url,
                            "source":       sub_cfg["name"],
                            "category":     sub_cfg["category"],
                            "summary":      clean(post.selftext)[:300] if post.selftext else f"{post.ups} upvotes · {post.num_comments} comments",
                            "upvotes":      post.ups,
                            "comments":     post.num_comments,
                            "fetched_at":   datetime.now(timezone.utc).isoformat(),
                            "published_at": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                        }
                        if save(conn, story):
                            new_count += 1
                    time.sleep(1.0)
                except Exception as e:
                    errors.append(f"PRAW [{sub_cfg['name']}]: {e}")
        except ImportError:
            log.warning("praw not installed — falling back to public JSON")
            use_praw = False

    if not use_praw:
        for sub_cfg in SUBREDDITS:
            try:
                resp = http_requests.get(sub_cfg["url"], timeout=10, headers=HEADERS)
                posts = resp.json().get("data",{}).get("children",[])
                for post in posts:
                    p = post.get("data",{})
                    url = p.get("url","")
                    if not url:
                        continue
                    if p.get("is_self"):
                        url = f"https://reddit.com{p.get('permalink','')}"
                    story = {
                        "url_hash":     url_hash(url),
                        "title":        p.get("title",""),
                        "url":          url,
                        "source":       sub_cfg["name"],
                        "category":     sub_cfg["category"],
                        "summary":      clean(p.get("selftext",""))[:300] or f"{p.get('ups',0)} upvotes",
                        "upvotes":      p.get("ups",0),
                        "comments":     p.get("num_comments",0),
                        "fetched_at":   datetime.now(timezone.utc).isoformat(),
                        "published_at": datetime.fromtimestamp(
                            p.get("created_utc",0), tz=timezone.utc
                        ).isoformat(),
                    }
                    if save(conn, story):
                        new_count += 1
                time.sleep(1.0)
            except Exception as e:
                errors.append(f"Reddit JSON [{sub_cfg['name']}]: {e}")

    conn.close()
    log.info(f"Reddit done — {new_count} new")
    return {"new": new_count, "errors": errors}


def scrape_twitter() -> dict:
    """Pulls trending AI/tech tweets if Twitter bearer token is set."""
    if not CONFIG["TWITTER_BEARER_TOKEN"]:
        return {"new": 0, "errors": ["Twitter token not set — skipping"]}

    conn = sqlite3.connect(DB_PATH)
    new_count, errors = 0, []
    queries = [
        "AI jobs -is:retweet lang:en",
        "OpenAI OR Anthropic OR Claude -is:retweet lang:en",
        "tech layoffs OR hiring 2025 -is:retweet lang:en",
    ]
    headers = {"Authorization": f"Bearer {CONFIG['TWITTER_BEARER_TOKEN']}"}
    for q in queries:
        try:
            resp = http_requests.get(
                "https://api.twitter.com/2/tweets/search/recent",
                params={
                    "query": q,
                    "max_results": 10,
                    "tweet.fields": "public_metrics,created_at,author_id",
                    "expansions": "author_id",
                    "user.fields": "username",
                },
                headers=headers,
                timeout=10,
            )
            data = resp.json()
            users = {u["id"]: u["username"] for u in data.get("includes",{}).get("users",[])}
            for tweet in data.get("data",[]):
                tid  = tweet["id"]
                url  = f"https://twitter.com/i/web/status/{tid}"
                m    = tweet.get("public_metrics",{})
                story = {
                    "url_hash":     url_hash(url),
                    "title":        tweet["text"][:200],
                    "url":          url,
                    "source":       f"@{users.get(tweet.get('author_id',''),'twitter')}",
                    "category":     "AI",
                    "summary":      f"{m.get('like_count',0)} likes · {m.get('retweet_count',0)} RTs",
                    "upvotes":      m.get("like_count",0),
                    "comments":     m.get("reply_count",0),
                    "fetched_at":   datetime.now(timezone.utc).isoformat(),
                    "published_at": tweet.get("created_at",""),
                }
                if save(conn, story):
                    new_count += 1
            time.sleep(1.0)
        except Exception as e:
            errors.append(f"Twitter [{q[:30]}]: {e}")
    conn.close()
    log.info(f"Twitter done — {new_count} new")
    return {"new": new_count, "errors": errors}


def run_full_scrape() -> dict:
    log.info("=== SCRAPE START ===")
    results = {
        "rss":        scrape_rss(),
        "hackernews": scrape_hackernews(),
        "reddit":     scrape_reddit(),
        "twitter":    scrape_twitter(),
    }
    total_new = sum(r["new"] for r in results.values())
    log.info(f"=== SCRAPE DONE — {total_new} new stories ===")
    return {"total_new": total_new, "sources": results}


# ════════════════════════════════════════════════════════════════════
# RANKER — VIRALITY SCORE 1-10
# ════════════════════════════════════════════════════════════════════

def score_niche(title: str, summary: str = "") -> float:
    text = (title + " " + summary).lower()
    if any(neg in text for neg in NEGATIVE_KEYWORDS):
        return 0.1
    weight = 0.0
    for kw, w in KEYWORD_WEIGHTS.items():
        if kw in text:
            weight += w * 2 if kw in title.lower() else w
    return min(weight / 8.0, 1.0)

def score_recency(published_at: Optional[str], fetched_at: str) -> float:
    try:
        ref = published_at or fetched_at
        dt = datetime.fromisoformat(ref.replace("Z","+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        hours_old = max((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 0)
        return math.exp(-0.0578 * hours_old)  # half-life 12hrs
    except Exception:
        return 0.3

def score_engagement(upvotes: int, comments: int, source: str) -> float:
    if source == "HackerNews":
        return min(upvotes/300, 1.0) * 0.6 + min(comments/200, 1.0) * 0.4
    if source.startswith("r/"):
        return min(upvotes/3000, 1.0) * 0.6 + min(comments/500, 1.0) * 0.4
    return 0.4  # RSS: no engagement data

def compute_virality(title, summary, upvotes, comments, source, published_at, fetched_at) -> float:
    raw = (
        score_engagement(upvotes, comments, source) * 0.40 +
        score_recency(published_at, fetched_at)    * 0.30 +
        score_niche(title, summary)                * 0.30
    )
    return round(1.0 + raw * 9.0, 2)

def rank_all() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id,title,summary,upvotes,comments,source,published_at,fetched_at FROM stories ORDER BY fetched_at DESC LIMIT 500"
    ).fetchall()
    for row in rows:
        v = compute_virality(
            row["title"], row["summary"] or "",
            row["upvotes"], row["comments"], row["source"],
            row["published_at"], row["fetched_at"],
        )
        conn.execute("UPDATE stories SET virality=? WHERE id=?", (v, row["id"]))
    conn.commit()
    conn.close()
    log.info(f"Ranked {len(rows)} stories")
    return {"ranked": len(rows)}


# ════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ════════════════════════════════════════════════════════════════════

app = FastAPI(title="Talentsia News Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

scheduler = BackgroundScheduler()


@app.on_event("startup")
def startup():
    init_db()
    # Auto scrape every N hours
    scheduler.add_job(
        lambda: (run_full_scrape(), rank_all()),
        "interval",
        hours=CONFIG["SCRAPE_INTERVAL_HOURS"],
        id="auto_scrape",
        replace_existing=True,
    )
    scheduler.start()
    log.info(f"Scheduler started — scraping every {CONFIG['SCRAPE_INTERVAL_HOURS']}hrs")


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()


# ── API ROUTES ────────────────────────────────────────────────────

@app.post("/api/scrape/sync")
def scrape_sync():
    """Full scrape + rank — waits for result. Use for first run."""
    result = run_full_scrape()
    rank_all()
    return {"status": "done", **result}

@app.post("/api/scrape")
def scrape_bg(background_tasks: BackgroundTasks):
    """Background scrape — returns immediately."""
    background_tasks.add_task(lambda: (run_full_scrape(), rank_all()))
    return {"status": "scraping", "message": "Running in background — refresh in 60s"}

@app.post("/api/rank")
def rank():
    return {"status": "done", **rank_all()}

@app.get("/api/stories")
def get_stories(
    limit:        int           = Query(100, ge=1, le=500),
    category:     Optional[str] = Query(None),
    min_virality: float         = Query(0.0, ge=0, le=10),
    source:       Optional[str] = Query(None),
    search:       Optional[str] = Query(None),
):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    q = "SELECT * FROM stories WHERE 1=1"
    params = []
    if category and category != "All":
        q += " AND category=?"; params.append(category)
    if min_virality > 0:
        q += " AND virality>=?"; params.append(min_virality)
    if source:
        q += " AND source=?"; params.append(source)
    if search:
        q += " AND (title LIKE ? OR summary LIKE ?)"; params += [f"%{search}%"]*2
    q += " ORDER BY virality DESC, fetched_at DESC LIMIT ?"; params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return {"stories": [dict(r) for r in rows], "count": len(rows)}

@app.get("/api/stats")
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    total     = conn.execute("SELECT COUNT(*) as c FROM stories").fetchone()["c"]
    by_source = conn.execute("SELECT source, COUNT(*) as count, ROUND(AVG(virality),2) as avg_v FROM stories GROUP BY source ORDER BY count DESC").fetchall()
    by_cat    = conn.execute("SELECT category, COUNT(*) as count FROM stories GROUP BY category").fetchall()
    top3      = conn.execute("SELECT title, virality, source, url FROM stories ORDER BY virality DESC LIMIT 3").fetchall()
    conn.close()
    return {
        "total":       total,
        "by_source":   [dict(r) for r in by_source],
        "by_category": [dict(r) for r in by_cat],
        "top3":        [dict(r) for r in top3],
    }

@app.get("/api/health")
def health():
    try:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
        conn.close()
        return {"status": "ok", "stories_in_db": count, "scheduler": scheduler.running}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/api/sources")
def get_sources():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT DISTINCT source FROM stories ORDER BY source").fetchall()
    conn.close()
    return {"sources": [r[0] for r in rows]}


# ── TELEGRAM NOTIFY (Week 4 preview) ────────────────────────────

def telegram_notify(message: str):
    """Send a message to your Telegram. Used by Publisher Agent in Week 4."""
    if not CONFIG["TELEGRAM_BOT_TOKEN"] or not CONFIG["TELEGRAM_CHAT_ID"]:
        log.info("Telegram not configured — skipping notification")
        return
    try:
        http_requests.post(
            f"https://api.telegram.org/bot{CONFIG['TELEGRAM_BOT_TOKEN']}/sendMessage",
            json={"chat_id": CONFIG["TELEGRAM_CHAT_ID"], "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        log.info("Telegram notification sent")
    except Exception as e:
        log.warning(f"Telegram error: {e}")


# ── SERVE DASHBOARD HTML INLINE ──────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>TALENTSIA — News Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne+Mono&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#0C0C0B;--bg2:#131312;--bg3:#1A1A18;
    --border:rgba(255,255,255,0.07);--border2:rgba(255,255,255,0.12);
    --text:#E8E6DF;--text2:#8A887F;--text3:#555450;
    --accent:#FF6B35;--accent2:rgba(255,107,53,0.12);--accent3:rgba(255,107,53,0.06);
    --green:#2ECC71;--blue:#4A9EFF;--yellow:#F5C518;--red:#EF4444;
  }
  html,body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;font-size:14px;line-height:1.5;min-height:100vh;overflow-x:hidden}
  ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px}
  .header{display:flex;align-items:center;justify-content:space-between;padding:0 28px;height:54px;border-bottom:1px solid var(--border);position:sticky;top:0;background:rgba(12,12,11,0.96);backdrop-filter:blur(8px);z-index:100;gap:16px;flex-wrap:wrap}
  .logo{font-family:'Syne Mono',monospace;font-size:15px;letter-spacing:2px;display:flex;align-items:center;gap:8px;white-space:nowrap}
  .logo-dot{color:var(--accent)}
  .hrow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  .pill{display:flex;align-items:center;gap:5px;font-family:'Syne Mono',monospace;font-size:10px;color:var(--text3);padding:3px 10px;border:1px solid var(--border);border-radius:3px}
  .dot{width:5px;height:5px;border-radius:50%;background:var(--green);box-shadow:0 0 5px var(--green);animation:pulse 2s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .btn{font-family:'Syne Mono',monospace;font-size:11px;padding:6px 14px;border:1px solid var(--border2);background:transparent;color:var(--text2);cursor:pointer;border-radius:3px;transition:all .15s;white-space:nowrap}
  .btn:hover{border-color:var(--accent);color:var(--accent)}
  .btn-p{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
  .btn-p:hover{background:#ff7d4d;color:#fff}
  .btn-p:disabled{background:#553322;border-color:#553322;color:#aa8877;cursor:not-allowed}
  .ticker-wrap{border-bottom:1px solid var(--border);overflow:hidden;height:26px;display:flex;align-items:center}
  .tlabel{font-family:'Syne Mono',monospace;font-size:9px;color:var(--accent);letter-spacing:2px;padding:0 14px;border-right:1px solid var(--border);height:100%;display:flex;align-items:center;white-space:nowrap;background:var(--accent3);flex-shrink:0}
  .tscroll{white-space:nowrap;animation:tick 40s linear infinite;font-family:'Syne Mono',monospace;font-size:10px;color:var(--text3);padding-left:20px}
  @keyframes tick{from{transform:translateX(0)}to{transform:translateX(-50%)}}
  .layout{display:grid;grid-template-columns:250px 1fr;min-height:calc(100vh - 80px)}
  .sidebar{border-right:1px solid var(--border);padding:20px 0;position:sticky;top:80px;height:calc(100vh - 80px);overflow-y:auto}
  .ss{padding:0 18px 16px;border-bottom:1px solid var(--border);margin-bottom:4px}
  .slabel{font-family:'Syne Mono',monospace;font-size:9px;letter-spacing:2px;color:var(--text3);margin-bottom:10px;text-transform:uppercase}
  .srow{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:4px}
  .sc{background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:9px 11px}
  .snum{font-family:'Syne Mono',monospace;font-size:20px;line-height:1;margin-bottom:3px}
  .slb{font-size:9px;color:var(--text3);letter-spacing:.5px}
  .src-item{display:flex;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border);cursor:pointer}
  .src-item:last-child{border-bottom:none}
  .src-item:hover .src-name,.src-item.active .src-name{color:var(--accent)}
  .src-item.active .src-cnt{background:var(--accent2);color:var(--accent);border-color:var(--accent)}
  .src-name{font-size:11px;color:var(--text2);transition:color .1s}
  .src-cnt{font-family:'Syne Mono',monospace;font-size:9px;padding:2px 6px;border:1px solid var(--border);border-radius:2px;color:var(--text3)}
  .ts{padding:8px 0;border-bottom:1px solid var(--border);cursor:pointer}
  .ts:last-child{border-bottom:none}
  .ts-rank{font-family:'Syne Mono',monospace;font-size:8px;color:var(--accent);letter-spacing:1px;margin-bottom:3px}
  .ts-title{font-size:10px;color:var(--text2);line-height:1.4}
  .ts:hover .ts-title{color:var(--text)}
  .main{display:flex;flex-direction:column}
  .controls{display:flex;align-items:center;gap:8px;padding:12px 24px;border-bottom:1px solid var(--border);flex-wrap:wrap;background:var(--bg);position:sticky;top:80px;z-index:90}
  .sw{flex:1;min-width:160px;position:relative}
  .sw svg{position:absolute;left:9px;top:50%;transform:translateY(-50%);opacity:.3}
  .si{width:100%;background:var(--bg2);border:1px solid var(--border);border-radius:3px;padding:6px 11px 6px 30px;color:var(--text);font-family:'Syne',sans-serif;font-size:12px;outline:none;transition:border-color .15s}
  .si::placeholder{color:var(--text3)}.si:focus{border-color:var(--border2)}
  .fg{display:flex;gap:5px;flex-wrap:wrap}
  .fb{font-family:'Syne Mono',monospace;font-size:9px;padding:5px 10px;border:1px solid var(--border);background:transparent;color:var(--text3);cursor:pointer;border-radius:3px;transition:all .12s;letter-spacing:.5px;white-space:nowrap}
  .fb:hover{border-color:var(--border2);color:var(--text2)}
  .fb.active{background:var(--accent2);border-color:var(--accent);color:var(--accent)}
  .vw{display:flex;align-items:center;gap:7px;white-space:nowrap}
  .vl{font-family:'Syne Mono',monospace;font-size:9px;color:var(--text3)}
  input[type=range]{-webkit-appearance:none;width:80px;height:2px;background:var(--border2);border-radius:1px;outline:none;cursor:pointer}
  input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:11px;height:11px;border-radius:50%;background:var(--accent);cursor:pointer}
  .vv{font-family:'Syne Mono',monospace;font-size:10px;color:var(--accent);min-width:20px}
  .feed{padding:16px 24px;flex:1}
  .fhdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
  .fcnt{font-family:'Syne Mono',monospace;font-size:10px;color:var(--text3)}
  .card{display:grid;grid-template-columns:48px 1fr auto;gap:0 14px;padding:14px 0;border-bottom:1px solid var(--border);cursor:pointer;text-decoration:none;color:inherit;transition:background .1s}
  .card:last-child{border-bottom:none}
  .card:hover{background:var(--bg2);margin:0 -24px;padding:14px 24px}
  .vc{display:flex;flex-direction:column;align-items:center;padding-top:2px}
  .vs{font-family:'Syne Mono',monospace;font-size:20px;line-height:1;margin-bottom:1px}
  .vlb{font-family:'Syne Mono',monospace;font-size:7px;letter-spacing:1px;color:var(--text3)}
  .vbar{width:26px;height:2px;border-radius:1px;margin-top:5px;background:var(--border);position:relative;overflow:hidden}
  .vfill{position:absolute;left:0;top:0;bottom:0;border-radius:1px}
  .sbdy{min-width:0}
  .smeta{display:flex;align-items:center;gap:7px;margin-bottom:5px;flex-wrap:wrap}
  .stag{font-family:'Syne Mono',monospace;font-size:8px;padding:2px 6px;border-radius:2px;border:1px solid;letter-spacing:.5px;text-transform:uppercase}
  .ai{color:#4A9EFF;border-color:rgba(74,158,255,.3);background:rgba(74,158,255,.06)}
  .tc{color:#A78BFA;border-color:rgba(167,139,250,.3);background:rgba(167,139,250,.06)}
  .jb{color:#2ECC71;border-color:rgba(46,204,113,.3);background:rgba(46,204,113,.06)}
  .stime,.ssrc{font-family:'Syne Mono',monospace;font-size:8px;color:var(--text3)}
  .stitle{font-family:'Syne',sans-serif;font-size:14px;font-weight:600;line-height:1.4;color:var(--text);margin-bottom:5px;transition:color .1s}
  .card:hover .stitle{color:var(--accent)}
  .ssum{font-size:11px;color:var(--text3);line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .sact{display:flex;flex-direction:column;align-items:flex-end;gap:5px;padding-top:2px;flex-shrink:0}
  .erow{display:flex;gap:8px}
  .est{font-family:'Syne Mono',monospace;font-size:9px;color:var(--text3)}
  .ol{font-family:'Syne Mono',monospace;font-size:8px;padding:3px 8px;border:1px solid var(--border);border-radius:2px;color:var(--text3);background:transparent;text-decoration:none;white-space:nowrap}
  .ol:hover{border-color:var(--accent);color:var(--accent)}
  .empty{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:80px 20px;text-align:center;gap:14px}
  .ei{font-family:'Syne Mono',monospace;font-size:28px;color:var(--text3)}
  .et{font-size:15px;font-weight:600;color:var(--text2)}
  .es{font-size:11px;color:var(--text3);max-width:300px;line-height:1.6}
  .sk{background:linear-gradient(90deg,var(--bg2) 25%,var(--bg3) 50%,var(--bg2) 75%);background-size:200% 100%;animation:shimmer 1.5s infinite;border-radius:3px}
  @keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
  .skc{display:grid;grid-template-columns:48px 1fr;gap:14px;padding:14px 0;border-bottom:1px solid var(--border)}
  #toast{position:fixed;bottom:20px;right:20px;background:var(--bg2);border:1px solid var(--border2);border-radius:4px;padding:10px 16px;font-family:'Syne Mono',monospace;font-size:11px;color:var(--text2);z-index:999;transform:translateY(60px);opacity:0;transition:all .2s;max-width:320px}
  #toast.show{transform:translateY(0);opacity:1}
  #toast.ok{border-left:3px solid var(--green);color:var(--green)}
  #toast.err{border-left:3px solid var(--red);color:var(--red)}
  #toast.info{border-left:3px solid var(--accent);color:var(--accent)}
  @media(max-width:860px){.layout{grid-template-columns:1fr}.sidebar{display:none}.sact{display:none}.header{padding:0 14px}.feed,.controls{padding:12px 14px}.card:hover{margin:0 -14px;padding:14px 14px}}
</style>
</head>
<body>
<header class="header">
  <div class="logo">TALENTSIA<span class="logo-dot">.</span><span style="color:var(--text3);font-size:10px;letter-spacing:1px">NEWS INTEL</span></div>
  <div class="hrow">
    <div class="pill"><span class="dot"></span><span id="db-count">— stories</span></div>
    <button class="btn" onclick="rerank()">RE-RANK</button>
    <button class="btn btn-p" id="sbtn" onclick="doScrape()">▶ PULL NEWS</button>
  </div>
</header>
<div class="ticker-wrap">
  <div class="tlabel">LIVE FEED</div>
  <div class="tscroll" id="ticker">Loading headlines…&nbsp;&nbsp;&nbsp;&nbsp;Loading headlines…</div>
</div>
<div class="layout">
  <aside class="sidebar">
    <div class="ss">
      <div class="slabel">Overview</div>
      <div class="srow">
        <div class="sc"><div class="snum" id="s-total">—</div><div class="slb">TOTAL</div></div>
        <div class="sc"><div class="snum" style="color:var(--accent)" id="s-top">—</div><div class="slb">TOP SCORE</div></div>
      </div>
    </div>
    <div class="ss" id="top3-sec">
      <div class="slabel">Top Picks Today</div>
      <div id="top3"></div>
    </div>
    <div class="ss" style="border-bottom:none">
      <div class="slabel">Sources</div>
      <div id="src-list">
        <div class="src-item active" onclick="fSrc(null,this)">
          <span class="src-name" style="color:var(--text)">All Sources</span>
          <span class="src-cnt" id="src-all">—</span>
        </div>
      </div>
    </div>
  </aside>
  <main class="main">
    <div class="controls">
      <div class="sw">
        <svg width="13" height="13" fill="none" stroke="white" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input class="si" type="text" placeholder="Search stories…" id="search" oninput="dLoad()"/>
      </div>
      <div class="fg">
        <button class="fb active" onclick="fCat('All',this)">ALL</button>
        <button class="fb" onclick="fCat('AI',this)">AI</button>
        <button class="fb" onclick="fCat('Tech',this)">TECH</button>
        <button class="fb" onclick="fCat('Jobs',this)">JOBS</button>
      </div>
      <div class="vw">
        <span class="vl">MIN VIRAL</span>
        <input type="range" min="0" max="9" step="1" value="0" id="vslider" oninput="document.getElementById('vval').textContent=this.value;dLoad()">
        <span class="vv" id="vval">0</span>
      </div>
    </div>
    <div class="feed" id="feed"></div>
  </main>
</div>
<div id="toast"></div>
<script>
let CAT=null,SRC=null,dtimer=null;
const API=window.location.origin;
function toast(m,t='info'){const e=document.getElementById('toast');e.textContent=m;e.className='show '+t;clearTimeout(e._t);e._t=setTimeout(()=>e.className='',3200)}
function vcol(v){return v>=8?'#FF6B35':v>=6?'#F5C518':v>=4?'#4A9EFF':'#555450'}
function ago(s){if(!s)return'';try{const d=(Date.now()-new Date(s))/1000;if(d<3600)return Math.round(d/60)+'m ago';if(d<86400)return Math.round(d/3600)+'h ago';return Math.round(d/86400)+'d ago'}catch{return''}}
function dLoad(){clearTimeout(dtimer);dtimer=setTimeout(load,300)}
function fCat(c,b){CAT=c;document.querySelectorAll('.fb').forEach(x=>x.classList.remove('active'));b.classList.add('active');load()}
function fSrc(s,el){SRC=s;document.querySelectorAll('.src-item').forEach(x=>x.classList.remove('active'));el.classList.add('active');load()}
function skel(n){return Array.from({length:n},()=>`<div class="skc"><div><div class="sk" style="width:38px;height:26px;margin-bottom:3px"></div></div><div><div class="sk" style="width:110px;height:9px;margin-bottom:7px"></div><div class="sk" style="width:90%;height:14px;margin-bottom:5px"></div><div class="sk" style="width:65%;height:10px"></div></div></div>`).join('')}
async function load(){
  const q=document.getElementById('search').value.trim();
  const mv=document.getElementById('vslider').value;
  const p=new URLSearchParams({limit:100});
  if(CAT&&CAT!=='All')p.set('category',CAT);
  if(parseFloat(mv)>0)p.set('min_virality',mv);
  if(SRC)p.set('source',SRC);
  if(q)p.set('search',q);
  const feed=document.getElementById('feed');
  feed.innerHTML=skel(6);
  try{
    const r=await fetch(`${API}/api/stories?${p}`);
    const d=await r.json();
    render(d.stories||[]);
  }catch(e){
    feed.innerHTML=`<div class="empty"><div class="ei">!</div><div class="et">Server not reachable</div><div class="es">Make sure the app is running. Check the Antigravity logs.</div></div>`;
  }
}
function render(stories){
  const feed=document.getElementById('feed');
  if(!stories.length){
    feed.innerHTML=`<div class="empty"><div class="ei">◌</div><div class="et">No stories yet</div><div class="es">Click PULL NEWS to fetch the latest AI, tech and jobs stories from Reddit, HackerNews and RSS.</div><button class="btn btn-p" style="margin-top:8px" onclick="doScrape()">▶ PULL NEWS NOW</button></div>`;
    return;
  }
  const cc={'AI':'ai','Tech':'tc','Jobs':'jb'};
  feed.innerHTML=`<div class="fhdr"><span class="fcnt">${stories.length} STORIES</span><span class="fcnt">sorted by virality ↓</span></div>`+
  stories.map(s=>{
    const v=parseFloat(s.virality||0).toFixed(1);
    const col=vcol(parseFloat(v));
    const pct=Math.round(parseFloat(v)/10*100);
    const c=cc[s.category]||'tc';
    const a=ago(s.published_at||s.fetched_at);
    return `<a class="card" href="${s.url}" target="_blank" rel="noopener">
      <div class="vc"><div class="vs" style="color:${col}">${v}</div><div class="vlb">VIRAL</div><div class="vbar"><div class="vfill" style="width:${pct}%;background:${col}"></div></div></div>
      <div class="sbdy">
        <div class="smeta"><span class="stag ${c}">${s.category}</span><span class="ssrc">${s.source}</span>${a?`<span class="stime">${a}</span>`:''}</div>
        <div class="stitle">${s.title}</div>
        ${s.summary?`<div class="ssum">${s.summary}</div>`:''}
      </div>
      <div class="sact">
        <div class="erow">${s.upvotes?`<div class="est">▲ ${s.upvotes.toLocaleString()}</div>`:''} ${s.comments?`<div class="est">💬 ${s.comments.toLocaleString()}</div>`:''}</div>
        <span class="ol">OPEN ↗</span>
      </div>
    </a>`;
  }).join('');
}
async function loadStats(){
  try{
    const r=await fetch(`${API}/api/stats`);
    const d=await r.json();
    document.getElementById('s-total').textContent=d.total||0;
    document.getElementById('db-count').textContent=`${d.total||0} stories`;
    const t=d.top3?.[0];
    if(t)document.getElementById('s-top').textContent=parseFloat(t.virality).toFixed(1);
    document.getElementById('top3').innerHTML=(d.top3||[]).map((s,i)=>`<div class="ts"><div class="ts-rank">#${i+1} · ${parseFloat(s.virality).toFixed(1)} VIRALITY</div><div class="ts-title">${s.title}</div></div>`).join('');
    const total=d.total||0;
    document.getElementById('src-list').innerHTML=`<div class="src-item active" onclick="fSrc(null,this)"><span class="src-name" style="color:var(--text)">All Sources</span><span class="src-cnt">${total}</span></div>`+
    (d.by_source||[]).map(s=>`<div class="src-item" onclick="fSrc('${s.source}',this)"><span class="src-name">${s.source}</span><span class="src-cnt">${s.count}</span></div>`).join('');
    const hl=(d.top3||[]).map(s=>s.title).join('   ·   ');
    if(hl)document.getElementById('ticker').textContent=hl+'   ·   '+hl;
  }catch(e){}
}
async function doScrape(){
  const btn=document.getElementById('sbtn');
  btn.disabled=true;btn.textContent='⟳ FETCHING…';
  toast('Scraping Reddit, HackerNews & RSS feeds…','info');
  try{
    const r=await fetch(`${API}/api/scrape/sync`,{method:'POST'});
    const d=await r.json();
    toast(`✓ ${d.total_new||0} new stories pulled & ranked`,'ok');
    await loadStats();await load();
  }catch(e){toast('Error: '+e.message,'err')}
  finally{btn.disabled=false;btn.textContent='▶ PULL NEWS'}
}
async function rerank(){
  toast('Re-ranking…','info');
  try{await fetch(`${API}/api/rank`,{method:'POST'});toast('✓ Re-ranked','ok');await load();await loadStats()}
  catch(e){toast('Re-rank failed','err')}
}
(async()=>{await loadStats();await load();setInterval(loadStats,60000)})();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


# ════════════════════════════════════════════════════════════════════
# ENTRY POINT — Antigravity runs this automatically
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=CONFIG["PORT"],
        reload=False,
        log_level="info",
    )
