from __future__ import annotations

from typing import Any

from utils.logger import setup_logger


class EngagementScorer:
    def __init__(self, weights: dict[str, float]):
        self.weights = weights
        self.logger = setup_logger("EngagementScorer")

    def score(self, post: dict[str, Any]) -> float:
        score = 0.0
        mapping = {
            "likes": "likes",
            "replies": "replies",
            "retweets": "retweets",
            "quotes": "quotes",
            "stars": "stars",
            "votes": "votes",
            "score": "score",
        }
        for config_key, post_key in mapping.items():
            weight = self.weights.get(config_key, 0)
            value = post.get(post_key, 0)
            if isinstance(value, (int, float)):
                score += value * weight

        return round(score, 2)

    def score_all(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored = []
        for post in posts:
            post["engagement_score"] = self.score(post)
            scored.append(post)
        scored.sort(key=lambda x: x.get("engagement_score", 0), reverse=True)
        return scored

    def rank(self, posts: list[dict[str, Any]], top_n: int = 10) -> list[dict[str, Any]]:
        scored = self.score_all(posts)
        return scored[:top_n]
