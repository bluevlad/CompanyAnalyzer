"""
arq 워커 태스크 — 분석 파이프라인을 백그라운드에서 실행합니다.
서버 재시작/워커 재시작 시에도 Redis 큐에 남아 있으므로 작업이 유실되지 않습니다.
"""

import time
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.database.models import Analysis, AnalysisResult, CrawledPage, DiscoveredPage
from app.services.discovery_service import DiscoveryService
from app.services.crawler_service import CrawlerService
from app.services.preprocessor_service import PreprocessorService
from app.services.analyzer_service import AnalyzerService
from app.services.site_evaluator_service import SiteEvaluatorService
from app.services.email_service import EmailService

settings = get_settings()


async def run_analysis(ctx: dict, analysis_id: int, url: str, email: str | None = None, company_name: str = ""):
    """기업 분석 파이프라인 (arq 태스크)."""
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        try:
            analysis = await session.get(Analysis, analysis_id)
            start_time = time.time()

            def _update_progress(step_name, step_data):
                progress = deepcopy(analysis.step_progress) if analysis.step_progress else {}
                if "steps" not in progress:
                    progress["steps"] = {}
                progress["current_step"] = step_name
                progress["steps"][step_name] = step_data
                analysis.step_progress = progress

            # ── Step 1: Discovery ──
            analysis.status = "crawling"
            analysis.step = "discovering"
            _update_progress("discovering", {"status": "running"})
            await session.commit()

            discovery = DiscoveryService()
            discovered = await discovery.discover(url)

            category_counts = {}
            for page in discovered:
                db_discovered = DiscoveredPage(
                    analysis_id=analysis_id,
                    url=page["url"],
                    category=page["category"],
                    depth=page["depth"],
                    priority=page["priority"],
                    title=page.get("title"),
                    parent_url=page.get("parent_url"),
                )
                session.add(db_discovered)
                cat = page["category"]
                category_counts[cat] = category_counts.get(cat, 0) + 1

            _update_progress("discovering", {
                "status": "done",
                "pages_found": len(discovered),
                "by_category": category_counts,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            await session.commit()

            # ── Step 2: Deep Crawl ──
            analysis.step = "crawling"
            _update_progress("crawling", {"status": "running", "total": 0, "done": 0})
            await session.commit()

            crawler = CrawlerService()
            crawled_pages = await crawler.crawl(url)

            for page in crawled_pages:
                db_page = CrawledPage(
                    analysis_id=analysis_id,
                    url=page.get("url", ""),
                    title=page.get("title", ""),
                    content_text=page.get("text", ""),
                    content_length=page.get("text_length", 0),
                    status_code=page.get("status_code"),
                )
                session.add(db_page)

            analysis.crawled_pages = len(crawled_pages)

            total_text_length = sum(p.get("text_length", 0) for p in crawled_pages)
            category_stats = {}
            for dp in discovered:
                cat = dp["category"]
                if cat not in category_stats:
                    category_stats[cat] = {"pages": 0, "text_length": 0}
                category_stats[cat]["pages"] += 1
            for page in crawled_pages:
                page_url = page.get("url", "")
                for dp in discovered:
                    if dp["url"] == page_url:
                        cat = dp["category"]
                        if cat in category_stats:
                            category_stats[cat]["text_length"] += page.get("text_length", 0)
                        break

            _update_progress("crawling", {
                "status": "done",
                "total": len(crawled_pages),
                "done": len(crawled_pages),
                "total_text_length": total_text_length,
                "by_category": category_stats,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            await session.commit()

            # ── Step 3: Layer 1 전처리 ──
            preprocessor = PreprocessorService()
            preprocessed = await preprocessor.preprocess_with_extraction(crawled_pages)

            # ── Step 4: Layer 2 AI 분석 ──
            analysis.status = "analyzing"
            analysis.step = "analyzing"
            categories = ["business", "digital", "branding", "summary"]
            _update_progress("analyzing", {
                "status": "running",
                "categories": categories,
                "done_categories": [],
            })
            await session.commit()

            analyzer = AnalyzerService()
            analysis_result = await analyzer.analyze(preprocessed)

            results = analysis_result.get("results", {})
            for category, content in results.items():
                db_result = AnalysisResult(
                    analysis_id=analysis_id,
                    category=category,
                    content=content,
                )
                session.add(db_result)

            _update_progress("analyzing", {
                "status": "done",
                "categories": categories,
                "done_categories": list(results.keys()),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })

            # ── Step 5: 사이트 정량 평가 ──
            try:
                evaluator = SiteEvaluatorService()
                site_metrics = await evaluator.evaluate(url, crawled_pages)
                if "digital" in results and isinstance(results["digital"], dict):
                    llm_digital_score = results["digital"].get("score", 7)
                    blended = SiteEvaluatorService.blend_scores(
                        site_metrics["code_measured_score"], llm_digital_score
                    )
                    site_metrics["blended_digital_score"] = blended
                db_metrics = AnalysisResult(
                    analysis_id=analysis_id,
                    category="site_metrics",
                    content=site_metrics,
                )
                session.add(db_metrics)
            except Exception:
                pass

            # ── 완료 ──
            analysis.status = "completed"
            analysis.step = "completed"
            analysis.total_tokens = analysis_result.get("total_tokens", 0)
            analysis.analysis_duration = time.time() - start_time
            analysis.completed_at = datetime.now(timezone.utc)
            await session.commit()

            # ── 이메일 발송 ──
            if email:
                try:
                    email_service = EmailService()
                    email_data = {
                        "id": analysis_id,
                        "results": results,
                        "crawled_pages": analysis.crawled_pages,
                        "total_tokens": analysis.total_tokens,
                        "analysis_duration": analysis.analysis_duration,
                        "completed_at": str(analysis.completed_at),
                    }
                    result = await email_service.send_analysis_report(email, company_name, email_data)
                    if result["success"]:
                        analysis.email_sent = True
                        analysis.email_sent_at = datetime.now(timezone.utc)
                    else:
                        analysis.email_error = result.get("error", "Unknown error")
                    await session.commit()
                except Exception as email_err:
                    analysis.email_error = str(email_err)
                    await session.commit()

        except Exception as e:
            analysis = await session.get(Analysis, analysis_id)
            analysis.status = "failed"
            analysis.step = "failed"
            analysis.error_message = str(e)
            await session.commit()

        finally:
            await engine.dispose()


async def recover_stuck_analyses(ctx: dict):
    """서버 재시작 시 중단된 분석을 감지하고 재큐잉합니다 (startup 시 1회 실행)."""
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from sqlalchemy import select

    async with SessionLocal() as session:
        active_steps = ["pending", "discovering", "crawling", "analyzing"]
        result = await session.execute(
            select(Analysis).where(Analysis.step.in_(active_steps))
        )
        stuck = result.scalars().all()

        for analysis in stuck:
            # 상태를 failed로 마킹 (사용자가 재분석 요청)
            analysis.status = "failed"
            analysis.step = "failed"
            analysis.error_message = "서버 재시작으로 인해 분석이 중단되었습니다. 재분석을 요청해주세요."

        if stuck:
            await session.commit()

    await engine.dispose()
    return f"{len(stuck)}건 중단 분석 처리 완료"
