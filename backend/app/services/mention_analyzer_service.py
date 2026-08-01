"""단건 Mention에 sentiment / importance / 한줄요약을 부여하는 서비스.

빠른 분류이므로 PREPROCESSING_MODEL(gemma3:4b)을 사용한다.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import ollama as ollama_lib

from app.core.config import get_settings
from app.database.models import Mention, MonitoringTarget
from app.prompts.mention_classifier import MENTION_CLASSIFIER_PROMPT

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_json(text: str) -> dict:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


class MentionAnalyzerService:
    def __init__(self) -> None:
        self.client = ollama_lib.AsyncClient(host=settings.OLLAMA_BASE_URL)
        self.model = settings.PREPROCESSING_MODEL

    async def enrich(self, mention: Mention, target: MonitoringTarget) -> Optional[dict]:
        """mention에 sentiment/importance/summary를 부여 (in-place)."""
        if not mention.title and not mention.raw_content:
            return None

        prompt = MENTION_CLASSIFIER_PROMPT.format(
            company_name=target.company.name if target.company else "",
            keywords=", ".join(target.keywords or []),
            source_name=mention.source_name or "",
            title=mention.title or "",
            content=(mention.raw_content or "")[:1500],
        )

        try:
            resp = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 512, "temperature": 0.2},
            )
            text = resp["message"]["content"]
        except Exception as exc:
            logger.error("classify failed for mention=%s: %s", mention.id, exc)
            return None

        data = _parse_json(text)
        if not data:
            return None

        sentiment = data.get("sentiment")
        if sentiment in ("positive", "neutral", "negative"):
            mention.sentiment = sentiment
        score = data.get("importance_score")
        if isinstance(score, (int, float)):
            mention.importance_score = max(0, min(100, int(score)))
        summary = data.get("one_line_summary")
        if summary:
            mention.one_line_summary = str(summary)[:500]
        return data
