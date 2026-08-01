"""
arq 워커 설정 — `arq app.worker.settings.WorkerSettings` 로 실행합니다.
"""

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.worker.tasks import run_analysis, recover_stuck_analyses

settings = get_settings()


def _parse_redis_url(url: str) -> RedisSettings:
    """redis://host:port/db 형식의 URL을 RedisSettings로 변환합니다."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
    )


class WorkerSettings:
    """arq 워커 설정."""

    functions = [run_analysis]
    on_startup = recover_stuck_analyses
    redis_settings = _parse_redis_url(settings.REDIS_URL)
    max_jobs = 2                    # 동시 분석 최대 2건
    job_timeout = 1800              # 30분 타임아웃
    max_tries = 2                   # 실패 시 1회 재시도
    retry_defer = 30                # 재시도 대기 30초
    queue_name = "companyanalyzer"  # 큐 이름
