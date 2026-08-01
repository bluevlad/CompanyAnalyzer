"""분석 요청 및 결과 조회 API"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_database
from app.database.models import Company, Analysis, AnalysisResult
from app.schemas.analyze import (
    AnalyzeRequest, AnalyzeResponse, AnalysisDetailResponse,
    AnalysisListResponse, ActiveAnalysisResponse,
)

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def create_analysis(
    request: AnalyzeRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_database),
):
    """기업 홈페이지 분석을 요청합니다."""
    url = str(request.url)

    # 기업 조회 또는 생성
    result = await db.execute(select(Company).where(Company.url == url))
    company = result.scalar_one_or_none()

    if not company:
        company = Company(
            name=request.company_name or url,
            url=url,
        )
        db.add(company)
        await db.flush()
    elif request.company_name and request.company_name != company.name:
        company.name = request.company_name
        await db.flush()

    # 중복 분석 방지: 동일 기업에 진행 중인 분석이 있으면 차단
    active_steps = ["pending", "discovering", "crawling", "statistics", "analyzing"]
    active_result = await db.execute(
        select(Analysis).where(
            Analysis.company_id == company.id,
            Analysis.step.in_(active_steps),
        )
    )
    active_analysis = active_result.scalar_one_or_none()

    if active_analysis:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "이미 분석 중인 기업입니다",
                "analysis_id": active_analysis.id,
                "company_name": company.name,
                "status": active_analysis.status,
            },
        )

    # 분석 레코드 생성
    analysis = Analysis(
        company_id=company.id,
        status="pending",
        email=request.email,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # arq 태스크 큐에 분석 작업 등록
    arq_pool = http_request.app.state.arq_pool
    await arq_pool.enqueue_job(
        "run_analysis",
        analysis.id,
        url,
        email=request.email,
        company_name=company.name,
    )

    return AnalyzeResponse(
        id=analysis.id,
        company_id=company.id,
        company_name=company.name,
        url=company.url,
        status=analysis.status,
        step=analysis.step,
        email=analysis.email,
        created_at=analysis.created_at,
    )


@router.get("/analyses/active", response_model=list[ActiveAnalysisResponse])
async def get_active_analyses(
    db: AsyncSession = Depends(get_database),
):
    """현재 진행 중인 분석 목록을 조회합니다. 재접속 시 안내에 사용됩니다."""
    active_steps = ["pending", "discovering", "crawling", "statistics", "analyzing"]
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.company))
        .where(Analysis.step.in_(active_steps))
        .order_by(Analysis.created_at.desc())
    )
    analyses = result.scalars().all()

    return [
        ActiveAnalysisResponse(
            id=a.id,
            company_id=a.company_id,
            company_name=a.company.name,
            url=a.company.url,
            status=a.status,
            step=a.step,
            step_progress=a.step_progress or {},
            crawled_pages=a.crawled_pages or 0,
            created_at=a.created_at,
        )
        for a in analyses
    ]


@router.get("/analyses")
async def list_analyses(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_database),
):
    """분석 이력 목록을 조회합니다."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.company))
        .order_by(Analysis.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    analyses = result.scalars().all()

    return [
        AnalysisListResponse(
            id=a.id,
            company_name=a.company.name,
            url=a.company.url,
            status=a.status,
            step=a.step,
            crawled_pages=a.crawled_pages or 0,
            email_sent=a.email_sent or False,
            created_at=a.created_at,
            completed_at=a.completed_at,
        )
        for a in analyses
    ]


@router.get("/analyses/{analysis_id}")
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_database),
):
    """분석 결과 상세를 조회합니다."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.company), selectinload(Analysis.results))
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")

    # 카테고리별 결과 구성
    results_dict = {}
    for r in analysis.results:
        results_dict[r.category] = r.content

    return AnalysisDetailResponse(
        id=analysis.id,
        company_id=analysis.company_id,
        company_name=analysis.company.name,
        url=analysis.company.url,
        status=analysis.status,
        step=analysis.step,
        step_progress=analysis.step_progress or {},
        crawled_pages=analysis.crawled_pages or 0,
        total_tokens=analysis.total_tokens or 0,
        analysis_duration=analysis.analysis_duration,
        results=results_dict,
        email=analysis.email,
        email_sent=analysis.email_sent or False,
        email_sent_at=analysis.email_sent_at,
        email_error=analysis.email_error,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )


@router.get("/analyses/{analysis_id}/compare")
async def compare_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_database),
):
    """동일 기업의 이전 분석과 점수를 비교합니다."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.company), selectinload(Analysis.results))
        .where(Analysis.id == analysis_id)
    )
    current = result.scalar_one_or_none()

    if not current:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")

    if current.status != "completed":
        raise HTTPException(status_code=400, detail="완료된 분석만 비교할 수 있습니다.")

    # 동일 기업의 이전 완료 분석 조회
    prev_result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.results))
        .where(
            Analysis.company_id == current.company_id,
            Analysis.status == "completed",
            Analysis.id < analysis_id,
        )
        .order_by(Analysis.id.desc())
        .limit(1)
    )
    previous = prev_result.scalar_one_or_none()

    if not previous:
        return {"has_previous": False, "message": "이전 분석 이력이 없습니다."}

    # 현재/이전 점수 추출
    def get_scores(analysis_obj):
        for r in analysis_obj.results:
            if r.category == "summary" and isinstance(r.content, dict):
                return r.content.get("overall_scores", {})
        return {}

    current_scores = get_scores(current)
    previous_scores = get_scores(previous)

    # 점수 diff 계산
    score_diff = {}
    all_keys = set(list(current_scores.keys()) + list(previous_scores.keys()))
    for key in all_keys:
        curr = current_scores.get(key)
        prev = previous_scores.get(key)
        if curr is not None and prev is not None:
            score_diff[key] = {
                "current": curr,
                "previous": prev,
                "diff": curr - prev,
            }

    return {
        "has_previous": True,
        "current_analysis_id": current.id,
        "previous_analysis_id": previous.id,
        "current_date": current.created_at.isoformat(),
        "previous_date": previous.created_at.isoformat(),
        "score_diff": score_diff,
        "current_pages": current.crawled_pages,
        "previous_pages": previous.crawled_pages,
    }


