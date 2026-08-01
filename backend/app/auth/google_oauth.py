"""Google Identity Services (GSI) ID 토큰 검증.

AllergyInsight / EduFit과 동일한 패턴 — 프론트엔드에서 Google GSI로 받은
ID token credential을 검증한 후 admin JWT를 발급한다. CLIENT_SECRET 불필요.

필요 환경변수:
    GOOGLE_CLIENT_ID         — Google Cloud Console에서 발급한 web client ID
    SUPER_ADMIN_EMAILS       — 이 이메일만 admin role 부여 (콤마 구분)

deprecated:
    이전 Authlib 기반 redirect flow(/login, /callback)는 제거되었다.
    프론트는 GSI 버튼이 발급한 credential을 POST /api/auth/google/verify 로 보낸다.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.config import get_auth_settings
from app.auth.dependencies import require_admin
from app.auth.jwt_handler import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/google", tags=["auth"])


class GoogleVerifyRequest(BaseModel):
    credential: str  # GSI에서 받은 ID token JWT


class GoogleVerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    email: str
    picture: str = ""
    role: str = "admin"


def _verify_id_token(credential: str, expected_audience: str) -> dict:
    """google-auth로 ID token 검증. 성공 시 idinfo dict."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    idinfo = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        expected_audience,
    )
    if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError("invalid issuer")
    return idinfo


@router.get("/config")
async def google_config():
    """프론트엔드가 GSI 초기화에 사용할 public client_id 노출."""
    settings = get_auth_settings()
    return {"client_id": settings.GOOGLE_CLIENT_ID}


@router.post("/verify", response_model=GoogleVerifyResponse)
async def google_verify(payload: GoogleVerifyRequest):
    settings = get_auth_settings()

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured (GOOGLE_CLIENT_ID missing)",
        )

    try:
        idinfo = _verify_id_token(payload.credential, settings.GOOGLE_CLIENT_ID)
    except ValueError as exc:
        logger.warning("google id token verify failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        )

    email = (idinfo.get("email") or "").strip().lower()
    name = idinfo.get("name") or (email.split("@")[0] if email else "user")
    picture = idinfo.get("picture") or ""

    admin_emails = [e.lower() for e in settings.SUPER_ADMIN_EMAILS_LIST]
    if not email or email not in admin_emails:
        logger.warning("google login denied — not an admin: %s", email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 없는 계정입니다.",
        )

    token = create_access_token(
        {
            "sub": email,
            "name": name,
            "picture": picture,
            "role": "admin",
            "auth": "google",
        }
    )
    logger.info("google login success: %s", email)
    return GoogleVerifyResponse(
        access_token=token,
        name=name,
        email=email,
        picture=picture,
    )


# 토큰 검증용 — 프론트의 라우트 가드가 사용
me_router = APIRouter(prefix="/auth", tags=["auth"])


@me_router.get("/me")
async def me(admin: dict = Depends(require_admin)):
    return {
        "email": admin.get("sub"),
        "name": admin.get("name"),
        "picture": admin.get("picture", ""),
        "role": admin.get("role", "admin"),
        "auth": admin.get("auth", "google"),
    }
