# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 상위 `C:/GIT/CLAUDE.md`의 Git-First Workflow를 상속합니다.

## 실행 환경 감지 (SSH 재접속 금지)

- Claude는 현재 호스트에서 직접 실행 중 — **SSH 재접속을 시도하지 말 것**
- `uname -s` = `Darwin` → MacBook 환경, docker/docker compose 직접 실행 가능
- `uname -s` 결과가 Windows/MINGW/MSYS → Windows 개발환경
- Docker 명령은 현재 호스트에서 바로 실행 (별도 SSH 접속 불필요)
- compose 파일 선택: Darwin → `docker-compose.yml` / Windows → `docker-compose.local.yml`

> 3-머신 작업 환경(MacBook 편집·운영 / Desktop 터미널·AutoQA / Notebook TIPAIP2 격리) 규칙: [WORKSTATION_GUIDE.md](https://github.com/bluevlad/Ai-Legacy-bluevlad/blob/main/infrastructure/environments/WORKSTATION_GUIDE.md) — 개인 서비스 편집은 MacBook 에서만, Desktop 은 pull-only

## Project Overview

CompanyAnalyzer - 기업 홈페이지 기반 AI 강점/개선점 분석 시스템 (URL 크롤링 → 콘텐츠 전처리 → Claude AI 분석 → 구조화된 리포트)

## Environment

- **Database**: PostgreSQL (공유 컨테이너, psycopg2 + asyncpg)
- **LLM**: Ollama (gemma3:12b 분석)
- **Crawling**: httpx (정적) + Playwright (동적/SPA)
- **Docker Strategy**: Docker Compose (backend + frontend)
- **Python Version**: 3.11+

## Tech Stack

### Backend (backend/)

| 항목 | 기술 |
|------|------|
| Language | Python 3.11+ |
| Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 (async: asyncpg, sync: psycopg2) |
| Migration | Alembic |
| Database | PostgreSQL 15 |
| Crawling | httpx (정적), Playwright (동적) |
| HTML Parsing | BeautifulSoup4, lxml |
| AI | Ollama SDK |
| Config | Pydantic + python-dotenv |
| Testing | pytest, pytest-asyncio |

### Frontend (frontend/)

| 항목 | 기술 |
|------|------|
| Language | JavaScript (JSX) |
| Framework | React 18 |
| Build Tool | Vite |
| Router | React Router 6 |
| HTTP Client | Axios |
| Chart | Recharts |
| Serve | Nginx (Docker) |

## Setup and Run Commands

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
playwright install chromium

# Backend 실행
uvicorn app.api.main:app --reload --port 9080

# Backend 테스트
pytest

# Docker (전체)
docker compose -f docker-compose.local.yml up -d

# Frontend
cd frontend
npm install
npm run dev         # 개발 서버
npm run build       # 프로덕션 빌드
```

### Port Mapping

| 서비스 | 로컬 | Docker |
|--------|------|--------|
| Backend API | 9080 | 9080:9080 |
| Frontend | (dev port) | 4080:4080 |

## Architecture Overview

```
backend/app/
├── api/            # FastAPI 메인 앱
├── routers/        # API 라우터 (엔드포인트)
├── services/       # 비즈니스 로직 (크롤러, 분석기)
├── prompts/        # LLM 프롬프트 템플릿
├── schemas/        # Pydantic 스키마
├── database/       # SQLAlchemy 세션, 모델
└── core/           # 설정, 의존성
```

## Do NOT

- Oracle 문법 사용 금지 — PostgreSQL 전용
- .env 파일 커밋 금지
- requirements.txt에 없는 패키지를 설치 없이 import 금지
- pydantic v1 문법과 v2 문법 혼용 금지 (v2 사용)
- 서버 주소, 비밀번호 추측 금지 — 반드시 확인 후 사용
- 자격증명(API 키 등)을 소스코드에 하드코딩하지 마라
- CORS에 allow_origins=["*"] 사용하지 마라 — 허용 Origin 명시
- robots.txt를 무시하고 크롤링하지 마라
- 크롤링 속도 제한(2초 간격)을 무시하지 마라
- 로그인이 필요한 페이지를 크롤링하지 마라

## Required Environment Variables

```
DATABASE_URL=              # PostgreSQL 연결
OLLAMA_BASE_URL=           # Ollama 서버 URL (기본: http://localhost:11434)
ANALYSIS_MODEL=            # 분석 모델 (기본: gemma3:12b)
PREPROCESSING_MODEL=       # 전처리 모델 (기본: gemma3:4b)
MAX_CRAWL_PAGES=           # 최대 크롤링 페이지 수 (기본: 10)
CRAWL_DELAY_SECONDS=       # 크롤링 요청 간격 (기본: 2)
FRONTEND_URL=              # CORS 설정
BACKEND_URL=               # 백엔드 URL
```

## Database Notes

- SQL 문법: PostgreSQL 호환만 사용
- 비동기 드라이버: asyncpg
- 동기 드라이버: psycopg2-binary
- 마이그레이션: Alembic

## Documentation

### 문서 참조 경로
- 코드 문서: `CompanyAnalyzer/docs/`
- 프로젝트 문서: `C:/GIT/Ai-Legacy-bluevlad/docs/CompanyAnalyzer/`
  - 기획서, WBS, IMPLEMENTATION.md, 로드맵

### 문서 작성 규칙
- 코드 관련 (API 변경, 환경설정): `CompanyAnalyzer/docs/`
- 기획/설계/로드맵: `C:/GIT/Ai-Legacy-bluevlad/docs/CompanyAnalyzer/`

## Deployment

- **운영 포트**: Frontend 4080, Backend 9080
- **네트워크**: database-network (외부 공유), companyanalyzer-network (내부)
- **헬스체크**: http://localhost:9080/api/health

## 자주 발생하는 Root-Cause (예방 가이드)

| Root-Cause | 설명 | 예방 |
|-----------|------|------|
| `env-assumption` | Docker 내/외부 경로, 환경변수 가정 | Settings 클래스에서 필수값 검증, 기본값 금지 |
| `import-error` | 패키지 import 경로 오류, 상대/절대 경로 혼동 | `__init__.py` 확인, 절대 import 사용 |
| `null-handling` | Optional 필드 None 미처리 | Pydantic `Optional[T]` + 기본값 명시 |
| `type-mismatch` | SQLAlchemy 모델 ↔ Pydantic 스키마 타입 불일치 | `model_validate()` 사용, from_attributes=True |
| `async-handling` | await 누락, 동기/비동기 혼용 | async def에서 동기 DB 호출 금지, run_in_executor 사용 |
| `db-migration` | Alembic 마이그레이션 누락/충돌 | 스키마 변경 시 반드시 `alembic revision --autogenerate` |
