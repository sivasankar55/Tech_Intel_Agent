from __future__ import annotations

from datetime import datetime
from typing import Any

import warnings

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from config.settings import NewsSource
from collectors.base import BaseCollector

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class NewsCollector(BaseCollector):
    def __init__(self, config: Any, db: Any):
        super().__init__(config, db)
        self.sources = config.news.sources
        self.max_articles = config.news.max_articles
        self.firecrawl_key = config.firecrawl_api_key

    def collect(self) -> list[dict[str, Any]]:
        articles = []
        for source in self.sources:
            try:
                if source.type == "rss":
                    items = self._fetch_rss(source)
                else:
                    items = self._scrape_page(source)
                articles.extend(items)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {source.name}: {e}")

        articles.sort(key=lambda x: x.get("score", 0), reverse=True)
        return articles[: self.max_articles]

    def _fetch_rss(self, source: NewsSource) -> list[dict[str, Any]]:
        try:
            resp = httpx.get(source.url, timeout=30, follow_redirects=True)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            items = soup.find_all("item") or soup.find_all("entry")
            results = []
            for item in items[: self.max_articles]:
                title_tag = item.find("title")
                link_tag = item.find("link")
                desc_tag = item.find("description") or item.find("summary")
                pub_tag = item.find("pubDate") or item.find("published") or item.find("updated")

                link = ""
                if link_tag:
                    link = link_tag.get("href", "") or link_tag.get_text().strip()

                results.append(
                    {
                        "source": "news",
                        "source_id": str(hash(link)),
                        "author": source.name,
                        "title": title_tag.get_text().strip() if title_tag else "",
                        "text": desc_tag.get_text().strip() if desc_tag else "",
                        "url": link,
                        "timestamp": self._parse_date(pub_tag.get_text().strip() if pub_tag else None),
                        "score": 50,
                    }
                )
            return results
        except Exception as e:
            self.logger.warning(f"RSS fetch error for {source.name}: {e}")
            return []

    def _scrape_page(self, source: NewsSource) -> list[dict[str, Any]]:
        if self.firecrawl_key and "your_" not in self.firecrawl_key:
            return self._fetch_via_firecrawl(source)
        return self._mock_articles(source)

    def _fetch_via_firecrawl(self, source: NewsSource) -> list[dict[str, Any]]:
        url = "https://api.firecrawl.dev/v1/scrape"
        headers = {
            "Authorization": f"Bearer {self.firecrawl_key}",
            "Content-Type": "application/json",
        }
        payload = {"url": source.url, "formats": ["markdown"]}
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("data", {}).get("markdown", "")
                if content:
                    return [
                        {
                            "source": "news",
                            "source_id": f"firecrawl_{source.name}",
                            "author": source.name,
                            "title": f"Article from {source.name}",
                            "text": content[:500],
                            "url": source.url,
                            "timestamp": datetime.utcnow(),
                            "score": 60,
                        }
                    ]
        except Exception as e:
            self.logger.warning(f"Firecrawl error: {e}")
        return []

    def _mock_articles(self, source: NewsSource) -> list[dict[str, Any]]:
        return [
            {
                "source": "news",
                "source_id": f"mock_news_{source.name}_{i}",
                "author": source.name,
                "title": f"Breaking AI News from {source.name} - Article {i}",
                "text": "Major developments in artificial intelligence: New models, frameworks, and tools are being released at an unprecedented pace.",
                "url": source.url,
                "timestamp": datetime.utcnow(),
                "score": 70 - i * 5,
            }
            for i in range(3)
        ]

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        return datetime.utcnow()
