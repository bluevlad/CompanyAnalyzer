# CompanyAnalyzer

기업 홈페이지 기반 AI 강점/개선점 분석 시스템

## Overview

기업 홈페이지 URL을 입력하면 AI가 자동으로 크롤링하고, 사업/디지털/브랜딩 관점에서 기업의 강점과 개선점을 분석하여 구조화된 리포트를 제공합니다.

## Features

- **URL 기반 자동 크롤링**: 홈페이지 주요 페이지 자동 수집
- **AI 기업 분석**: Claude API를 활용한 다각도 분석
- **구조화된 리포트**: 사업/디지털/브랜딩 카테고리별 분석 결과
- **분석 이력 관리**: 기업별 분석 결과 저장 및 추적

## Tech Stack

| 레이어 | 기술 |
|--------|------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | React 18 / Vite |
| Database | PostgreSQL 15 |
| AI | Claude API (Sonnet 4.5) |
| Crawling | httpx / Playwright |
| Deploy | Docker Compose |

## Quick Start

### Docker (권장)

```bash
docker compose -f docker-compose.local.yml up -d
```

- Frontend: http://localhost:4080
- Backend API: http://localhost:9080
- API Docs: http://localhost:9080/docs

### 개발 환경

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
uvicorn app.api.main:app --reload --port 9080

# Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
CompanyAnalyzer/
├── backend/           # FastAPI 백엔드
│   ├── app/
│   │   ├── api/       # FastAPI 앱
│   │   ├── routers/   # API 엔드포인트
│   │   ├── services/  # 크롤러, 분석기
│   │   ├── prompts/   # LLM 프롬프트
│   │   ├── schemas/   # Pydantic 스키마
│   │   ├── database/  # DB 모델/세션
│   │   └── core/      # 설정
│   └── Dockerfile
├── frontend/          # React 프론트엔드
│   ├── src/
│   │   ├── pages/     # 페이지 컴포넌트
│   │   ├── components/# 공통 컴포넌트
│   │   └── services/  # API 클라이언트
│   └── Dockerfile
├── docker-compose.yml
└── docker-compose.local.yml
```

## License

```
Copyright (c) 2026 운몽시스템즈 (Unmong Systems). All rights reserved.
```
