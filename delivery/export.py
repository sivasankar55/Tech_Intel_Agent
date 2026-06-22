from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.logger import setup_logger


class Exporter:
    def __init__(self, export_dir: str = "exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger("Exporter")

    def export_csv(self, posts: list[dict[str, Any]], filename: str | None = None) -> str | None:
        if not filename:
            filename = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

        filepath = self.export_dir / filename
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "source", "author", "title", "text", "url", "timestamp",
                        "likes", "replies", "retweets", "quotes", "stars", "votes",
                        "engagement_score", "category", "summary", "signal",
                    ],
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(posts)

            self.logger.info(f"CSV exported: {filepath}")
            return str(filepath)
        except Exception as e:
            self.logger.error(f"CSV export failed: {e}")
            return None

    def export_pdf(self, html_content: str, filename: str | None = None) -> str | None:
        if not filename:
            filename = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

        filepath = self.export_dir / filename
        try:
            from weasyprint import HTML

            html_str = f"""
            <html>
            <head><meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; }}
                h1 {{ color: #4f46e5; }}
                h2 {{ color: #374151; border-bottom: 1px solid #ddd; }}
                blockquote {{ border-left: 3px solid #4f46e5; padding: 10px; background: #f9fafb; }}
            </style>
            </head>
            <body>{html_content}</body>
            </html>
            """
            HTML(string=html_str).write_pdf(filepath)
            self.logger.info(f"PDF exported: {filepath}")
            return str(filepath)
        except ImportError:
            self.logger.warning("WeasyPrint not installed, skipping PDF export")
            return None
        except Exception as e:
            self.logger.warning(f"PDF export failed: {e}")
            return None

    def export_report_json(self, report_data: dict[str, Any]) -> str | None:
        import json

        filename = f"report_{report_data.get('report_type', 'daily')}_{datetime.utcnow().strftime('%Y%m%d')}.json"
        filepath = self.export_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, default=str)
            return str(filepath)
        except Exception as e:
            self.logger.error(f"JSON export failed: {e}")
            return None
