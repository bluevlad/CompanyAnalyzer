"""PoC CLI: 모니터링 대상 1건에 대해 수집 → 인덱싱 → 브리핑 생성을 직접 실행.

OAuth 없이 검증할 때 사용. monitoring 라우터의 run-now 엔드포인트와 동일 흐름.

사용법:
    cd backend
    python -m scripts.run_briefing --target-id 1 --period daily [--no-send]
"""
import argparse
import asyncio
import logging

from app.database.connection import AsyncSessionLocal
from app.services.mention_collector_service import MentionCollectorService
from app.services.newsletter_renderer_service import NewsletterRendererService
from app.services.periodic_report_service import PeriodicReportService
from app.services.rag_indexer_service import get_rag_indexer

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.models import MonitoringTarget

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("run_briefing")


async def main(target_id: int, period: str, send: bool) -> None:
    async with AsyncSessionLocal() as session:
        # 대상 로드
        result = await session.execute(
            select(MonitoringTarget)
            .options(selectinload(MonitoringTarget.company))
            .where(MonitoringTarget.id == target_id)
        )
        target = result.scalar_one_or_none()
        if target is None:
            log.error("monitoring target id=%s not found. scripts.seed_company 먼저 실행하세요.", target_id)
            return
        log.info("[1/4] target loaded: %s (id=%s)", target.company.name if target.company else "?", target.id)

        # 1) 수집
        collector = MentionCollectorService()
        new_mentions = await collector.collect(session, target)
        log.info("[2/4] collected %s new mentions", len(new_mentions))

        # 2) RAG 인덱싱
        indexer = get_rag_indexer()
        total_chunks = 0
        for m in new_mentions:
            try:
                total_chunks += await indexer.index_mention(session, m)
            except Exception as exc:
                log.warning("index skip mention=%s: %s", m.id, exc)
        log.info("[3/4] indexed %s chunks into ChromaDB", total_chunks)

        # 3) 브리핑 생성
        reporter = PeriodicReportService()
        newsletter = await reporter.run(session, target_id, period)  # type: ignore[arg-type]
        if newsletter is None:
            log.error("briefing generation failed")
            return
        log.info(
            "[4/4] newsletter id=%s subject=%r",
            newsletter.id,
            newsletter.subject,
        )

        # 4) 렌더 / 발송
        renderer = NewsletterRendererService()
        if send:
            result = await renderer.send(session, newsletter.id)
            log.info("send result: %s", result)
        else:
            html = await renderer.render(session, newsletter.id)
            if html:
                log.info("HTML rendered (%s chars). Use --send to email.", len(html))
                # 디버깅 편의: 처음 500자
                print("\n--- HTML preview (first 500 chars) ---")
                print(html[:500])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-id", type=int, required=True)
    parser.add_argument("--period", choices=["daily", "weekly", "monthly"], default="daily")
    parser.add_argument("--no-send", action="store_true", help="이메일 발송 건너뛰기 (렌더만)")
    args = parser.parse_args()
    asyncio.run(main(args.target_id, args.period, send=not args.no_send))
