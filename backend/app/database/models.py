from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    industry = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    analyses = relationship("Analysis", back_populates="company")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    step = Column(String(20), nullable=False, default="pending")  # v2: 6단계 상태
    step_progress = Column(JSON, nullable=False, default=dict)    # v2: 단계별 세부 진행률
    crawled_pages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    analysis_duration = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", back_populates="analyses")
    results = relationship("AnalysisResult", back_populates="analysis")
    pages = relationship("CrawledPage", back_populates="analysis")
    discovered_pages = relationship("DiscoveredPage", back_populates="analysis", cascade="all, delete-orphan")


# ─── Monitoring & Newsletter (분석설정 대상 기업의 외부 언급 모니터링) ────────


class MonitoringTarget(Base):
    """분석 설정 대상 기업 (모니터링 활성화)."""

    __tablename__ = "monitoring_targets"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, unique=True)
    keywords = Column(JSON, nullable=False)  # 모니터링 검색 키워드 목록 (기업명, 제품명 등)
    news_sources = Column(JSON, nullable=False)  # ["naver_news","google_news_rss"]
    schedule_daily = Column(Boolean, default=True, nullable=False)
    schedule_weekly = Column(Boolean, default=True, nullable=False)
    schedule_monthly = Column(Boolean, default=True, nullable=False)
    recipient_emails = Column(JSON, nullable=False)  # ["ceo@example.com", ...]
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company")
    mentions = relationship("Mention", back_populates="target", cascade="all, delete-orphan")
    newsletters = relationship("Newsletter", back_populates="target", cascade="all, delete-orphan")


class Mention(Base):
    """수집된 외부 언급 1건 (뉴스/보도자료 등)."""

    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("monitoring_targets.id"), nullable=False, index=True)
    source_type = Column(String(20), nullable=False)  # news / blog / press
    source_name = Column(String(100), nullable=True)  # "네이버뉴스", "전자신문" 등
    url = Column(String(1000), nullable=False)
    title = Column(String(500), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    author = Column(String(200), nullable=True)
    raw_content = Column(Text, nullable=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    sentiment = Column(String(10), nullable=True)  # positive/neutral/negative
    importance_score = Column(Integer, nullable=True)  # 0~100
    matched_keywords = Column(JSON, nullable=True)
    one_line_summary = Column(String(500), nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

    target = relationship("MonitoringTarget", back_populates="mentions")
    rag_chunks = relationship("RagChunk", back_populates="mention", cascade="all, delete-orphan")


class RagChunk(Base):
    """ChromaDB 벡터에 대응하는 메타데이터 (실벡터는 ChromaDB에 저장)."""

    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, index=True)
    mention_id = Column(Integer, ForeignKey("mentions.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    chroma_id = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    mention = relationship("Mention", back_populates="rag_chunks")


class Newsletter(Base):
    """발송된 일/주/월 단위 브리핑 1건."""

    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("monitoring_targets.id"), nullable=False, index=True)
    period_type = Column(String(10), nullable=False)  # daily / weekly / monthly
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    subject = Column(String(300), nullable=False)
    html_content = Column(Text, nullable=True)
    ai_summary = Column(JSON, nullable=True)  # {headline, summary_3lines, executive_actions, ...}
    sent_at = Column(DateTime(timezone=True), nullable=True)
    sent_to = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("target_id", "period_type", "period_start", name="uq_newsletter_period"),
    )

    target = relationship("MonitoringTarget", back_populates="newsletters")
    mention_links = relationship(
        "NewsletterMention", back_populates="newsletter", cascade="all, delete-orphan"
    )


class NewsletterMention(Base):
    """뉴스레터 ↔ 인용된 멘션 매핑."""

    __tablename__ = "newsletter_mentions"

    id = Column(Integer, primary_key=True, index=True)
    newsletter_id = Column(
        Integer, ForeignKey("newsletters.id", ondelete="CASCADE"), nullable=False
    )
    mention_id = Column(Integer, ForeignKey("mentions.id"), nullable=False)
    rank = Column(Integer, nullable=True)

    newsletter = relationship("Newsletter", back_populates="mention_links")
    mention = relationship("Mention")


class DiscoveredPage(Base):
    """Discovery 단계에서 발견된 페이지 (사이트맵 구조 파악 결과)."""

    __tablename__ = "discovered_pages"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False, default="other")
    depth = Column(Integer, default=0)
    priority = Column(Integer, default=5)
    selected = Column(Boolean, default=True)
    parent_url = Column(String(500), nullable=True)
    title = Column(String(300), nullable=True)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("Analysis", back_populates="discovered_pages")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    category = Column(String(50), nullable=False)
    content = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("Analysis", back_populates="results")


class CrawledPage(Base):
    __tablename__ = "crawled_pages"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    url = Column(String(500), nullable=False)
    title = Column(String(300), nullable=True)
    content_text = Column(Text, nullable=True)
    content_length = Column(Integer, default=0)
    status_code = Column(Integer, nullable=True)
    crawled_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("Analysis", back_populates="pages")
