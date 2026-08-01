from functools import cached_property, lru_cache

from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Admin access control — comma-separated string in env (pydantic-settings v2는
    # list[str]을 env에서 JSON으로 parse하므로 빈 문자열에서 실패한다 → str로 받고
    # 사용 시 SUPER_ADMIN_EMAILS_LIST 프로퍼티로 split.)
    SUPER_ADMIN_EMAILS: str = ""

    @cached_property
    def SUPER_ADMIN_EMAILS_LIST(self) -> list[str]:
        return [e.strip() for e in self.SUPER_ADMIN_EMAILS.split(",") if e.strip()]

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours

    # URLs
    FRONTEND_URL: str = "http://localhost:4080"
    BACKEND_URL: str = "http://localhost:9080"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
