# Talentsia — Instagram Content AI Pipeline

> **8 autonomous agents · 9 open-source models · 100% self-hosted**
>
> Scrape → Rank → Write → Visualize → Avatar → Publish — fully automated Instagram Reels.

---

## 🏗️ Architecture

```
Scraper → Ranker → Writer → Visual → Avatar → Publisher
  📡        🏆       ✍️       🎨       🎭       📱
Reddit    Score    Mistral   FLUX.1   XTTS-v2   Telegram
RSS      Embed    LLaMA3    CogVideo  SadTalker IG Graph
HN       Rank     Claude    Wan2.1    LatentSync  API
X/Twitter         fallback           Whisper V3
```

## 📊 Pipeline Overview

| Agent | Model(s) | Function |
|-------|----------|----------|
| **Scraper** | — | Reddit JSON, RSS, HN, X/Twitter v2, WorldMonitor |
| **Ranker** | sentence-transformers | Engagement × recency × semantic relevance scoring |
| **Writer** | Mistral 7B-ft → LLaMA 3.1 → Claude | Hook → Body → CTA script generation |
| **Visual** | FLUX.1 Schnell + CogVideoX-5B / Wan2.1 | Thumbnails, key frames, B-roll video |
| **Avatar** | XTTS-v2 + SadTalker/LatentSync + Whisper V3 | Voice clone, lip sync, auto-captions |
| **Publisher** | — | Telegram preview → approval → Instagram publish |
| **Scheduler** | — | 3× daily post times (7AM / 12PM / 7PM IST) |
| **Notifier** | — | Telegram daily summaries + alerts |

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone <your-repo> talentsia-pipeline
cd talentsia-pipeline
cp .env.example .env
# Edit .env with your API keys
```

### 2. Docker Compose (Recommended)

```bash
docker compose up -d
```

This starts: API (8000), Dashboard (5173), Celery Worker, Beat Scheduler, Redis, Nginx (80).

### 3. Manual Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Start Redis
redis-server &
# Start API
uvicorn api.main:app --reload --port 8000
# Start Celery worker
celery -A celery_app worker --loglevel=info
# Start Celery beat
celery -A celery_app beat --loglevel=info
# Start Dashboard
cd dashboard && npm install && npm run dev
```

### 4. Access

- **Dashboard**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🔑 API Configuration

Copy `.env.example` → `.env` and fill in:

| Service | Required? | Notes |
|---------|-----------|-------|
| Ollama | ✅ Required | Local LLM — `ollama pull mistral` or fine-tuned model |
| Reddit | ❌ Optional | JSON API works without auth for public subreddits |
| Twitter/X | ❌ Optional | Bearer token for v2 search endpoint |
| Instagram | 🔶 For publishing | Graph API long-lived token + Business Account ID |
| Telegram | 🔶 For notifications | Bot token + chat ID for previews/approvals |
| Anthropic | ❌ Optional | Cloud LLM fallback when local models unavailable |
| ComfyUI | 🔶 For visuals | FLUX.1 Schnell checkpoint |
| XTTS-v2 | 🔶 For voice | Reference audio file required |

## 🎛️ Fine-Tuning

### Train your custom model:

```bash
# 1. Add your scripts to the dataset
ls fine_tuning/dataset/scripts.jsonl

# 2. Train with Unsloth + QLoRA (requires GPU)
python fine_tuning/train.py --epochs 3 --lr 2e-4

# 3. Export to GGUF for Ollama
python fine_tuning/export_gguf.py --name talentsia-writer

# 4. Register with Ollama
cd output/gguf && ollama create talentsia-writer -f Modelfile

# 5. Update .env
echo "OLLAMA_MODEL=talentsia-writer" >> .env
```

## 📁 Project Structure

```
talentsia-pipeline/
├── agents/                 # 8 autonomous agents
│   ├── base_agent.py       # Base class with metrics
│   ├── scraper_agent.py    # Reddit/RSS/HN/X/WorldMonitor
│   ├── ranker_agent.py     # Semantic scoring
│   ├── writer_agent.py     # LLM script generation
│   ├── visual_agent.py     # Image + video generation
│   ├── avatar_agent.py     # Voice + lip sync + captions
│   ├── publisher_agent.py  # Telegram + Instagram
│   ├── scheduler_agent.py  # Post scheduling
│   └── notification_agent.py # Telegram notifications
├── api/                    # FastAPI backend
│   ├── main.py
│   └── routes/
│       ├── stories.py
│       ├── agents.py
│       ├── reels.py
│       └── schedule.py
├── config/
│   ├── sources.yaml        # Data sources config
│   ├── schedule.yaml       # Posting schedule
│   └── nginx.conf          # Reverse proxy
├── dashboard/              # React (Vite) frontend
│   ├── Dockerfile
│   └── src/
│       ├── App.jsx         # Main dashboard
│       └── index.css       # Dark theme
├── db/
│   ├── schema.sql          # 7 tables + indexes
│   └── database.py         # SQLite manager
├── fine_tuning/
│   ├── train.py            # Unsloth + QLoRA
│   ├── export_gguf.py      # GGUF + Ollama Modelfile
│   └── dataset/
│       └── scripts.jsonl   # 10 sample entries
├── prompts/
│   ├── system_prompt.txt   # Voice DNA
│   └── visual_prompts.py   # Script → visual prompt mapping
├── celery_app.py           # Task queue + beat schedule
├── docker-compose.yml      # Full stack orchestration
├── Dockerfile              # Python backend
├── requirements.txt        # Dependencies
├── .env.example            # All configuration keys
└── README.md               # This file
```

## 🔒 Security Notes

- All API keys stored in `.env` (gitignored)
- All models run locally (self-hosted)
- Telegram approval required before Instagram posting
- No data sent to cloud unless Anthropic fallback triggers
- SQLite database local, WAL mode enabled

## 📄 License

MIT — Build what you want. Credit appreciated.
