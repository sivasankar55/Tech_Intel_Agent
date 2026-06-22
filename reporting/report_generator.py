from __future__ import annotations

from datetime import datetime
from typing import Any

from utils.logger import setup_logger


class ReportGenerator:
    def __init__(self, config: Any):
        self.config = config
        self.logger = setup_logger("ReportGenerator")

    def generate_daily(
        self,
        posts: list[dict[str, Any]],
        trends: list[dict[str, Any]],
        top_posts: list[dict[str, Any]],
        repos: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        executive_summary: str = "",
    ) -> dict[str, Any]:
        cfg = self.config.reporting
        sections = []

        # Title
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        title = f"Daily AI & Tech Intelligence Report — {date_str}"
        sections.append(f"# {title}\n")

        # Executive Summary
        if cfg.include_executive_summary and executive_summary:
            sections.append("## Executive Summary\n")
            sections.append(executive_summary + "\n")

        # Top 10 Posts
        if cfg.include_top_posts and top_posts:
            sections.append("## Top 10 Highest Engagement Posts\n")
            for i, post in enumerate(top_posts[: cfg.max_top_posts], 1):
                author = post.get("author", "Unknown")
                score = post.get("engagement_score", 0)
                summary = post.get("summary") or post.get("text", "")[:200]
                url = post.get("url", "")
                why = self._why_it_mattered(post)
                sections.append(
                    f"### {i}. {author} — Score: {score:.0f}\n"
                    f"> {summary}\n\n"
                    f"[View Post]({url})\n\n"
                    f"*Why it mattered:* {why}\n"
                )

        # AI News
        if cfg.include_ai_news:
            news_posts = [p for p in posts if p.get("category") == "AI News"][:5]
            if news_posts:
                sections.append("## Important AI News\n")
                for p in news_posts:
                    title_t = p.get("title") or p.get("text", "")[:100]
                    sections.append(f"- **{title_t}** — {p.get('summary', '')[:150]}")
                sections.append("")

        # New AI Tools
        if cfg.include_tools and tools:
            sections.append("## New AI Tools & Products\n")
            for tool in tools[: cfg.max_tools]:
                name = tool.get("title", tool.get("name", "Unknown"))
                desc = tool.get("text", "") or tool.get("tagline", "")
                url = tool.get("url", "")
                votes = tool.get("votes", 0)
                sections.append(f"- **[{name}]({url})** — {desc[:150]} (Votes: {votes})")
            sections.append("")

        # Trending GitHub Repos
        if cfg.include_repos and repos:
            sections.append("## Trending GitHub Repositories\n")
            for repo in repos[: cfg.max_trending_repos]:
                name = repo.get("title", repo.get("name", "Unknown"))
                desc = repo.get("text", "")[:150]
                url = repo.get("url", "")
                stars = repo.get("stars", 0)
                sections.append(f"- **[{name}]({url})** ⭐ {stars:,} — {desc}")
            sections.append("")

        # Emerging Trends
        if cfg.include_trends and trends:
            sections.append("## Emerging Trends\n")
            seen: set[str] = set()
            for t in trends:
                name = t.get("name", "")
                if name.lower() in seen:
                    continue
                seen.add(name.lower())
                cat = t.get("category", "")
                freq = t.get("frequency", 1)
                sections.append(f"- **{name}** ({cat}) — Mentioned {freq}x")
            sections.append("")

        # Opportunities
        if cfg.include_opportunities:
            sections.append("## Opportunities\n")
            opportunities = self._generate_opportunities(posts, trends, tools)
            for opp in opportunities:
                sections.append(f"- **{opp['title']}** — {opp['description']}")
            sections.append("")

        # Key Takeaways
        if cfg.include_takeaways:
            sections.append("## Key Takeaways\n")
            takeaways = self._generate_takeaways(posts, trends)
            for t in takeaways:
                sections.append(f"- {t}")
            sections.append("")

        markdown_content = "\n".join(sections)

        return {
            "report_type": "daily",
            "title": title,
            "markdown_content": markdown_content,
            "html_content": self._markdown_to_html(markdown_content),
            "summary": executive_summary[:500] if executive_summary else "",
            "period_start": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            "period_end": datetime.utcnow(),
            "total_posts": len(posts),
            "avg_engagement": (
                sum(p.get("engagement_score", 0) for p in posts if p.get("engagement_score"))
                / max(len([p for p in posts if p.get("engagement_score")]), 1)
            ),
            "top_category": self._get_top_category(posts),
        }

    def generate_weekly(self, daily_reports: list[dict]) -> dict[str, Any]:
        week_end = datetime.utcnow()
        week_start = week_end.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = week_start.replace(day=week_start.day - 7)

        sections = [f"# Weekly AI & Tech Intelligence Report\n"]
        sections.append(f"Period: {week_start.strftime('%B %d')} — {week_end.strftime('%B %d, %Y')}\n")

        if daily_reports:
            total_posts = sum(r.get("total_posts", 0) for r in daily_reports)
            avg_eng = sum(r.get("avg_engagement", 0) for r in daily_reports) / max(len(daily_reports), 1)
            sections.append(f"**Summary:** {len(daily_reports)} reports, {total_posts} posts collected, average engagement: {avg_eng:.1f}\n")

        sections.append("### Daily Snapshots\n")
        for report in daily_reports:
            date_str = report.get("title", "").split("—")[-1].strip() if "—" in report.get("title", "") else "Unknown"
            sections.append(f"- **{date_str}** — {report.get('summary', '')[:200]}")
        sections.append("")

        markdown = "\n".join(sections)
        return {
            "report_type": "weekly",
            "title": f"Weekly AI & Tech Intelligence Report — {week_start.strftime('%b %d')} to {week_end.strftime('%b %d, %Y')}",
            "markdown_content": markdown,
            "html_content": self._markdown_to_html(markdown),
            "period_start": week_start,
            "period_end": week_end,
        }

    def generate_monthly(self, daily_reports: list[dict]) -> dict[str, Any]:
        month_end = datetime.utcnow()
        month_start = month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        sections = [f"# Monthly AI & Tech Intelligence Report\n"]
        sections.append(f"Period: {month_start.strftime('%B %Y')}\n")

        if daily_reports:
            total_posts = sum(r.get("total_posts", 0) for r in daily_reports)
            sections.append(f"**Summary:** {len(daily_reports)} reports, {total_posts} posts analyzed.\n")

        markdown = "\n".join(sections)
        return {
            "report_type": "monthly",
            "title": f"Monthly AI & Tech Intelligence Report — {month_start.strftime('%B %Y')}",
            "markdown_content": markdown,
            "html_content": self._markdown_to_html(markdown),
            "period_start": month_start,
            "period_end": month_end,
        }

    def _why_it_mattered(self, post: dict) -> str:
        source = post.get("source", "")
        author = post.get("author", "")
        text = (post.get("text", "") or post.get("title", "") or "").lower()
        score = post.get("engagement_score", 0)

        if score > 5000:
            return "Exceptional engagement indicates a major announcement or industry shift."
        if score > 2000:
            return "High engagement suggests significant community interest in this topic."
        if "model" in text or "launch" in text:
            return "Product or model launch generating substantial discussion."
        if "open source" in text or "github" in text:
            return "Open source release attracting developer attention."
        if source == "producthunt" and post.get("votes", 0) > 500:
            return "Top-rated product launch on Product Hunt."
        return "Noteworthy content with above-average engagement metrics."

    def _generate_opportunities(self, posts: list[dict], trends: list[dict], tools: list[dict]) -> list[dict]:
        text = " ".join(p.get("text", "") or "" for p in posts).lower()
        text += " ".join(t.get("name", "") for t in trends).lower()

        opportunities = []
        if "mcp" in text or "model context protocol" in text:
            opportunities.append({"title": "MCP Tooling & Integration", "description": "Build developer tools, SDKs, and integrations around the Model Context Protocol ecosystem."})
        if "agent" in text:
            opportunities.append({"title": "Agent Frameworks & Platforms", "description": "Create specialized agent frameworks for vertical use cases like customer support, coding, and data analysis."})
        if "rag" in text or "vector" in text:
            opportunities.append({"title": "RAG Infrastructure", "description": "Build better retrieval infrastructure and tooling for production RAG systems."})
        if "code" in text or "coding" in text:
            opportunities.append({"title": "AI Code Review & Testing", "description": "Develop AI-powered code review and automated testing tools for modern development workflows."})
        if "fine.tuning" in text or "fine-tuning" in text:
            opportunities.append({"title": "Fine-tuning as a Service", "description": "Offer managed fine-tuning services for open-source models targeting specific industries."})

        opportunities.append({"title": "Content Series: Daily AI Brief", "description": "Create a newsletter or video series summarizing daily AI developments."})
        opportunities.append({"title": "AI Tool Directory", "description": "Build a curated directory of AI tools with reviews and comparisons."})

        return opportunities

    def _generate_takeaways(self, posts: list[dict], trends: list[dict]) -> list[str]:
        takeaways = []
        cats = [p.get("category", "") for p in posts if p.get("category")]
        from collections import Counter
        top_cats = Counter(cats).most_common(3)

        if top_cats:
            takeaways.append(f"Dominant categories: {', '.join(f'{c[0]} ({c[1]} posts)' for c in top_cats)}.")

        high_signal = [p for p in posts if p.get("signal") == "high"]
        if high_signal:
            takeaways.append(f"Identified {len(high_signal)} high-signal items worth deeper investigation.")

        if trends:
            trend_names = list(set(t.get("name", "") for t in trends))[:5]
            takeaways.append(f"Emerging themes: {', '.join(trend_names)}.")

        takeaways.append("Monitor identified tools and startups for potential partnership or investment opportunities.")

        return takeaways

    def _get_top_category(self, posts: list[dict]) -> str:
        from collections import Counter
        cats = [p.get("category", "") for p in posts if p.get("category")]
        if not cats:
            return "Uncategorized"
        return Counter(cats).most_common(1)[0][0]

    def _markdown_to_html(self, markdown: str) -> str:
        try:
            import markdown as md
            return md.markdown(markdown, extensions=["extra", "tables"])
        except ImportError:
            html = markdown.replace("### ", "<h3>")
            html = html.replace("## ", "<h2>")
            html = html.replace("# ", "<h1>")
            html = html.replace("**", "<strong>").replace("**", "</strong>")
            html = html.replace("*", "<em>").replace("*", "</em>")
            html = html.replace("\n\n", "</p><p>")
            html = html.replace("\n- ", "<br>- ")
            html = f"<html><body><p>{html}</p></body></html>"
            return html
