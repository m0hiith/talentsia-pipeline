-- Talentsia Pipeline — SQLite Schema
-- Stories, scripts, media, reels, publish history, agent logs, schedule slots

CREATE TABLE IF NOT EXISTS stories (
    id              TEXT PRIMARY KEY,
    url             TEXT NOT NULL,
    url_hash        TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    source          TEXT NOT NULL,          -- reddit, rss, hackernews, twitter, worldmonitor
    source_detail   TEXT,                   -- subreddit name, feed name, etc.
    content         TEXT,
    author          TEXT,
    score           INTEGER DEFAULT 0,      -- source engagement score
    published_at    TIMESTAMP,
    scraped_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Ranking fields
    relevance_score REAL DEFAULT 0.0,
    recency_score   REAL DEFAULT 0.0,
    final_score     REAL DEFAULT 0.0,
    rank            INTEGER,
    status          TEXT DEFAULT 'new'      -- new, ranked, scripted, published, rejected
);

CREATE TABLE IF NOT EXISTS scripts (
    id              TEXT PRIMARY KEY,
    story_id        TEXT NOT NULL REFERENCES stories(id),
    hook            TEXT NOT NULL,
    body            TEXT NOT NULL,
    cta             TEXT NOT NULL,
    full_text       TEXT NOT NULL,
    word_count      INTEGER,
    model_used      TEXT DEFAULT 'mistral-7b-ft',
    caption         TEXT,                   -- Instagram caption
    hashtags        TEXT,                   -- Comma-separated
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status          TEXT DEFAULT 'draft'    -- draft, approved, rejected
);

CREATE TABLE IF NOT EXISTS media (
    id              TEXT PRIMARY KEY,
    script_id       TEXT NOT NULL REFERENCES scripts(id),
    media_type      TEXT NOT NULL,          -- thumbnail, image, broll, voice, avatar, captions, final
    file_path       TEXT NOT NULL,
    prompt_used     TEXT,
    model_used      TEXT,                   -- flux.1-schnell, cogvideox-5b, wan2.1, xtts-v2, sadtalker, latentsync, whisper-large-v3
    duration_secs   REAL,
    file_size_bytes INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reels (
    id              TEXT PRIMARY KEY,
    script_id       TEXT NOT NULL REFERENCES scripts(id),
    final_video     TEXT,                   -- Path to 9:16 assembled reel
    thumbnail       TEXT,                   -- Path to thumbnail
    duration_secs   REAL,
    status          TEXT DEFAULT 'assembling', -- assembling, ready, pending_approval, approved, published, stub_published, rejected, failed
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS publish_history (
    id              TEXT PRIMARY KEY,
    reel_id         TEXT NOT NULL REFERENCES reels(id),
    platform        TEXT NOT NULL DEFAULT 'instagram',
    post_id         TEXT,                   -- Instagram media ID
    post_url        TEXT,
    caption         TEXT,
    hashtags        TEXT,
    scheduled_at    TIMESTAMP,
    published_at    TIMESTAMP,
    status          TEXT DEFAULT 'pending'  -- pending, published, stub, failed
);

-- ── Agent Run Logs ──────────────────────────────
CREATE TABLE IF NOT EXISTS agent_logs (
    id              TEXT PRIMARY KEY,
    agent_name      TEXT NOT NULL,          -- scraper, ranker, writer, visual, avatar, publisher, scheduler, notifier
    run_number      INTEGER,
    status          TEXT NOT NULL,          -- success, failed
    duration_secs   REAL,
    result_summary  TEXT,                   -- JSON summary of run results
    error_message   TEXT,
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Schedule Slots ──────────────────────────────
CREATE TABLE IF NOT EXISTS schedule_slots (
    id              TEXT PRIMARY KEY,
    slot_time       TEXT NOT NULL,          -- "07:00", "12:00", "19:00"
    date            TEXT NOT NULL,          -- "2026-03-14"
    reel_id         TEXT REFERENCES reels(id),
    status          TEXT DEFAULT 'open'     -- open, assigned, published, skipped
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status);
CREATE INDEX IF NOT EXISTS idx_stories_final_score ON stories(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_stories_url_hash ON stories(url_hash);
CREATE INDEX IF NOT EXISTS idx_stories_source ON stories(source);
CREATE INDEX IF NOT EXISTS idx_scripts_story ON scripts(story_id);
CREATE INDEX IF NOT EXISTS idx_scripts_status ON scripts(status);
CREATE INDEX IF NOT EXISTS idx_media_script ON media(script_id);
CREATE INDEX IF NOT EXISTS idx_media_type ON media(media_type);
CREATE INDEX IF NOT EXISTS idx_reels_status ON reels(status);
CREATE INDEX IF NOT EXISTS idx_publish_status ON publish_history(status);
CREATE INDEX IF NOT EXISTS idx_agent_logs_name ON agent_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_logs_started ON agent_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_schedule_date ON schedule_slots(date);
