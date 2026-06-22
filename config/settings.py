from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class TwitterConfig(BaseModel):
    accounts: list[str] = Field(default_factory=lambda: ["OpenAI", "AnthropicAI"])
    max_posts_per_account: int = 20


class GitHubConfig(BaseModel):
    since: str = "daily"
    topics: list[str] = Field(default_factory=lambda: ["ai", "agents", "mcp"])
    max_repos_per_topic: int = 10


class ProductHuntConfig(BaseModel):
    topics: list[str] = Field(default_factory=lambda: ["artificial-intelligence", "developer-tools"])
    max_products: int = 20


class HackerNewsConfig(BaseModel):
    topics: list[str] = Field(default_factory=lambda: ["ai", "startup", "engineering"])
    max_stories: int = 30


class NewsSource(BaseModel):
    name: str
    type: str = "rss"
    url: str


class NewsConfig(BaseModel):
    sources: list[NewsSource] = Field(default_factory=list)
    max_articles: int = 20


class EngagementWeights(BaseModel):
    likes: float = 1.0
    replies: float = 3.0
    retweets: float = 2.0
    quotes: float = 4.0
    stars: float = 1.0
    votes: float = 2.0
    score: float = 1.0


class EngagementConfig(BaseModel):
    weights: EngagementWeights = EngagementWeights()
    min_score: float = 10


class FilteringConfig(BaseModel):
    min_text_length: int = 50
    exclude_keywords: list[str] = Field(default_factory=lambda: ["spam", "click here"])
    categories: list[str] = Field(
        default_factory=lambda: [
            "AI News", "AI Tools", "Startup News", "Open Source Projects",
            "Coding Tools", "Agent Frameworks", "Automation Platforms", "Research",
        ]
    )


class AIAnalysisConfig(BaseModel):
    enabled: bool = True
    model: str = "gemini-2.0-flash"
    max_tokens: int = 4096


class ReportingConfig(BaseModel):
    max_top_posts: int = 10
    max_trending_repos: int = 10
    max_tools: int = 10
    include_executive_summary: bool = True
    include_top_posts: bool = True
    include_ai_news: bool = True
    include_tools: bool = True
    include_repos: bool = True
    include_trends: bool = True
    include_opportunities: bool = True
    include_takeaways: bool = True


class TelegramDelivery(BaseModel):
    enabled: bool = True
    chunk_size: int = 4000


class EmailDelivery(BaseModel):
    enabled: bool = True


class DeliveryConfig(BaseModel):
    telegram: TelegramDelivery = TelegramDelivery()
    email: EmailDelivery = EmailDelivery()


class ScheduleConfig(BaseModel):
    time: str = "08:00"
    timezone: str = "UTC"


class StorageConfig(BaseModel):
    database: str = "sqlite:///data/tech_intel.db"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/agent.log"


class Config(BaseModel):
    schedule: ScheduleConfig = ScheduleConfig()
    twitter: TwitterConfig = TwitterConfig()
    github: GitHubConfig = GitHubConfig()
    producthunt: ProductHuntConfig = ProductHuntConfig()
    hackernews: HackerNewsConfig = HackerNewsConfig()
    news: NewsConfig = NewsConfig()
    engagement: EngagementConfig = EngagementConfig()
    filtering: FilteringConfig = FilteringConfig()
    ai_analysis: AIAnalysisConfig = AIAnalysisConfig()
    reporting: ReportingConfig = ReportingConfig()
    delivery: DeliveryConfig = DeliveryConfig()
    storage: StorageConfig = StorageConfig()
    logging: LoggingConfig = LoggingConfig()

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    @property
    def telegram_bot_token(self) -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", "")

    @property
    def telegram_chat_id(self) -> str:
        return os.getenv("TELEGRAM_CHAT_ID", "")

    @property
    def email_host(self) -> str:
        return os.getenv("EMAIL_HOST", "smtp.gmail.com")

    @property
    def email_port(self) -> int:
        return int(os.getenv("EMAIL_PORT", "587"))

    @property
    def email_user(self) -> str:
        return os.getenv("EMAIL_USER", "")

    @property
    def email_password(self) -> str:
        return os.getenv("EMAIL_PASSWORD", "")

    @property
    def email_to(self) -> str:
        return os.getenv("EMAIL_TO", "")

    @property
    def firecrawl_api_key(self) -> str:
        return os.getenv("FIRECRAWL_API_KEY", "")

    @property
    def scrapingdog_api_key(self) -> str:
        return os.getenv("SCRAPINGDOG_API_KEY", "")

    @property
    def twitter_bearer_token(self) -> str:
        return os.getenv("TWITTER_BEARER_TOKEN", "")

    @property
    def github_token(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def producthunt_token(self) -> str:
        return os.getenv("PRODUCTHUNT_DEVELOPER_TOKEN", "")


def load_config(path: str | Path | None = None) -> Config:
    load_dotenv()

    if path is None:
        path = Path(__file__).parent.parent / "config.yaml"

    path = Path(path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return Config(**data)

    return Config()