@router.post("/analyses/{analysis_id}/resend-email")
async def resend_email(
    analysis_id: int,
    db: AsyncSession = Depends(get_database),
):
    """분석 결과 이메일을 재발송합니다."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.company), selectinload(Analysis.results))
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")

    if analysis.status != "completed":
        raise HTTPException(status_code=400, detail="완료된 분석만 이메일을 발송할 수 있습니다.")

    if not analysis.email:
        raise HTTPException(status_code=400, detail="이메일 주소가 등록되지 않았습니다.")

    # 결과 데이터 구성
    results_dict = {}
    for r in analysis.results:
        results_dict[r.category] = r.content

    email_data = {
        "id": analysis.id,
        "results": results_dict,
        "crawled_pages": analysis.crawled_pages or 0,
        "total_tokens": analysis.total_tokens or 0,
        "analysis_duration": analysis.analysis_duration,
        "completed_at": str(analysis.completed_at) if analysis.completed_at else "",
    }

    email_service = EmailService()
    send_result = await email_service.send_analysis_report(
        analysis.email,
        analysis.company.name,
        email_data,
    )

    if send_result["success"]:
        analysis.email_sent = True
        analysis.email_sent_at = datetime.now(timezone.utc)
        analysis.email_error = None
        await db.commit()
        return {"message": "이메일이 발송되었습니다."}
    else:
        analysis.email_error = send_result.get("error", "Unknown error")
        await db.commit()
        raise HTTPException(status_code=500, detail=f"이메일 발송 실패: {send_result.get('error')}")


@router.delete("/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_database),
):
    """분석 결과를 삭제합니다."""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")

    await db.delete(analysis)
    await db.commit()
    return {"message": "삭제되었습니다."}
