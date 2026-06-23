#!/usr/bin/env python3
"""
Daily AI & Tech Intelligence Agent
Automatically collects, analyzes, and delivers intelligence reports.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from analyzers.ai_analyzer import AIAnalyzer
from analyzers.dedup import Deduplicator
from analyzers.engagement import EngagementScorer
from analyzers.trends import TrendDetector
from collectors.github import GitHubCollector
from collectors.hackernews import HackerNewsCollector
from collectors.news import NewsCollector
from collectors.producthunt import ProductHuntCollector
from collectors.twitter import TwitterCollector
from config.settings import Config, load_config
from database.storage import Database
from delivery.email import EmailDeliverer
from delivery.export import Exporter
from delivery.telegram import TelegramDeliverer
from reporting.report_generator import ReportGenerator
from utils.logger import setup_logger


class TechIntelAgent:
    def __init__(self, config_path: str | None = None):
        self.config: Config = load_config(config_path)
        self.logger = setup_logger(
            "TechIntelAgent",
            level=self.config.logging.level,
            log_file=self.config.logging.file,
        )
        self.db = Database(self.config.storage.database)
        self.report_gen = ReportGenerator(self.config)
        self.scorer = EngagementScorer(self.config.engagement.weights.model_dump())
        self.dedup = Deduplicator()
        self.trend_detector = TrendDetector()
        self.ai_analyzer = AIAnalyzer(
            api_key=self.config.gemini_api_key,
            model=self.config.ai_analysis.model,
            max_tokens=self.config.ai_analysis.max_tokens,
        )
        self.telegram = TelegramDeliverer(
            bot_token=self.config.telegram_bot_token,
            chat_id=self.config.telegram_chat_id,
            chunk_size=self.config.delivery.telegram.chunk_size,
        )
        self.email = EmailDeliverer(
            host=self.config.email_host,
            port=self.config.email_port,
            user=self.config.email_user,
            password=self.config.email_password,
            to_addr=self.config.email_to,
        )
        self.exporter = Exporter()
        self.scheduler = BackgroundScheduler()

        self.logger.info("Tech Intelligence Agent initialized")

    def run_once(self):
        self.logger.info("=== Starting Intelligence Collection ===")

        if self.db.has_report_today("daily"):
            self.logger.info("Daily report already generated today, skipping")
            return

        all_posts = []
        all_trends = []

        collectors = [
            ("Twitter", TwitterCollector(self.config, self.db)),
            ("GitHub", GitHubCollector(self.config, self.db)),
            ("Product Hunt", ProductHuntCollector(self.config, self.db)),
            ("Hacker News", HackerNewsCollector(self.config, self.db)),
            ("News", NewsCollector(self.config, self.db)),
        ]

        for name, collector in collectors:
            self.logger.info(f"Running {name} collector...")
            posts = collector.run()
            for p in posts:
                p["source"] = name.lower().replace(" ", "_")
            all_posts.extend(posts)

        self.logger.info(f"Total raw posts collected: {len(all_posts)}")

        all_posts = self.dedup.deduplicate(all_posts)

        all_posts = self.scorer.score_all(all_posts)

        all_posts = self.ai_analyzer.analyze_posts(all_posts)

        filtered = [
            p
            for p in all_posts
            if p.get("is_duplicate") != 1
            and p.get("engagement_score", 0) >= self.config.engagement.min_score
            and len(p.get("text", "") or p.get("title", "") or "") >= self.config.filtering.min_text_length
        ]

        self.logger.info(f"Posts after filtering: {len(filtered)}")

        for post in filtered:
            self.db.save_post(post)

        all_trends = self.trend_detector.detect(filtered)

        top_posts = filtered[: self.config.reporting.max_top_posts]
        repos = [p for p in filtered if p.get("source") == "github"][: self.config.reporting.max_trending_repos]
        tools = [p for p in filtered if p.get("source") == "producthunt"][: self.config.reporting.max_tools]

        executive_summary = ""
        if self.config.ai_analysis.enabled and self.config.gemini_api_key:
            report_context = f"Total posts: {len(filtered)}\nTop score: {filtered[0].get('engagement_score', 0) if filtered else 0}\nTrends: {[t['name'] for t in all_trends[:10]]}"
            executive_summary = self.ai_analyzer.generate_report_summary(report_context)

        report_data = self.report_gen.generate_daily(
            posts=filtered,
            trends=all_trends,
            top_posts=top_posts,
            repos=repos,
            tools=tools,
            executive_summary=executive_summary,
        )

        report = self.db.save_report(report_data)

        for trend_data in all_trends:
            trend_data["report_id"] = report.id
            trend_data["first_seen"] = trend_data.get("first_seen", datetime.now(timezone.utc))
            trend_data["last_seen"] = trend_data.get("last_seen", datetime.now(timezone.utc))
            self.db.save_trend(trend_data)

        metric_data = {
            "metric_name": "avg_engagement",
            "metric_value": report_data.get("avg_engagement", 0),
            "category": "engagement",
            "report_id": report.id,
        }
        self.db.save_metric(metric_data)

        self.exporter.export_report_json(report_data)
        self.exporter.export_csv(filtered)

        if report_data.get("html_content"):
            pdf_path = self.exporter.export_pdf(report_data["html_content"])
            if pdf_path:
                self.logger.info(f"PDF exported: {pdf_path}")

        delivery_results = {}

        if self.config.delivery.telegram.enabled:
            self.logger.info("Delivering to Telegram...")
            tg_ok = self.telegram.send(report_data["markdown_content"])
            if tg_ok:
                self.db.mark_delivered(report.id, "telegram")
            delivery_results["telegram"] = tg_ok

        if self.config.delivery.email.enabled:
            self.logger.info("Delivering via Email...")
            email_ok = self.email.send(
                subject=report_data["title"],
                html_content=report_data.get("html_content", ""),
            )
            if email_ok:
                self.db.mark_delivered(report.id, "email")
            delivery_results["email"] = email_ok

        self.logger.info(f"=== Collection Complete ===")
        self.logger.info(f"Posts: {len(filtered)} | Trends: {len(all_trends)} | Report ID: {report.id}")
        self.logger.info(f"Deliveries: {delivery_results}")

    def check_weekly_report(self):
        if datetime.now(timezone.utc).weekday() != 0:
            return
        self.logger.info("Generating weekly report...")
        since = datetime.now(timezone.utc) - timedelta(days=7)
        daily_reports = self.db.get_reports_since(since, report_type="daily")
        if daily_reports:
            report_data = self.report_gen.generate_weekly(
                [{"title": r.title, "summary": r.summary, "total_posts": r.total_posts, "avg_engagement": r.avg_engagement} for r in daily_reports]
            )
            report = self.db.save_report(report_data)
            if self.config.delivery.telegram.enabled:
                self.telegram.send(report_data["markdown_content"])
            if self.config.delivery.email.enabled:
                self.email.send(subject=report_data["title"], html_content=report_data.get("html_content", ""))

    def check_monthly_report(self):
        if datetime.now(timezone.utc).day != 1:
            return
        self.logger.info("Generating monthly report...")
        since = datetime.now(timezone.utc) - timedelta(days=30)
        daily_reports = self.db.get_reports_since(since, report_type="daily")
        if daily_reports:
            report_data = self.report_gen.generate_monthly(
                [{"title": r.title, "summary": r.summary, "total_posts": r.total_posts, "avg_engagement": r.avg_engagement} for r in daily_reports]
            )
            report = self.db.save_report(report_data)

    def run_scheduled(self):
        schedule = self.config.schedule
        hour, minute = map(int, schedule.time.split(":"))

        self.scheduler.add_job(
            self.run_once,
            CronTrigger(hour=hour, minute=minute, timezone=schedule.timezone),
            id="daily_intel",
            name="Daily Intelligence Collection",
        )

        self.scheduler.add_job(
            self.check_weekly_report,
            CronTrigger(hour=hour, minute=minute + 5, day_of_week="mon", timezone=schedule.timezone),
            id="weekly_report",
            name="Weekly Report Generation",
        )

        self.scheduler.add_job(
            self.check_monthly_report,
            CronTrigger(hour=hour, minute=minute + 10, day=1, timezone=schedule.timezone),
            id="monthly_report",
            name="Monthly Report Generation",
        )

        self.logger.info(f"Scheduler started. Next daily run at {schedule.time} {schedule.timezone}")
        self.logger.info("Weekly: Monday after daily | Monthly: 1st after daily")

        self.scheduler.start()

        try:
            from datetime import timezone
            self.logger.info("Agent running. Press Ctrl+C to stop.")
            import time
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Shutting down...")
            self.scheduler.shutdown()

    def run_dashboard(self, host: str = "0.0.0.0", port: int = 8000):
        from dashboard.api import DashboardAPI
        api = DashboardAPI(self.db, self.config)
        api.create_app()
        api.run(host=host, port=port)

    def run_serve(self, host: str = "0.0.0.0", port: int = 8000):
        from dashboard.api import DashboardAPI

        self.scheduler = BackgroundScheduler()
        schedule = self.config.schedule
        hour, minute = map(int, schedule.time.split(":"))

        self.scheduler.add_job(
            self.run_once,
            CronTrigger(hour=hour, minute=minute, timezone=schedule.timezone),
            id="daily_intel",
        )
        self.scheduler.add_job(
            self.check_weekly_report,
            CronTrigger(hour=hour, minute=minute + 5, day_of_week="mon", timezone=schedule.timezone),
            id="weekly_report",
        )
        self.scheduler.add_job(
            self.check_monthly_report,
            CronTrigger(hour=hour, minute=minute + 10, day=1, timezone=schedule.timezone),
            id="monthly_report",
        )
        self.scheduler.start()
        self.logger.info(f"Scheduler started. Next daily run at {schedule.time} {schedule.timezone}")

        api = DashboardAPI(self.db, self.config)
        api.create_app()
        api.run(host=host, port=port)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Daily AI & Tech Intelligence Agent")
    parser.add_argument("--config", "-c", help="Path to config.yaml", default=None)
    parser.add_argument("--run-once", "-r", action="store_true", help="Run collection once and exit")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run as scheduled daemon")
    parser.add_argument("--dashboard", action="store_true", help="Start dashboard API only")
    parser.add_argument("--serve", "-s", action="store_true", help="Run daemon + dashboard together")
    parser.add_argument("--host", default="0.0.0.0", help="Dashboard host")
    parser.add_argument("--port", type=int, default=8000, help="Dashboard port")

    args = parser.parse_args()

    agent = TechIntelAgent(config_path=args.config)

    if args.run_once:
        agent.run_once()
    elif args.dashboard:
        agent.run_dashboard(host=args.host, port=args.port)
    elif args.serve:
        agent.run_serve(host=args.host, port=args.port)
    else:
        agent.run_scheduled()


if __name__ == "__main__":
    main()
