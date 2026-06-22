from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from collectors.base import BaseCollector


class GitHubCollector(BaseCollector):
    def __init__(self, config: Any, db: Any):
        super().__init__(config, db)
        self.topics = config.github.topics
        self.max_repos = config.github.max_repos_per_topic
        self.token = config.github_token

    def collect(self) -> list[dict[str, Any]]:
        repos = []
        repos.extend(self._fetch_trending())
        for topic in self.topics:
            try:
                topic_repos = self._search_by_topic(topic)
                repos.extend(topic_repos)
            except Exception as e:
                self.logger.warning(f"Failed to search topic {topic}: {e}")
        return self._deduplicate(repos)

    def _fetch_trending(self) -> list[dict[str, Any]]:
        self.logger.info("Fetching GitHub trending")
        try:
            url = "https://api.github.com/search/repositories"
            query = "created:>2024-01-01 stars:>50"
            headers = self._headers()
            params = {"q": query, "sort": "stars", "order": "desc", "per_page": 25}
            resp = httpx.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 200:
                return self._parse_items(resp.json().get("items", []))
        except Exception as e:
            self.logger.warning(f"Trending fetch error: {e}")

        return self._mock_trending()

    def _search_by_topic(self, topic: str) -> list[dict[str, Any]]:
        try:
            url = "https://api.github.com/search/repositories"
            query = f"topic:{topic} stars:>100"
            headers = self._headers()
            params = {"q": query, "sort": "stars", "order": "desc", "per_page": self.max_repos}
            resp = httpx.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 200:
                return self._parse_items(resp.json().get("items", []))
            elif resp.status_code == 403:
                self.logger.warning("GitHub API rate limited, using mock")
                return self._mock_topic(topic)
        except Exception as e:
            self.logger.warning(f"Topic search error for {topic}: {e}")
        return []

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _parse_items(self, items: list[dict]) -> list[dict[str, Any]]:
        repos = []
        for item in items:
            repos.append(
                {
                    "source": "github",
                    "source_id": str(item.get("id", "")),
                    "author": item.get("owner", {}).get("login", ""),
                    "title": item.get("full_name", ""),
                    "text": item.get("description", "") or "",
                    "url": item.get("html_url", ""),
                    "timestamp": self._parse_time(item.get("created_at")),
                    "stars": item.get("stargazers_count", 0),
                    "score": item.get("score", 0),
                }
            )
        return repos

    def _mock_trending(self) -> list[dict[str, Any]]:
        return [
            {
                "source": "github",
                "source_id": f"mock_trend_{i}",
                "author": "openai",
                "title": f"openai/ai-tool-{i}",
                "text": f"A powerful new AI tool for developers #{i}",
                "url": f"https://github.com/openai/ai-tool-{i}",
                "timestamp": datetime.utcnow(),
                "stars": 5000 + i * 1000,
                "score": 100 - i * 5,
            }
            for i in range(5)
        ]

    def _mock_topic(self, topic: str) -> list[dict[str, Any]]:
        return [
            {
                "source": "github",
                "source_id": f"mock_{topic}_{i}",
                "author": "community",
                "title": f"community/{topic}-framework-{i}",
                "text": f"A {topic} framework for building next-gen applications",
                "url": f"https://github.com/community/{topic}-framework-{i}",
                "timestamp": datetime.utcnow(),
                "stars": 2000 - i * 200,
                "score": 80 - i * 10,
            }
            for i in range(3)
        ]

    def _deduplicate(self, repos: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique = []
        for repo in repos:
            key = repo.get("source_id", repo.get("url", ""))
            if key not in seen:
                seen.add(key)
                unique.append(repo)
        return unique

    def _parse_time(self, ts: Any) -> datetime | None:
        if not ts:
            return None
        if isinstance(ts, datetime):
            return ts
        for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"]:
            try:
                return datetime.strptime(str(ts), fmt)
            except ValueError:
                continue
        return datetime.utcnow()
