"""
AGENT-02 — Ranker Agent
Scores stories by: engagement × recency × niche relevance.
Uses sentence-transformers for semantic similarity when available,
falls back to keyword matching.
Forwards top 3 to the writer agent.

Scoring weights:
  - Engagement: 30%  (logarithmic scale)
  - Recency: 30%     (exponential decay, half-life ~14h)
  - Relevance: 40%   (keyword or embedding similarity)
"""

import math
import os
from datetime import datetime
from pathlib import Path

import yaml

from agents.base_agent import BaseAgent
from db.database import get_db

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"

# Try to load sentence-transformers for semantic ranking
_embedder = None
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _EMBEDDER_MODEL = os.getenv("RANKER_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    # Lazy load — only load model when first needed
except ImportError:
    SentenceTransformer = None
    st_util = None


def _get_embedder():
    global _embedder
    if _embedder is None and SentenceTransformer is not None:
        _embedder = SentenceTransformer(
            os.getenv("RANKER_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        )
    return _embedder


def load_niche_keywords() -> list[str]:
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    return config.get("niche_keywords", [])


class RankerAgent(BaseAgent):
    name = "ranker"
    description = "Scores stories: engagement × recency × relevance. Forwards top 3."

    async def execute(self, top_n: int = 3, **kwargs) -> dict:
        keywords = load_niche_keywords()

        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM stories WHERE status = 'new' ORDER BY scraped_at DESC LIMIT 100"
            ).fetchall()
            stories = [dict(r) for r in rows]

        if not stories:
            return {"ranked": 0, "top_stories": []}

        # Precompute niche embedding for semantic scoring
        niche_embedding = None
        embedder = _get_embedder()
        if embedder is not None:
            niche_text = " ".join(keywords)
            niche_embedding = embedder.encode(niche_text, convert_to_tensor=True)
            self.logger.info("🧠 Using sentence-transformers for semantic ranking")
        else:
            self.logger.info("📝 Using keyword matching for ranking (install sentence-transformers for semantic mode)")

        # Score each story
        for story in stories:
            story["engagement_score"] = self._engagement_score(story.get("score", 0))
            story["recency_score"] = self._recency_score(story.get("published_at"))

            text = story.get("title", "") + " " + story.get("content", "")
            if embedder is not None and niche_embedding is not None:
                story["relevance_score"] = self._semantic_relevance(
                    text, niche_embedding, embedder
                )
            else:
                story["relevance_score"] = self._keyword_relevance(text, keywords)

            story["final_score"] = round(
                story["engagement_score"] * 0.3
                + story["recency_score"] * 0.3
                + story["relevance_score"] * 0.4,
                3,
            )

        # Sort and pick top N
        stories.sort(key=lambda s: s["final_score"], reverse=True)
        top = stories[:top_n]

        # Update DB with scores and rank
        with get_db() as conn:
            for i, story in enumerate(stories):
                conn.execute(
                    """UPDATE stories SET relevance_score = ?, recency_score = ?,
                       final_score = ?, rank = ?, status = ?
                       WHERE id = ?""",
                    (
                        story["relevance_score"],
                        story["recency_score"],
                        story["final_score"],
                        i + 1,
                        "ranked" if story in top else "new",
                        story["id"],
                    ),
                )

        self.logger.info(
            f"🏆 Ranked {len(stories)} stories. Top {top_n}: "
            + ", ".join(f'"{s["title"][:40]}..." ({s["final_score"]})' for s in top)
        )

        return {
            "ranked": len(stories),
            "top_stories": [
                {
                    "id": s["id"],
                    "title": s["title"],
                    "source": s["source"],
                    "final_score": s["final_score"],
                    "engagement": s["engagement_score"],
                    "recency": s["recency_score"],
                    "relevance": s["relevance_score"],
                }
                for s in top
            ],
        }

    def _engagement_score(self, raw_score: int) -> float:
        """Logarithmic engagement score (0-1)."""
        if raw_score <= 0:
            return 0.0
        return min(1.0, math.log10(raw_score + 1) / 4)

    def _recency_score(self, published_at: str | None) -> float:
        """Exponential decay: 1.0 for now, ~0.1 after 48 hours."""
        if not published_at:
            return 0.3
        try:
            pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            hours_ago = (datetime.utcnow() - pub.replace(tzinfo=None)).total_seconds() / 3600
            return max(0.0, math.exp(-hours_ago / 20))
        except (ValueError, TypeError):
            return 0.3

    def _keyword_relevance(self, text: str, keywords: list[str]) -> float:
        """Keyword match relevance score (0-1)."""
        if not text or not keywords:
            return 0.0
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        return min(1.0, matches / max(len(keywords) * 0.3, 1))

    def _semantic_relevance(self, text: str, niche_embedding, embedder) -> float:
        """Semantic similarity using sentence-transformers (0-1)."""
        try:
            text_embedding = embedder.encode(text[:512], convert_to_tensor=True)
            similarity = st_util.cos_sim(text_embedding, niche_embedding).item()
            # Normalize from [-1, 1] to [0, 1]
            return max(0.0, min(1.0, (similarity + 1) / 2))
        except Exception:
            return 0.5


ranker = RankerAgent()
