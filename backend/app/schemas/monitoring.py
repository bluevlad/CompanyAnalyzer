"""모니터링 / 뉴스레터 API Pydantic 스키마."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class MonitoringTargetCreate(BaseModel):
    company_name: str = Field(..., max_length=200)
    company_url: HttpUrl
    industry: Optional[str] = Field(None, max_length=100)
    keywords: list[str] = Field(..., min_length=1)
    news_sources: list[str] = Field(default_factory=lambda: ["naver_news", "google_news_rss"])
    schedule_daily: bool = True
    schedule_weekly: bool = True
    schedule_monthly: bool = True
    recipient_emails: list[EmailStr] = Field(..., min_length=1)


class MonitoringTargetUpdate(BaseModel):
    keywords: Optional[list[str]] = None
    news_sources: Optional[list[str]] = None
    schedule_daily: Optional[bool] = None
    schedule_weekly: Optional[bool] = None
    schedule_monthly: Optional[bool] = None
    recipient_emails: Optional[list[EmailStr]] = None
    is_active: Optional[bool] = None


class MonitoringTargetResponse(BaseModel):
    id: int
    company_id: int
    company_name: str
    company_url: str
    keywords: list[str]
    news_sources: list[str]
    schedule_daily: bool
    schedule_weekly: bool
    schedule_monthly: bool
    recipient_emails: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MentionResponse(BaseModel):
    id: int
    target_id: int
    source_type: str
    source_name: Optional[str]
    url: str
    title: Optional[str]
    published_at: Optional[datetime]
    sentiment: Optional[str]
    importance_score: Optional[int]
    one_line_summary: Optional[str]
    matched_keywords: Optional[list[str]]
    collected_at: datetime


class NewsletterResponse(BaseModel):
    id: int
    target_id: int
    period_type: str
    period_start: datetime
    period_end: datetime
    subject: str
    ai_summary: Optional[dict[str, Any]]
    sent_at: Optional[datetime]
    sent_to: Optional[list[str]]
    error_message: Optional[str]
    created_at: datetime


class RunNowResponse(BaseModel):
    target_id: int
    period: str
    collected: int
    indexed_chunks: int
    newsletter_id: Optional[int]
    sent: bool
    error: Optional[str] = None
