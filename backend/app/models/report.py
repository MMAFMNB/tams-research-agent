"""Report model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_ticker_created", "tenant_id", "ticker", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    chat_session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id"), nullable=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str] = mapped_column(String(5), default="en")
    status: Mapped[ReportStatus] = mapped_column(SQLEnum(ReportStatus), default=ReportStatus.PENDING)
    report_type: Mapped[str] = mapped_column(String(50), default="full")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="reports")
    user = relationship("User", back_populates="reports")
    chat_session = relationship("ChatSession", back_populates="reports")
    sections = relationship("ReportSection", back_populates="report", order_by="ReportSection.sort_order")
    snapshot = relationship("ReportSnapshot", back_populates="report", uselist=False)
    files = relationship("ReportFile", back_populates="report")
    sources = relationship("ReportSource", back_populates="report")
