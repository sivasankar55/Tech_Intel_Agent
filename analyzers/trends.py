from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any

from utils.logger import setup_logger


class TrendDetector:
    def __init__(self):
        self.logger = setup_logger("TrendDetector")
        self._compile_patterns()

    def _compile_patterns(self):
        self.tool_pattern = re.compile(
            r"\b(chatgpt|claude|gemini|copilot|cursor|perplexity|midjourney|"
            r"stable.diffusion|langchain|llamaindex|haystack|gradio|"
            r"fastapi|docker|kubernetes|pytorch|tensorflow|jax|"
            r"huggingface|spacy|transformers|diffusers|"
            r"vite|next\.js|vercel|railway|fly\.io)\b",
            re.IGNORECASE,
        )
        self.framework_pattern = re.compile(
            r"\b(agent|mcp|model.context.protocol|rag|vector.db|"
            r"fine.tuning|rlhf|prompt.engineering|chain.of.thought|"
            r"function.calling|tool.use|multi.modal|agentic|"
            r"langgraph|crewai|autogen|pydantic.ai)\b",
            re.IGNORECASE,
        )
        self.model_pattern = re.compile(
            r"\b(gpt-4|gpt-4o|gpt-5|claude-3|claude-4|claude-opus|"
            r"gemini-2|gemini-2\.5|llama-3|llama-4|mistral|mixtral|"
            r"deepseek|qwen|command.r|dbrx|phi-3|phi-4)\b",
            re.IGNORECASE,
        )
        self.startup_pattern = re.compile(
            r"\b(openai|anthropic|perplexity|cursor|vercel|lovable|bolt|"
            r"langchain|huggingface|replicate|cohere|ai21|stability|"
            r"runway|character.ai|adept|notion|linear|supabase|"
            r"neon|plane|cal\.com)\b",
            re.IGNORECASE,
        )

    def detect(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tools: list[str] = []
        frameworks: list[str] = []
        models: list[str] = []
        startups: list[str] = []

        for post in posts:
            text = f"{post.get('text', '')} {post.get('title', '')}"

            tools.extend(self.tool_pattern.findall(text))
            frameworks.extend(self.framework_pattern.findall(text))
            models.extend(self.model_pattern.findall(text))
            startups.extend(self.startup_pattern.findall(text))

        trends = []

        for label, items in [
            ("Tools", tools),
            ("Frameworks", frameworks),
            ("AI Models", models),
            ("Startups", startups),
        ]:
            counter = Counter(items)
            for item, count in counter.most_common(10):
                if count >= 2:
                    trends.append(
                        {
                            "name": item.lower().replace(".", " ").title(),
                            "category": label,
                            "frequency": count,
                            "first_seen": datetime.utcnow(),
                            "last_seen": datetime.utcnow(),
                        }
                    )

        self.logger.info(f"Detected {len(trends)} trends")
        return trends

    def generate_summaries(self, trends: list[dict]) -> list[str]:
        summaries = []
        category_groups: dict[str, list[str]] = {}
        for t in trends:
            cat = t.get("category", "Other")
            if cat not in category_groups:
                category_groups[cat] = []
            category_groups[cat].append(t["name"])

        for cat, items in category_groups.items():
            top = items[:3]
            if top:
                summaries.append(f"{cat}: {', '.join(top)} trending")
        return summaries
