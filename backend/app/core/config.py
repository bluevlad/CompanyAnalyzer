from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""

    # LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    ANALYSIS_MODEL: str = "gemma3:12b"
    PREPROCESSING_MODEL: str = "gemma3:4b"

    # Crawling
    MAX_CRAWL_PAGES: int = 10
    CRAWL_DELAY_SECONDS: float = 2.0
    CRAWL_TIMEOUT_SECONDS: int = 30
    USER_AGENT: str = "CompanyAnalyzer/1.0 (+https://github.com/bluevlad/CompanyAnalyzer)"

    # URLs
    FRONTEND_URL: str = "http://localhost:4080"
    BACKEND_URL: str = "http://localhost:9080"

    # Email / SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "CompanyAnalyzer"
    SMTP_USE_TLS: bool = True

    # 뉴스 수집 (모니터링)
    NAVER_NEWS_CLIENT_ID: str = ""
    NAVER_NEWS_CLIENT_SECRET: str = ""
    GOOGLE_NEWS_RSS_LANG: str = "ko"
    GOOGLE_NEWS_RSS_COUNTRY: str = "KR"
    MENTION_FETCH_LIMIT: int = 30  # 키워드당 최대 수집 건수

    # RAG / ChromaDB
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000
    CHROMADB_PERSIST_DIR: str = "/data/chromadb"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # Redis / Task Queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # 스케줄러
    SCHEDULER_TZ: str = "Asia/Seoul"
    DAILY_BRIEFING_HOUR: int = 8
    WEEKLY_BRIEFING_DOW: str = "mon"
    MONTHLY_BRIEFING_DAY: int = 1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
