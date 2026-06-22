from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from .models import Metric, Post, Report, Trend, init_db


class Database:
    def __init__(self, database_url: str):
        engine, self.Session = init_db(database_url)

    def get_session(self) -> DBSession:
        return self.Session()

    # --- Post operations ---

    def save_post(self, post_data: dict[str, Any]) -> Post | None:
        with self.get_session() as session:
            existing = (
                session.query(Post)
                .filter(
                    Post.source == post_data.get("source"),
                    Post.source_id == post_data.get("source_id"),
                )
                .first()
            )
            if existing:
                existing.likes = post_data.get("likes", existing.likes)
                existing.replies = post_data.get("replies", existing.replies)
                existing.retweets = post_data.get("retweets", existing.retweets)
                existing.quotes = post_data.get("quotes", existing.quotes)
                existing.stars = post_data.get("stars", existing.stars)
                existing.votes = post_data.get("votes", existing.votes)
                existing.score = post_data.get("score", existing.score)
                existing.engagement_score = post_data.get("engagement_score", existing.engagement_score)
                existing.category = post_data.get("category", existing.category)
                existing.summary = post_data.get("summary", existing.summary)
                existing.is_duplicate = post_data.get("is_duplicate", existing.is_duplicate)
                session.commit()
                return existing

            post = Post(**{k: v for k, v in post_data.items() if hasattr(Post, k)})
            session.add(post)
            session.commit()
            session.refresh(post)
            return post

    def get_posts_by_source(self, source: str, limit: int = 100) -> list[Post]:
        with self.get_session() as session:
            return (
                session.query(Post)
                .filter(Post.source == source, Post.is_duplicate == 0)
                .order_by(Post.engagement_score.desc())
                .limit(limit)
                .all()
            )

    def get_top_posts(self, limit: int = 10, since: datetime | None = None) -> list[Post]:
        with self.get_session() as session:
            query = session.query(Post).filter(Post.is_duplicate == 0)
            if since:
                query = query.filter(Post.timestamp >= since)
            return query.order_by(Post.engagement_score.desc()).limit(limit).all()

    def get_posts_since(self, since: datetime, limit: int = 500) -> list[Post]:
        with self.get_session() as session:
            return (
                session.query(Post)
                .filter(Post.timestamp >= since, Post.is_duplicate == 0)
                .order_by(Post.engagement_score.desc())
                .limit(limit)
                .all()
            )

    def get_all_posts_since(self, since: datetime) -> list[Post]:
        with self.get_session() as session:
            return (
                session.query(Post)
                .filter(Post.timestamp >= since, Post.is_duplicate == 0)
                .all()
            )

    def mark_duplicates(self, source_ids: list[str]) -> None:
        with self.get_session() as session:
            session.query(Post).filter(
                Post.source_id.in_(source_ids), Post.is_duplicate == 0
            ).update({Post.is_duplicate: 1})
            session.commit()

    def get_post_count_since(self, since: datetime) -> int:
        with self.get_session() as session:
            return (
                session.query(func.count(Post.id))
                .filter(Post.timestamp >= since, Post.is_duplicate == 0)
                .scalar()
                or 0
            )

    # --- Report operations ---

    def save_report(self, report_data: dict[str, Any]) -> Report:
        with self.get_session() as session:
            report = Report(**{k: v for k, v in report_data.items() if hasattr(Report, k)})
            session.add(report)
            session.commit()
            session.refresh(report)
            return report

    def get_latest_report(self, report_type: str = "daily") -> Report | None:
        with self.get_session() as session:
            return (
                session.query(Report)
                .filter(Report.report_type == report_type)
                .order_by(Report.created_at.desc())
                .first()
            )

    def get_reports_since(self, since: datetime, report_type: str | None = None) -> list[Report]:
        with self.get_session() as session:
            query = session.query(Report).filter(Report.created_at >= since)
            if report_type:
                query = query.filter(Report.report_type == report_type)
            return query.order_by(Report.created_at.desc()).all()

    def has_report_today(self, report_type: str = "daily") -> bool:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        with self.get_session() as session:
            return (
                session.query(Report)
                .filter(Report.report_type == report_type, Report.created_at >= today_start)
                .first()
                is not None
            )

    def mark_delivered(self, report_id: int, channel: str) -> None:
        with self.get_session() as session:
            report = session.query(Report).filter(Report.id == report_id).first()
            if report:
                if channel == "telegram":
                    report.delivered_telegram = 1
                elif channel == "email":
                    report.delivered_email = 1
                session.commit()

    # --- Trend operations ---

    def save_trend(self, trend_data: dict[str, Any]) -> Trend:
        with self.get_session() as session:
            existing = (
                session.query(Trend)
                .filter(Trend.name == trend_data.get("name"), Trend.report_id == trend_data.get("report_id"))
                .first()
            )
            if existing:
                existing.frequency = trend_data.get("frequency", existing.frequency)
                existing.description = trend_data.get("description", existing.description)
                existing.last_seen = datetime.utcnow()
                session.commit()
                return existing

            trend = Trend(**{k: v for k, v in trend_data.items() if hasattr(Trend, k)})
            session.add(trend)
            session.commit()
            session.refresh(trend)
            return trend

    def get_trends_since(self, since: datetime) -> list[Trend]:
        with self.get_session() as session:
            return (
                session.query(Trend)
                .filter(Trend.last_seen >= since)
                .order_by(Trend.frequency.desc())
                .all()
            )

    def get_aggregated_trends(self, since: datetime) -> list[dict[str, Any]]:
        with self.get_session() as session:
            results = (
                session.query(
                    Trend.name,
                    func.sum(Trend.frequency).label("total_freq"),
                    func.count(Trend.id).label("report_count"),
                )
                .filter(Trend.last_seen >= since)
                .group_by(Trend.name)
                .order_by(func.sum(Trend.frequency).desc())
                .limit(20)
                .all()
            )
            return [
                {"name": r[0], "total_frequency": r[1], "report_count": r[2]} for r in results
            ]

    # --- Metric operations ---

    def save_metric(self, metric_data: dict[str, Any]) -> Metric:
        with self.get_session() as session:
            metric = Metric(**{k: v for k, v in metric_data.items() if hasattr(Metric, k)})
            session.add(metric)
            session.commit()
            session.refresh(metric)
            return metric

    def get_metrics(self, metric_name: str, since: datetime) -> list[Metric]:
        with self.get_session() as session:
            return (
                session.query(Metric)
                .filter(Metric.metric_name == metric_name, Metric.recorded_at >= since)
                .order_by(Metric.recorded_at.asc())
                .all()
            )

    def get_avg_engagement_since(self, since: datetime) -> float:
        with self.get_session() as session:
            result = (
                session.query(func.avg(Post.engagement_score))
                .filter(Post.timestamp >= since, Post.is_duplicate == 0)
                .scalar()
            )
            return float(result) if result else 0.0

    def get_top_category_since(self, since: datetime) -> str | None:
        with self.get_session() as session:
            result = (
                session.query(Post.category, func.count(Post.id).label("cnt"))
                .filter(Post.timestamp >= since, Post.is_duplicate == 0, Post.category.isnot(None))
                .group_by(Post.category)
                .order_by(func.count(Post.id).desc())
                .first()
            )
            return result[0] if result else None
