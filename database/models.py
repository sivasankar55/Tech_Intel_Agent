from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)  # twitter, github, producthunt, hackernews, news
    source_id = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    title = Column(String(500), nullable=True)
    text = Column(Text, nullable=True)
    url = Column(String(1000), nullable=True)
    timestamp = Column(DateTime, nullable=True)
    likes = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    retweets = Column(Integer, default=0)
    quotes = Column(Integer, default=0)
    stars = Column(Integer, default=0)
    votes = Column(Integer, default=0)
    score = Column(Float, default=0)
    engagement_score = Column(Float, default=0.0)
    category = Column(String(100), nullable=True, index=True)
    summary = Column(Text, nullable=True)
    is_duplicate = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(50), nullable=False, index=True)  # daily, weekly, monthly
    title = Column(String(500), nullable=False)
    markdown_content = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    total_posts = Column(Integer, default=0)
    avg_engagement = Column(Float, default=0.0)
    top_category = Column(String(100), nullable=True)
    delivered_telegram = Column(Integer, default=0)
    delivered_email = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True)
    frequency = Column(Integer, default=1)
    description = Column(Text, nullable=True)
    report_id = Column(Integer, nullable=True)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(255), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    category = Column(String(100), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    report_id = Column(Integer, nullable=True)


def init_db(database_url: str) -> tuple:
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session
