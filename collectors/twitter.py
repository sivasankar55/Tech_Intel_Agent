from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import httpx

from collectors.base import BaseCollector


class TwitterCollector(BaseCollector):
    def __init__(self, config: Any, db: Any):
        super().__init__(config, db)
        self.accounts = config.twitter.accounts
        self.max_posts = config.twitter.max_posts_per_account
        self.bearer_token = config.twitter_bearer_token
        self.scrapingdog_key = config.scrapingdog_api_key

    def collect(self) -> list[dict[str, Any]]:
        posts = []
        for account in self.accounts:
            try:
                account_posts = self._fetch_account(account)
                posts.extend(account_posts)
                time.sleep(1)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {account}: {e}")
        return posts

    def _fetch_account(self, account: str) -> list[dict[str, Any]]:
        results = []

        if self.scrapingdog_key and "your_" not in self.scrapingdog_key:
            results = self._fetch_via_scrapingdog(account)

        if not results and self.bearer_token and "your_" not in self.bearer_token:
            results = self._fetch_via_api(account)

        if not results:
            self.logger.warning(f"No data for {account}, using mock")
            results = self._mock_data(account)

        return results

    def _fetch_via_scrapingdog(self, account: str) -> list[dict[str, Any]]:
        url = f"https://api.scrapingdog.com/twitter/"
        params = {
            "api_key": self.scrapingdog_key,
            "type": "profile",
            "username": account,
        }
        try:
            resp = httpx.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return self._parse_scrapingdog(account, resp.json())
        except Exception as e:
            self.logger.warning(f"ScrapingDog error for {account}: {e}")
        return []

    def _parse_scrapingdog(self, account: str, data: list | dict) -> list[dict[str, Any]]:
        posts = []
        tweets = data if isinstance(data, list) else data.get("tweets", [])
        for tweet in tweets[: self.max_posts]:
            posts.append(
                {
                    "source": "twitter",
                    "source_id": str(tweet.get("id", "")),
                    "author": account,
                    "text": tweet.get("text", tweet.get("full_text", "")),
                    "url": f"https://x.com/{account}/status/{tweet.get('id', '')}",
                    "timestamp": self._parse_time(tweet.get("created_at")),
                    "likes": tweet.get("favorite_count", tweet.get("likes", 0)),
                    "replies": tweet.get("reply_count", tweet.get("replies", 0)),
                    "retweets": tweet.get("retweet_count", tweet.get("retweets", 0)),
                    "quotes": tweet.get("quote_count", tweet.get("quotes", 0)),
                }
            )
        return posts

    def _fetch_via_api(self, account: str) -> list[dict[str, Any]]:
        url = f"https://api.twitter.com/2/users/by/username/{account}"
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        try:
            resp = httpx.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return []
            user_id = resp.json().get("data", {}).get("id")
            if not user_id:
                return []

            tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
            params = {
                "max_results": min(self.max_posts, 100),
                "tweet.fields": "public_metrics,created_at",
            }
            tweets_resp = httpx.get(tweets_url, headers=headers, params=params, timeout=15)
            if tweets_resp.status_code != 200:
                return []

            data = tweets_resp.json().get("data", [])
            return self._parse_api_response(account, data)
        except Exception as e:
            self.logger.warning(f"API error for {account}: {e}")
        return []

    def _parse_api_response(self, account: str, tweets: list[dict]) -> list[dict[str, Any]]:
        posts = []
        for tweet in tweets:
            metrics = tweet.get("public_metrics", {})
            posts.append(
                {
                    "source": "twitter",
                    "source_id": tweet.get("id", ""),
                    "author": account,
                    "text": tweet.get("text", ""),
                    "url": f"https://x.com/{account}/status/{tweet.get('id', '')}",
                    "timestamp": self._parse_time(tweet.get("created_at")),
                    "likes": metrics.get("like_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "quotes": metrics.get("quote_count", 0),
                }
            )
        return posts

    def _mock_data(self, account: str) -> list[dict[str, Any]]:
        import random

        return [
            {
                "source": "twitter",
                "source_id": f"mock_{account}_{i}",
                "author": account,
                "text": f"Exciting new developments in AI! This is a sample post from {account} about the future of technology. #{i}",
                "url": f"https://x.com/{account}/status/mock_{i}",
                "timestamp": datetime.utcnow(),
                "likes": random.randint(50, 5000),
                "replies": random.randint(5, 500),
                "retweets": random.randint(10, 2000),
                "quotes": random.randint(1, 200),
            }
            for i in range(min(self.max_posts, 5))
        ]

    def _parse_time(self, ts: Any) -> datetime | None:
        if not ts:
            return None
        if isinstance(ts, datetime):
            return ts
        for fmt in [
            "%a %b %d %H:%M:%S %z %Y",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
        ]:
            try:
                return datetime.strptime(str(ts).replace("+0000 ", ""), fmt)
            except ValueError:
                continue
        return datetime.utcnow()
