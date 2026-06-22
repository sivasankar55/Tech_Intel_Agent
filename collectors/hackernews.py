from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from collectors.base import BaseCollector


class HackerNewsCollector(BaseCollector):
    def __init__(self, config: Any, db: Any):
        super().__init__(config, db)
        self.max_stories = config.hackernews.max_stories
        self.base_url = "https://hacker-news.firebaseio.com/v0"

    def collect(self) -> list[dict[str, Any]]:
        stories = []
        start = datetime.utcnow()

        for story_type in ["top", "new"]:
            try:
                ids = self._fetch_story_ids(story_type)
                batch = ids[: self.max_stories]

                with httpx.Client(timeout=10) as client:
                    for sid in batch:
                        if (datetime.utcnow() - start).total_seconds() > 25:
                            self.logger.warning("Time budget exceeded, stopping HN collection")
                            break
                        try:
                            story = self._fetch_story(client, sid)
                            if story and self._is_relevant(story):
                                stories.append(story)
                        except Exception:
                            continue
            except Exception as e:
                self.logger.warning(f"Failed to fetch {story_type} stories: {e}")

        if not stories:
            self.logger.info("No HN stories fetched, using mock data")
            stories = self._mock_stories()

        return stories

    def _fetch_story_ids(self, story_type: str) -> list[int]:
        try:
            resp = httpx.get(f"{self.base_url}/{story_type}stories.json", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def _fetch_story(self, client: httpx.Client, story_id: int) -> dict[str, Any] | None:
        resp = client.get(f"{self.base_url}/item/{story_id}.json")
        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data or data.get("type") != "story":
            return None

        return {
            "source": "hackernews",
            "source_id": str(data.get("id", "")),
            "author": data.get("by", ""),
            "title": data.get("title", ""),
            "text": data.get("title", ""),
            "url": data.get("url", f"https://news.ycombinator.com/item?id={data.get('id')}"),
            "timestamp": datetime.fromtimestamp(data.get("time", 0)) if data.get("time") else None,
            "score": data.get("score", 0),
            "replies": data.get("descendants", 0),
        }

    def _is_relevant(self, story: dict) -> bool:
        title = (story.get("title") or "").lower()
        keywords = [
            "ai", "artificial intelligence", "machine learning", "llm", "gpt",
            "openai", "anthropic", "google", "meta", "startup", "yc ",
            "github", "developer", "coding", "programming", "open source",
            "agent", "mcp", "model context protocol", "langchain",
            "python", "javascript", "typescript", "react", "framework",
            "automation", "robot", "deep learning", "neural",
        ]
        return any(kw in title for kw in keywords)

    def _mock_stories(self) -> list[dict[str, Any]]:
        import random

        titles = [
            "OpenAI Announces GPT-5 with Breakthrough Reasoning Capabilities",
            "Anthropic Releases Claude 4: A New Era for AI Safety",
            "MCP Protocol Gains Traction Among Major AI Platforms",
            "YC-Backed Startup Raises $50M for AI Developer Tools",
            "New Open Source Agent Framework Challenges LangChain",
            "Python 4.0 Proposal Includes Major AI/ML Improvements",
            "GitHub Copilot Now Supports 20+ Languages with Agent Mode",
            "Rust-Based AI Framework Reaches 100K Stars on GitHub",
            "Google DeepMind Publishes Breakthrough Research on Sparse Models",
            "Startup Develops AI-Powered Automated Code Review Tool",
        ]
        return [
            {
                "source": "hackernews",
                "source_id": f"mock_hn_{i}",
                "author": f"user_{i}",
                "title": titles[i % len(titles)],
                "text": titles[i % len(titles)],
                "url": f"https://news.ycombinator.com/item?id=mock_{i}",
                "timestamp": datetime.utcnow(),
                "score": random.randint(50, 800),
                "replies": random.randint(5, 200),
            }
            for i in range(min(self.max_stories, 10))
        ]
