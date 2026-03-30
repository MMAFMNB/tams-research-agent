"""Report request/response schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AnalysisRequest(BaseModel):
    ticker: str
    company_name: str = ""
    sections: list[str] = []  # Empty = full report
    locale: str = "en"
    formats: list[str] = ["docx"]  # docx, pdf, pptx
    chat_session_id: str | None = None


class AnalysisStatusResponse(BaseModel):
    task_id: str
    report_id: str
    status: str
    progress: int = 0  # 0-100
    current_step: str = ""


class ReportResponse(BaseModel):
    id: str
    ticker: str
    company_name: str
    locale: str
    status: str
    report_type: str
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReportDetailResponse(ReportResponse):
    sections: list["ReportSectionResponse"] = []
    files: list["ReportFileResponse"] = []
    sources: list["ReportSourceResponse"] = []
    snapshot: "ReportSnapshotResponse | None" = None


class ReportSectionResponse(BaseModel):
    id: str
    section_key: str
    title: str
    content: str
    sort_order: int

    model_config = {"from_attributes": True}


class ReportFileResponse(BaseModel):
    id: str
    file_type: str
    storage_path: str
    file_size: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportSourceResponse(BaseModel):
    id: str
    source_type: str
    title: str
    url: str | None = None
    accessed_at: datetime
    reliability: str
    is_realtime: bool
    delay_minutes: int
    description: str | None = None

    model_config = {"from_attributes": True}


class ReportSnapshotResponse(BaseModel):
    current_price: float | None = None
    market_cap: int | None = None
    pe_ratio: float | None = None
    forward_pe: float | None = None
    eps_ttm: float | None = None
    dividend_yield: float | None = None
    rating: str | None = None
    price_target: float | None = None
    risk_level: str | None = None
    key_catalysts: dict | None = None
    key_risks: dict | None = None

    model_config = {"from_attributes": True}


class ReportComparisonResponse(BaseModel):
    ticker: str
    reports: list[ReportResponse]
    snapshots: list[ReportSnapshotResponse]
    changes: dict  # Computed diffs


class ShareLinkCreate(BaseModel):
    file_type: str = "pdf"
    expires_in_hours: int | None = None


class ShareLinkResponse(BaseModel):
    share_url: str
    token: str
    expires_at: datetime | None = None
