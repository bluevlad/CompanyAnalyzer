"""모니터링 / 뉴스레터 API 라우터.

전 엔드포인트 admin 인증 필수 (require_admin).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import require_admin
from app.core.dependencies import get_database
from app.database.models import (
    Company,
    Mention,
    MonitoringTarget,
    Newsletter,
)
from app.schemas.monitoring import (
    MentionResponse,
    MonitoringTargetCreate,
    MonitoringTargetResponse,
    MonitoringTargetUpdate,
    NewsletterResponse,
    RunNowResponse,
)
from app.services.mention_collector_service import MentionCollectorService
from app.services.newsletter_renderer_service import NewsletterRendererService
from app.services.periodic_report_service import PeriodicReportService
from app.services.rag_indexer_service import get_rag_indexer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

PeriodType = Literal["daily", "weekly", "monthly"]


def _to_response(target: MonitoringTarget) -> MonitoringTargetResponse:
    return MonitoringTargetResponse(
        id=target.id,
        company_id=target.company_id,
        company_name=target.company.name if target.company else "",
        company_url=target.company.url if target.company else "",
        keywords=target.keywords or [],
        news_sources=target.news_sources or [],
        schedule_daily=target.schedule_daily,
        schedule_weekly=target.schedule_weekly,
        schedule_monthly=target.schedule_monthly,
        recipient_emails=target.recipient_emails or [],
        is_active=target.is_active,
        created_at=target.created_at,
        updated_at=target.updated_at,
    )


# ─────────────────────── targets CRUD ──────────────────────────────────


@router.post("/targets", response_model=MonitoringTargetResponse)
async def create_target(
    payload: MonitoringTargetCreate,
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    # Company upsert by URL
    company_url = str(payload.company_url)
    result = await db.execute(select(Company).where(Company.url == company_url))
    company = result.scalar_one_or_none()
    if company is None:
        company = Company(
            name=payload.company_name,
            url=company_url,
            industry=payload.industry,
        )
        db.add(company)
        await db.flush()
    else:
        company.name = payload.company_name
        if payload.industry:
            company.industry = payload.industry

    # Existing target?
    result = await db.execute(
        select(MonitoringTarget).where(MonitoringTarget.company_id == company.id)
    )
    target = result.scalar_one_or_none()
    if target is not None:
        raise HTTPException(status_code=409, detail="monitoring target already exists for this company")

    target = MonitoringTarget(
        company_id=company.id,
        keywords=payload.keywords,
        news_sources=payload.news_sources,
        schedule_daily=payload.schedule_daily,
        schedule_weekly=payload.schedule_weekly,
        schedule_monthly=payload.schedule_monthly,
        recipient_emails=[str(e) for e in payload.recipient_emails],
        is_active=True,
    )
    db.add(target)
    await db.commit()
    await db.refresh(target, attribute_names=["company"])
    return _to_response(target)


@router.get("/targets", response_model=list[MonitoringTargetResponse])
async def list_targets(
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    result = await db.execute(
        select(MonitoringTarget)
        .options(selectinload(MonitoringTarget.company))
        .order_by(MonitoringTarget.id.desc())
    )
    return [_to_response(t) for t in result.scalars().all()]


@router.get("/targets/{target_id}", response_model=MonitoringTargetResponse)
async def get_target(
    target_id: int,
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    target = await _load_target(db, target_id)
    return _to_response(target)


@router.patch("/targets/{target_id}", response_model=MonitoringTargetResponse)
async def update_target(
    target_id: int,
    payload: MonitoringTargetUpdate,
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    target = await _load_target(db, target_id)
    data = payload.model_dump(exclude_unset=True)
    if "recipient_emails" in data:
        data["recipient_emails"] = [str(e) for e in data["recipient_emails"]]
    for key, value in data.items():
        setattr(target, key, value)
    await db.commit()
    await db.refresh(target, attribute_names=["company"])
    return _to_response(target)


@router.delete("/targets/{target_id}")
async def deactivate_target(
    target_id: int,
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    target = await _load_target(db, target_id)
    target.is_active = False
    await db.commit()
    return {"id": target_id, "is_active": False}


# ─────────────────────── mentions / newsletters ────────────────────────


@router.get("/targets/{target_id}/mentions", response_model=list[MentionResponse])
async def list_mentions(
    target_id: int,
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    await _load_target(db, target_id)  # 존재 확인
    stmt = select(Mention).where(Mention.target_id == target_id)
    if from_:
        stmt = stmt.where(Mention.collected_at >= from_)
    if to:
        stmt = stmt.where(Mention.collected_at < to)
    stmt = stmt.order_by(Mention.collected_at.desc()).limit(limit)
    result = await db.execute(stmt)
    mentions = result.scalars().all()
    return [
        MentionResponse(
            id=m.id,
            target_id=m.target_id,
            source_type=m.source_type,
            source_name=m.source_name,
            url=m.url,
            title=m.title,
            published_at=m.published_at,
            sentiment=m.sentiment,
            importance_score=m.importance_score,
            one_line_summary=m.one_line_summary,
            matched_keywords=m.matched_keywords,
            collected_at=m.collected_at,
        )
        for m in mentions
    ]


@router.get("/targets/{target_id}/newsletters", response_model=list[NewsletterResponse])
async def list_newsletters(
    target_id: int,
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    await _load_target(db, target_id)
    result = await db.execute(
        select(Newsletter)
        .where(Newsletter.target_id == target_id)
        .order_by(Newsletter.period_start.desc())
    )
    return [_newsletter_to_response(n) for n in result.scalars().all()]


@router.get("/newsletters/{newsletter_id}")
async def newsletter_html(
    newsletter_id: int,
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    """HTML 미리보기 — 저장된 html_content 또는 즉시 렌더링."""
    result = await db.execute(select(Newsletter).where(Newsletter.id == newsletter_id))
    newsletter = result.scalar_one_or_none()
    if newsletter is None:
        raise HTTPException(status_code=404, detail="newsletter not found")
    if not newsletter.html_content:
        renderer = NewsletterRendererService()
        await renderer.render(db, newsletter_id)
        await db.refresh(newsletter)
    return {
        "id": newsletter.id,
        "subject": newsletter.subject,
        "html": newsletter.html_content,
        "ai_summary": newsletter.ai_summary,
    }


@router.post("/newsletters/{newsletter_id}/resend")
async def resend_newsletter(
    newsletter_id: int,
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    renderer = NewsletterRendererService()
    return await renderer.send(db, newsletter_id)


# ─────────────────────── run-now (PoC trigger) ─────────────────────────


@router.post("/targets/{target_id}/run-now", response_model=RunNowResponse)
async def run_now(
    target_id: int,
    period: PeriodType = Query("daily"),
    send_email: bool = Query(True),
    db: AsyncSession = Depends(get_database),
    _: dict = Depends(require_admin),
):
    """수동 트리거: 수집 → RAG 인덱싱 → 브리핑 생성 → (옵션) 이메일 발송.

    PoC 검증용. 실패해도 진행 단계는 응답에 포함.
    """
    target = await _load_target(db, target_id)

    # 1) 수집
    collector = MentionCollectorService()
    try:
        new_mentions = await collector.collect(db, target)
        collected = len(new_mentions)
    except Exception as exc:
        logger.exception("collect failed")
        return RunNowResponse(
            target_id=target_id, period=period, collected=0,
            indexed_chunks=0, newsletter_id=None, sent=False, error=f"collect: {exc}",
        )

    # 2) RAG 인덱싱
    indexer = get_rag_indexer()
    indexed_chunks = 0
    for m in new_mentions:
        try:
            indexed_chunks += await indexer.index_mention(db, m)
        except Exception as exc:
            logger.warning("index skip mention=%s: %s", m.id, exc)

    # 3) 브리핑 생성
    reporter = PeriodicReportService()
    try:
        newsletter = await reporter.run(db, target_id, period)
    except Exception as exc:
        logger.exception("report failed")
        return RunNowResponse(
            target_id=target_id, period=period, collected=collected,
            indexed_chunks=indexed_chunks, newsletter_id=None, sent=False,
            error=f"report: {exc}",
        )
    if newsletter is None:
        return RunNowResponse(
            target_id=target_id, period=period, collected=collected,
            indexed_chunks=indexed_chunks, newsletter_id=None, sent=False,
            error="report returned None",
        )

    # 4) 발송
    sent = False
    error: Optional[str] = None
    if send_email:
        renderer = NewsletterRendererService()
        result = await renderer.send(db, newsletter.id)
        sent = bool(result.get("success"))
        if not sent:
            error = result.get("error")
    else:
        # 미발송이라도 HTML은 미리 렌더해둔다
        renderer = NewsletterRendererService()
        await renderer.render(db, newsletter.id)

    return RunNowResponse(
        target_id=target_id,
        period=period,
        collected=collected,
        indexed_chunks=indexed_chunks,
        newsletter_id=newsletter.id,
        sent=sent,
        error=error,
    )


# ─────────────────────── helpers ───────────────────────────────────────


async def _load_target(db: AsyncSession, target_id: int) -> MonitoringTarget:
    result = await db.execute(
        select(MonitoringTarget)
        .options(selectinload(MonitoringTarget.company))
        .where(MonitoringTarget.id == target_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="monitoring target not found")
    return target


def _newsletter_to_response(n: Newsletter) -> NewsletterResponse:
    return NewsletterResponse(
        id=n.id,
        target_id=n.target_id,
        period_type=n.period_type,
        period_start=n.period_start,
        period_end=n.period_end,
        subject=n.subject,
        ai_summary=n.ai_summary,
        sent_at=n.sent_at,
        sent_to=n.sent_to,
        error_message=n.error_message,
        created_at=n.created_at,
    )
