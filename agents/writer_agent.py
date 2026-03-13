"""
AGENT-03 — Writer Agent
Fine-tuned LLM generates Hook → Body → CTA scripts in @talentsia voice.
Primary: Mistral 7B fine-tuned via Ollama REST API
Fallback: LLaMA 3.1 8B via Ollama → Anthropic Claude API

Model chain: mistral-ft → llama3.1:8b → claude-sonnet (cloud fallback)
"""

import json
import os
import uuid
from pathlib import Path

import httpx

from agents.base_agent import BaseAgent
from db.database import get_db

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_PRIMARY = os.getenv("OLLAMA_MODEL", "mistral-ft")
OLLAMA_MODEL_FALLBACK = os.getenv("OLLAMA_MODEL_FALLBACK", "llama3.1:8b")


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text()


class WriterAgent(BaseAgent):
    name = "writer"
    description = "Fine-tuned Mistral 7B. Hook → Body → CTA in your voice."

    async def execute(self, story_id: str = None, **kwargs) -> dict:
        # Get top ranked stories to write scripts for
        with get_db() as conn:
            if story_id:
                rows = conn.execute(
                    "SELECT * FROM stories WHERE id = ?", (story_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM stories WHERE status = 'ranked' ORDER BY final_score DESC LIMIT 3"
                ).fetchall()

        stories = [dict(r) for r in rows]
        if not stories:
            return {"scripts": 0, "message": "No ranked stories available"}

        system_prompt = load_system_prompt()
        scripts_created = []

        for story in stories:
            user_prompt = self._build_prompt(story)

            # Try models in order: Mistral-ft → LLaMA 3.1 → Claude
            script_text = None
            model_used = None

            # 1. Primary: Fine-tuned Mistral 7B
            script_text = await self._generate_ollama(
                system_prompt, user_prompt, OLLAMA_MODEL_PRIMARY
            )
            if script_text:
                model_used = OLLAMA_MODEL_PRIMARY

            # 2. Fallback: LLaMA 3.1 8B
            if not script_text:
                script_text = await self._generate_ollama(
                    system_prompt, user_prompt, OLLAMA_MODEL_FALLBACK
                )
                if script_text:
                    model_used = OLLAMA_MODEL_FALLBACK

            # 3. Cloud fallback: Anthropic Claude
            if not script_text:
                script_text = await self._generate_anthropic(system_prompt, user_prompt)
                if script_text:
                    model_used = "claude-sonnet"

            if not script_text:
                self.logger.error(f"Failed to generate script for: {story['title']}")
                continue

            # Parse Hook / Body / CTA
            parsed = self._parse_script(script_text)

            # Generate caption and hashtags
            caption = self._generate_caption(story["title"], parsed["cta"])
            hashtags = self._generate_hashtags(story["title"], story.get("source", ""))

            # Store to DB
            script_id = str(uuid.uuid4())
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO scripts (id, story_id, hook, body, cta, full_text,
                       word_count, model_used, caption, hashtags, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')""",
                    (
                        script_id,
                        story["id"],
                        parsed["hook"],
                        parsed["body"],
                        parsed["cta"],
                        script_text,
                        len(script_text.split()),
                        model_used,
                        caption,
                        hashtags,
                    ),
                )
                conn.execute(
                    "UPDATE stories SET status = 'scripted' WHERE id = ?",
                    (story["id"],),
                )

            scripts_created.append({
                "script_id": script_id,
                "story_title": story["title"],
                "word_count": len(script_text.split()),
                "model": model_used,
            })

        self.logger.info(f"✍️ Created {len(scripts_created)} scripts")
        return {"scripts": len(scripts_created), "details": scripts_created}

    def _build_prompt(self, story: dict) -> str:
        """Build the user prompt from a story."""
        return (
            f"News Headline: {story['title']}\n\n"
            f"Source: {story['source']} ({story.get('source_detail', '')})\n\n"
            f"Details: {story.get('content', '')[:500]}\n\n"
            f"Write a 60-90 word Instagram Reel script following the Hook → Body → CTA format.\n"
            f"Remember: Start with shock/curiosity/fear/FOMO. Be bold. Every sentence must earn its place."
        )

    async def _generate_ollama(self, system: str, user: str, model: str) -> str | None:
        """Generate script using local Ollama model."""
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "num_predict": 256,
                        },
                    },
                )
                if resp.status_code == 200:
                    content = resp.json().get("message", {}).get("content", "")
                    if content and len(content.split()) >= 20:
                        return content
        except Exception as e:
            self.logger.warning(f"Ollama ({model}) unavailable: {e}")
        return None

    async def _generate_anthropic(self, system: str, user: str) -> str | None:
        """Fallback: Generate script using Anthropic Claude API."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 512,
                        "system": system,
                        "messages": [{"role": "user", "content": user}],
                    },
                )
                if resp.status_code == 200:
                    return resp.json()["content"][0]["text"]
        except Exception as e:
            self.logger.warning(f"Anthropic fallback failed: {e}")
        return None

    def _parse_script(self, text: str) -> dict:
        """Parse script into Hook / Body / CTA sections."""
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

        if len(lines) <= 3:
            return {
                "hook": lines[0] if lines else "",
                "body": " ".join(lines[1:-1]),
                "cta": lines[-1] if len(lines) > 1 else "",
            }

        # Check for labeled sections
        hook, body, cta = [], [], []
        section = "hook"
        for line in lines:
            lower = line.lower()
            if any(label in lower for label in ["hook:", "hook -", "**hook", "## hook"]):
                section = "hook"
                line = line.split(":", 1)[-1].strip() if ":" in line else ""
            elif any(label in lower for label in ["body:", "body -", "**body", "## body"]):
                section = "body"
                line = line.split(":", 1)[-1].strip() if ":" in line else ""
            elif any(label in lower for label in ["cta:", "cta -", "**cta", "call to action", "## cta"]):
                section = "cta"
                line = line.split(":", 1)[-1].strip() if ":" in line else ""

            if line:
                {"hook": hook, "body": body, "cta": cta}[section].append(line)

        return {
            "hook": " ".join(hook) if hook else lines[0],
            "body": " ".join(body) if body else " ".join(lines[1:-1]),
            "cta": " ".join(cta) if cta else lines[-1],
        }

    def _generate_caption(self, title: str, cta: str) -> str:
        """Generate Instagram caption from story title and CTA."""
        return f"🔥 {title}\n\n{cta}\n\nAlways drop value. Always stay ahead. 🚀\n\n#Talentsia"

    def _generate_hashtags(self, title: str, source: str) -> str:
        """Generate relevant hashtags from story title."""
        # Base hashtags that always appear
        base_tags = ["AI", "Tech", "Innovation", "Future", "Trending", "Talentsia"]

        # Source-specific tags
        source_tags = {
            "reddit": ["RedditFinds"],
            "hackernews": ["HackerNews", "YCombinator"],
            "rss": ["TechNews"],
            "twitter": ["XPlatform"],
        }
        base_tags.extend(source_tags.get(source, []))

        # Dynamic tags from title
        keywords = title.lower().split()
        topic_map = {
            "ai": "ArtificialIntelligence",
            "gpt": "GPT",
            "openai": "OpenAI",
            "google": "Google",
            "apple": "Apple",
            "microsoft": "Microsoft",
            "jobs": "TechJobs",
            "hiring": "Hiring",
            "startup": "Startup",
            "robot": "Robotics",
            "autonomous": "Automation",
            "machine": "MachineLearning",
            "deep": "DeepLearning",
            "llm": "LLM",
            "neural": "NeuralNetworks",
        }
        for word in keywords:
            for key, tag in topic_map.items():
                if key in word and tag not in base_tags:
                    base_tags.append(tag)
                    break

        # Deduplicate and limit
        all_tags = list(dict.fromkeys(base_tags))[:20]
        return ",".join(f"#{tag}" for tag in all_tags)


writer = WriterAgent()
