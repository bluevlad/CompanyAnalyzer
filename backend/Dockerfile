FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 브라우저 설치 (Phase 2에서 활성화)
# RUN playwright install --with-deps chromium

# 비root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 애플리케이션 코드 복사
COPY . .

# ChromaDB persistent dir (volume mount target)
RUN mkdir -p /data/chromadb && chown -R appuser:appuser /data

# 권한 설정
RUN chown -R appuser:appuser /app

# 비root 사용자로 전환
USER appuser

# 포트 노출
EXPOSE 9080

# 실행
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "9080"]
