"""Report snapshot model - frozen metrics at report generation time for comparison."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Numeric, BigInteger, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from app.core.database import Base


class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), unique=True, nullable=False)
    current_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    market_cap: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    pe_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    forward_pe: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    eps_ttm: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    dividend_yield: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    rating: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    price_target: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    key_catalysts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    key_risks: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    raw_market_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    report = relationship("Report", back_populates="snapshot")
