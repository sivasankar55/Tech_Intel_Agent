from __future__ import annotations

from typing import Any

from utils.logger import setup_logger


class Deduplicator:
    def __init__(self):
        self.logger = setup_logger("Deduplicator")

    def deduplicate(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen_urls: set[str] = set()
        seen_texts: set[int] = set()
        unique = []

        for post in posts:
            url = post.get("url", "")
            text = (post.get("text", "") or post.get("title", "") or "").strip().lower()

            if url and url in seen_urls:
                post["is_duplicate"] = 1
                continue

            text_hash = hash(text[:100])
            if text_hash in seen_texts:
                post["is_duplicate"] = 1
                continue

            seen_urls.add(url)
            seen_texts.add(text_hash)
            unique.append(post)

        self.logger.info(f"Deduplication: {len(posts)} -> {len(unique)} unique")
        return unique
