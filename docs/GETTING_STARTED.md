# Getting Started

## 사전 요구사항

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (공유 컨테이너 또는 로컬)
- Ollama (로컬 LLM 서버)

## 설정

### 1. Ollama 모델 설치

```bash
ollama pull gemma3:12b
```

### 2. 환경변수 설정

```bash
cp .env.example .env.local
# .env.local 파일을 열어 OLLAMA_BASE_URL 등을 확인
```

### 2. 데이터베이스 생성

```sql
CREATE DATABASE companyanalyzer;
```

### 4. Backend 실행

```bash
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt

uvicorn app.api.main:app --reload --port 9080
```

API 문서 확인: http://localhost:9080/docs

### 5. Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 http://localhost:4080 접속

## Docker로 실행

```bash
docker compose -f docker-compose.local.yml up -d
```
