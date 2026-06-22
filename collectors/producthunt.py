from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from collectors.base import BaseCollector


class ProductHuntCollector(BaseCollector):
    def __init__(self, config: Any, db: Any):
        super().__init__(config, db)
        self.max_products = config.producthunt.max_products
        self.token = config.producthunt_token

    def collect(self) -> list[dict[str, Any]]:
        products = []

        if self.token and "your_" not in self.token:
            products = self._fetch_via_api()
        else:
            self.logger.warning("No Product Hunt token, using mock")
            products = self._mock_data()

        return products[: self.max_products]

    def _fetch_via_api(self) -> list[dict[str, Any]]:
        url = "https://api.producthunt.com/v2/api/graphql"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        query = """
        {
          posts(first: 20, order: VOTES) {
            edges {
              node {
                id
                name
                tagline
                url
                votesCount
                createdAt
                description
              }
            }
          }
        }
        """
        try:
            resp = httpx.post(url, json={"query": query}, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                edges = data.get("data", {}).get("posts", {}).get("edges", [])
                return self._parse_products(edges)
        except Exception as e:
            self.logger.warning(f"Product Hunt API error: {e}")
        return []

    def _parse_products(self, edges: list[dict]) -> list[dict[str, Any]]:
        products = []
        for edge in edges:
            node = edge.get("node", {})
            products.append(
                {
                    "source": "producthunt",
                    "source_id": str(node.get("id", "")),
                    "author": "",
                    "title": node.get("name", ""),
                    "text": node.get("tagline", node.get("description", "")),
                    "url": node.get("url", ""),
                    "timestamp": self._parse_time(node.get("createdAt")),
                    "votes": node.get("votesCount", 0),
                }
            )
        return products

    def _mock_data(self) -> list[dict[str, Any]]:
        import random

        tools = [
            "AI Code Assistant Pro",
            "Agent Studio",
            "MCP Hub",
            "LangFlow 2.0",
            "DevPilot AI",
            "AutoAgent",
            "PromptForge",
            "AI Testing Suite",
            "VectorDB Cloud",
            "AI Workflow Builder",
        ]
        return [
            {
                "source": "producthunt",
                "source_id": f"mock_ph_{i}",
                "author": "creator_team",
                "title": tools[i] if i < len(tools) else f"AI Tool {i}",
                "text": f"An innovative {tools[i % len(tools)]} that helps developers ship faster",
                "url": f"https://www.producthunt.com/posts/mock-{i}",
                "timestamp": datetime.utcnow(),
                "votes": random.randint(50, 2000),
            }
            for i in range(10)
        ]

    def _parse_time(self, ts: Any) -> datetime | None:
        if not ts:
            return None
        if isinstance(ts, datetime):
            return ts
        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"]:
            try:
                return datetime.strptime(str(ts), fmt)
            except ValueError:
                continue
        return datetime.utcnow()
