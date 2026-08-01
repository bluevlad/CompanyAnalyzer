from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional
from datetime import datetime


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None


class AnalyzeResponse(BaseModel):
    id: int
    company_id: int
    company_name: str
    url: str
    status: str
    step: str = "pending"
    email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisDetailResponse(BaseModel):
    id: int
    company_id: int
    company_name: str
    url: str
    status: str
    step: str = "pending"
    step_progress: dict = {}
    crawled_pages: int
    total_tokens: int
    analysis_duration: Optional[float]
    results: dict
    email: Optional[str] = None
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    email_error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class AnalysisListResponse(BaseModel):
    id: int
    company_name: str
    url: str
    status: str
    step: str = "pending"
    crawled_pages: int
    email_sent: bool = False
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ActiveAnalysisResponse(BaseModel):
    """진행 중인 분석 정보."""
    id: int
    company_id: int
    company_name: str
    url: str
    status: str
    step: str = "pending"
    step_progress: dict = {}
    crawled_pages: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class DuplicateAnalysisError(BaseModel):
    """중복 분석 요청 시 반환되는 에러 정보."""
    message: str
    analysis_id: int
    company_name: str
    status: str
