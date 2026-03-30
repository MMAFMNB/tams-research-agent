"""Tenant model for multi-tenant white-label support."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    logo_url: Mapped[str] = mapped_column(Text, nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), default="#222F62")
    accent_color: Mapped[str] = mapped_column(String(7), default="#1A6DB6")
    default_locale: Mapped[str] = mapped_column(String(5), default="en")
    pptx_template_path: Mapped[str] = mapped_column(Text, nullable=True)
    docx_header_path: Mapped[str] = mapped_column(Text, nullable=True)
    disclaimer_text: Mapped[str] = mapped_column(Text, nullable=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="tenant")
    reports = relationship("Report", back_populates="tenant")
    chat_sessions = relationship("ChatSession", back_populates="tenant")
