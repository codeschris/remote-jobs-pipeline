from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    ats_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    trust_tier: Mapped[int] = mapped_column(SmallInteger, default=2)

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_source_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)

    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    apply_url: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    seniority: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    legitimacy_score: Mapped[int] = mapped_column(SmallInteger, default=50)

    posted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    company: Mapped[Company | None] = relationship(back_populates="jobs")
