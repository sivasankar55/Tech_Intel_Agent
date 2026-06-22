from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware

    _has_fastapi = True
except ImportError:
    _has_fastapi = False

from utils.logger import setup_logger


class DashboardAPI:
    def __init__(self, db: Any, config: Any):
        self.db = db
        self.config = config
        self.logger = setup_logger("DashboardAPI")
        self.app = None

    def create_app(self):
        if not _has_fastapi:
            self.logger.warning("FastAPI not installed, dashboard unavailable")
            return None

        app = FastAPI(title="AI Tech Intelligence API", version="1.0.0")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/api/health")
        def health():
            return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

        @app.get("/api/posts/top")
        def get_top_posts(limit: int = Query(10, ge=1, le=100), hours: int = Query(24, ge=1, le=168)):
            since = datetime.utcnow() - timedelta(hours=hours)
            posts = self.db.get_top_posts(limit=limit, since=since)
            return [
                {
                    "id": p.id,
                    "source": p.source,
                    "author": p.author,
                    "title": p.title,
                    "text": p.text[:300] if p.text else "",
                    "url": p.url,
                    "engagement_score": p.engagement_score,
                    "category": p.category,
                    "summary": p.summary,
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                }
                for p in posts
            ]

        @app.get("/api/posts/by-source")
        def get_posts_by_source(source: str, limit: int = Query(50, ge=1, le=200)):
            posts = self.db.get_posts_by_source(source, limit=limit)
            return [
                {
                    "id": p.id,
                    "author": p.author,
                    "title": p.title,
                    "text": p.text[:300] if p.text else "",
                    "url": p.url,
                    "engagement_score": p.engagement_score,
                    "category": p.category,
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                }
                for p in posts
            ]

        @app.get("/api/reports/latest")
        def get_latest_report(report_type: str = Query("daily", pattern="^(daily|weekly|monthly)$")):
            report = self.db.get_latest_report(report_type)
            if not report:
                raise HTTPException(status_code=404, detail="No report found")
            return {
                "id": report.id,
                "title": report.title,
                "report_type": report.report_type,
                "summary": report.summary,
                "markdown": report.markdown_content,
                "html": report.html_content,
                "total_posts": report.total_posts,
                "avg_engagement": report.avg_engagement,
                "top_category": report.top_category,
                "created_at": report.created_at.isoformat(),
            }

        @app.get("/api/reports/history")
        def get_report_history(report_type: str = Query("daily", pattern="^(daily|weekly|monthly)$"), limit: int = Query(30, ge=1, le=365)):
            since = datetime.utcnow() - timedelta(days=limit)
            reports = self.db.get_reports_since(since, report_type=report_type)
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "summary": r.summary[:200] if r.summary else "",
                    "total_posts": r.total_posts,
                    "avg_engagement": r.avg_engagement,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reports
            ]

        @app.get("/api/trends")
        def get_trends(hours: int = Query(168, ge=1, le=720)):
            since = datetime.utcnow() - timedelta(hours=hours)
            trends = self.db.get_aggregated_trends(since)
            return trends

        @app.get("/api/metrics")
        def get_metrics(metric_name: str, hours: int = Query(168, ge=1, le=720)):
            since = datetime.utcnow() - timedelta(hours=hours)
            metrics = self.db.get_metrics(metric_name, since)
            return [
                {
                    "value": m.metric_value,
                    "recorded_at": m.recorded_at.isoformat(),
                }
                for m in metrics
            ]

        @app.get("/api/summary")
        def get_summary(hours: int = Query(24, ge=1, le=168)):
            since = datetime.utcnow() - timedelta(hours=hours)
            posts_count = self.db.get_post_count_since(since)
            avg_eng = self.db.get_avg_engagement_since(since)
            top_cat = self.db.get_top_category_since(since)
            top_posts = self.db.get_top_posts(limit=5, since=since)
            trends = self.db.get_aggregated_trends(since)

            return {
                "period_hours": hours,
                "total_posts": posts_count,
                "avg_engagement": round(avg_eng, 2),
                "top_category": top_cat,
                "top_posts": [
                    {
                        "author": p.author,
                        "title": p.title,
                        "engagement_score": p.engagement_score,
                        "url": p.url,
                    }
                    for p in top_posts
                ],
                "top_trends": trends[:10],
            }

        self.app = app
        return app

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        if not self.app:
            self.app = self.create_app()
        if self.app:
            import uvicorn
            self.logger.info(f"Starting dashboard API on {host}:{port}")
            uvicorn.run(self.app, host=host, port=port)
