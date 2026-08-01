"""주기별(일/주/월) 브리핑 생성 서비스.

흐름:
    1) 기간 mentions 조회
    2) (옵션) 누락된 mention 분류 enrich
    3) RAG 컨텍스트 검색 (mention 기반 핵심 키워드 → ChromaDB top-k)
    4) Ollama gemma3:12b로 브리핑 JSON 생성
    5) Newsletter 레코드 저장 (period UNIQUE → 동일 기간 재실행 시 갱신)
    6) NewsletterMention 매핑 저장
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, time, timedelta
from typing import Literal, Optional
from zoneinfo import ZoneInfo

import ollama as ollama_lib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.database.models import (
    Mention,
    MonitoringTarget,
    Newsletter,
    NewsletterMention,
)
from app.prompts.daily_briefing import DAILY_BRIEFING_PROMPT
from app.prompts.monthly_briefing import MONTHLY_BRIEFING_PROMPT
from app.prompts.weekly_briefing import WEEKLY_BRIEFING_PROMPT
from app.services.mention_analyzer_service import MentionAnalyzerService
from app.services.rag_indexer_service import get_rag_indexer

logger = logging.getLogger(__name__)
settings = get_settings()

PeriodType = Literal["daily", "weekly", "monthly"]

PROMPTS = {
    "daily": DAILY_BRIEFING_PROMPT,
    "weekly": WEEKLY_BRIEFING_PROMPT,
    "monthly": MONTHLY_BRIEFING_PROMPT,
}

PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


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
        return {"raw_text": text}


def _period_window(period: PeriodType, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """KST 기준 period의 [start, end). 매일 00:00 ~ 24:00."""
    now = datetime.now(tz)
    today_start = datetime.combine(now.date(), time.min, tzinfo=tz)
    if period == "daily":
        # 어제 00:00 ~ 오늘 00:00
        end = today_start
        start = end - timedelta(days=1)
    elif period == "weekly":
        end = today_start
        start = end - timedelta(days=7)
    else:  # monthly
        end = today_start
        start = end - timedelta(days=30)
    return start, end


def _format_mentions_block(mentions: list[Mention]) -> str:
    lines = []
    for idx, m in enumerate(mentions, 1):
        published = m.published_at.strftime("%Y-%m-%d %H:%M") if m.published_at else "?"
        sentiment = m.sentiment or "-"
        score = m.importance_score if m.importance_score is not None else "-"
        summary = m.one_line_summary or (m.raw_content or "")[:200]
        lines.append(
            f"[#{idx}] ({m.source_name or '-'} | {published} | {sentiment} | imp={score})\n"
            f"    제목: {m.title or '-'}\n"
            f"    URL : {m.url}\n"
            f"    요약: {summary}"
        )
    return "\n".join(lines) if lines else "(수집된 외부 언급 없음)"


def _format_rag_block(snippets: list[dict]) -> str:
    if not snippets:
        return "(RAG 컨텍스트 없음)"
    lines = []
    for s in snippets:
        lines.append(
            f"- {s.get('title','')} ({s.get('source','')})\n  {s.get('text','')[:300]}"
        )
    return "\n".join(lines)


class PeriodicReportService:
    def __init__(self) -> None:
        self.client = ollama_lib.AsyncClient(host=settings.OLLAMA_BASE_URL)
        self.model = settings.ANALYSIS_MODEL
        self.rag = get_rag_indexer()
        self.classifier = MentionAnalyzerService()

    async def run(
        self,
        session: AsyncSession,
        target_id: int,
        period: PeriodType,
    ) -> Optional[Newsletter]:
        """지정 target의 period 브리핑을 생성하고 Newsletter 레코드를 반환."""
        target = await self._load_target(session, target_id)
        if target is None:
            logger.warning("target %s not found", target_id)
            return None

        tz = ZoneInfo(settings.SCHEDULER_TZ)
        period_start, period_end = _period_window(period, tz)

        mentions = await self._fetch_mentions(session, target_id, period_start, period_end)
        logger.info(
            "target=%s period=%s mentions=%s window=%s..%s",
            target_id, period, len(mentions), period_start, period_end,
        )

        # 미분류 mention 보강 (sentiment/importance/summary)
        for m in mentions:
            if m.sentiment is None or m.importance_score is None:
                try:
                    await self.classifier.enrich(m, target)
                except Exception as exc:
                    logger.warning("classify skip mention=%s: %s", m.id, exc)
        await session.commit()

        # 중요도 순 정렬, 최대 30건 컨텍스트
        mentions_sorted = sorted(
            mentions,
            key=lambda x: (x.importance_score or 0),
            reverse=True,
        )[:30]

        # RAG 검색 — 키워드 1개로 top-k 5
        rag_query = " ".join((target.keywords or [])[:3]) or (target.company.name if target.company else "")
        rag_snippets: list[dict] = []
        try:
            if rag_query:
                rag_snippets = await self.rag.search(target_id, rag_query, k=5)
        except Exception as exc:
            logger.warning("rag search failed: %s", exc)

        prompt = PROMPTS[period].format(
            company_name=target.company.name if target.company else f"target#{target_id}",
            keywords=", ".join(target.keywords or []),
            period_start=period_start.strftime("%Y-%m-%d %H:%M"),
            period_end=period_end.strftime("%Y-%m-%d %H:%M"),
            mention_count=len(mentions_sorted),
            mentions_block=_format_mentions_block(mentions_sorted),
            rag_context=_format_rag_block(rag_snippets),
        )

        try:
            resp = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 4096, "temperature": 0.3},
            )
            text = resp["message"]["content"]
        except Exception as exc:
            logger.error("LLM briefing call failed: %s", exc)
            return None

        ai_summary = _parse_json(text)
        subject = ai_summary.get("headline") or f"{target.company.name if target.company else ''} {period} briefing"

        # Newsletter upsert (period UNIQUE)
        existing = await session.execute(
            select(Newsletter).where(
                Newsletter.target_id == target_id,
                Newsletter.period_type == period,
                Newsletter.period_start == period_start,
            )
        )
        newsletter = existing.scalar_one_or_none()
        if newsletter is None:
            newsletter = Newsletter(
                target_id=target_id,
                period_type=period,
                period_start=period_start,
                period_end=period_end,
                subject=subject[:300],
                ai_summary=ai_summary,
            )
            session.add(newsletter)
            await session.flush()
        else:
            newsletter.subject = subject[:300]
            newsletter.ai_summary = ai_summary
            newsletter.error_message = None

        # 인용 mention 매핑 재구성
        await session.execute(
            NewsletterMention.__table__.delete().where(
                NewsletterMention.newsletter_id == newsletter.id
            )
        )
        for rank, m in enumerate(mentions_sorted, 1):
            session.add(
                NewsletterMention(
                    newsletter_id=newsletter.id, mention_id=m.id, rank=rank
                )
            )

        await session.commit()
        return newsletter

    async def _load_target(
        self, session: AsyncSession, target_id: int
    ) -> Optional[MonitoringTarget]:
        result = await session.execute(
            select(MonitoringTarget)
            .options(selectinload(MonitoringTarget.company))
            .where(MonitoringTarget.id == target_id)
        )
        return result.scalar_one_or_none()

    async def _fetch_mentions(
        self,
        session: AsyncSession,
        target_id: int,
        start: datetime,
        end: datetime,
    ) -> list[Mention]:
        # published_at 우선, NULL이면 collected_at으로 fallback
        result = await session.execute(
            select(Mention).where(
                Mention.target_id == target_id,
                ((Mention.published_at >= start) & (Mention.published_at < end))
                | (
                    (Mention.published_at.is_(None))
                    & (Mention.collected_at >= start)
                    & (Mention.collected_at < end)
                ),
            )
        )
        return list(result.scalars().all())
