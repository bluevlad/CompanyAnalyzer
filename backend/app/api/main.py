from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.config import get_auth_settings
from app.auth.google_oauth import router as auth_router, me_router as auth_me_router
from app.core.config import get_settings

from app.routers import analyze, monitoring

settings = get_settings()
auth_settings = get_auth_settings()


def _parse_redis_url(url: str) -> RedisSettings:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 arq Redis 풀 생성, 종료 시 정리."""
    app.state.arq_pool = await create_pool(
        _parse_redis_url(settings.REDIS_URL),
        default_queue_name="companyanalyzer",
    )
    yield
    await app.state.arq_pool.close()


app = FastAPI(
    title="CompanyAnalyzer API",
    description="기업 홈페이지 기반 AI 강점/개선점 분석 시스템",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router, prefix="/api")
app.include_router(auth_me_router, prefix="/api")
app.include_router(analyze.router)
app.include_router(monitoring.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "CompanyAnalyzer"}


@app.get("/api/stats")
async def stats():
    return {
        "service": "CompanyAnalyzer",
        "version": "1.0.0",
    }
