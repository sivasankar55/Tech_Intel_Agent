from __future__ import annotations

import json
from typing import Any

from utils.logger import setup_logger


class AIAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", max_tokens: int = 4096):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.logger = setup_logger("AIAnalyzer")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                self.logger.warning(f"Gemini client init failed: {e}")
                self._client = None
        return self._client

    def analyze_posts(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.api_key or not self._get_client():
            self.logger.warning("AI analysis disabled (no API key or client)")
            return self._basic_analysis(posts)

        batch_size = 20
        analyzed = []

        for i in range(0, len(posts), batch_size):
            batch = posts[i : i + batch_size]
            try:
                results = self._analyze_batch(batch)
                analyzed.extend(results)
            except Exception as e:
                self.logger.warning(f"AI batch analysis failed: {e}")
                analyzed.extend(self._basic_analysis(batch))

        return analyzed

    def _analyze_batch(self, batch: list[dict]) -> list[dict]:
        posts_text = "\n---\n".join(
            f"Post {j}: Title: {p.get('title', '')} | Text: {p.get('text', '')[:200]} | Author: {p.get('author', '')} | Source: {p.get('source', '')} | Score: {p.get('engagement_score', 0)}"
            for j, p in enumerate(batch)
        )

        prompt = f"""Analyze these tech/AI posts. For each, determine:
1. Category (one of: AI News, AI Tools, Startup News, Open Source Projects, Coding Tools, Agent Frameworks, Automation Platforms, Research)
2. A 1-sentence summary
3. Whether it is high, medium, or low signal
4. Whether it is a duplicate of another post (reply "yes" or "no")

Return ONLY a JSON array of objects with fields: index, category, summary, signal, is_duplicate

Posts:
{posts_text}"""

        client = self._get_client()
        if not client:
            return self._basic_analysis(batch)

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"max_output_tokens": self.max_tokens},
            )
            text = response.text.strip()
            text = text.replace("```json", "").replace("```", "").strip()
            results = json.loads(text)

            for r in results:
                idx = r.get("index")
                if idx is not None and idx < len(batch):
                    batch[idx]["category"] = r.get("category")
                    batch[idx]["summary"] = r.get("summary")
                    batch[idx]["signal"] = r.get("signal", "medium")
                    if r.get("is_duplicate", "").lower().startswith("y"):
                        batch[idx]["is_duplicate"] = 1

            return batch
        except Exception as e:
            self.logger.warning(f"AI parse error: {e}")
            return self._basic_analysis(batch)

    def generate_report_summary(self, report_context: str) -> str:
        if not self.api_key or not self._get_client():
            return self._default_summary(report_context)

        prompt = f"""Based on this daily intelligence data, generate a concise executive summary (2-3 paragraphs) highlighting the most important developments, key trends, and strategic insights.

Data:
{report_context}

Executive Summary:"""

        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"max_output_tokens": 1024},
            )
            return response.text.strip()
        except Exception:
            return self._default_summary(report_context)

    def _basic_analysis(self, posts: list[dict]) -> list[dict]:
        for post in posts:
            if not post.get("category"):
                post["category"] = self._guess_category(post)
            if not post.get("summary"):
                text = post.get("text", "") or post.get("title", "") or ""
                post["summary"] = text[:150] + ("..." if len(text) > 150 else "")
            post["signal"] = "medium"
        return posts

    def _guess_category(self, post: dict) -> str:
        text = f"{post.get('title', '')} {post.get('text', '')}".lower()
        source = post.get("source", "")
        if source == "github":
            return "Open Source Projects"
        if source == "producthunt":
            return "AI Tools"
        if source == "hackernews":
            return "AI News"
        if "agent" in text or "framework" in text:
            return "Agent Frameworks"
        if "tool" in text or "code" in text or "developer" in text:
            return "Coding Tools"
        if "startup" in text or source == "twitter":
            return "Startup News"
        if "research" in text or "paper" in text:
            return "Research"
        if "automation" in text:
            return "Automation Platforms"
        return "AI News"

    def _default_summary(self, data: str) -> str:
        import re
        scores = re.findall(r"engagement_score[:\s]+([\d.]+)", data)
        avg = sum(float(s) for s in scores) / max(len(scores), 1)
        return f"Today's intelligence report covers significant activity across AI and tech. Average engagement score: {avg:.1f}. Key areas include AI tools, open source projects, and emerging agent frameworks."
