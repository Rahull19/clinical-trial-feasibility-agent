"""SQLAlchemy ORM models for clinical trial data.
These are infrastructure-only models. Domain code never imports from here;
repositories map between ORM models and domain entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


class TrialORM(Base):
    """Historical clinical trial record."""

    __tablename__ = "trials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    protocol_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    therapeutic_area: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phase: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    indication: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    target_enrollment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    trial_sites: Mapped[List["TrialSiteORM"]] = relationship(
        "TrialSiteORM", back_populates="trial", cascade="all, delete-orphan"
    )
    trial_investigators: Mapped[List["TrialInvestigatorORM"]] = relationship(
        "TrialInvestigatorORM", back_populates="trial", cascade="all, delete-orphan"
    )


class CountryORM(Base):
    """Country with regulatory metadata."""

    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    regulatory_complexity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    avg_startup_weeks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    patient_pool: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    sites: Mapped[List["SiteORM"]] = relationship("SiteORM", back_populates="country")


class SiteORM(Base):
    """Clinical trial site."""

    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    country_id: Mapped[int] = mapped_column(Integer, ForeignKey("countries.id"), nullable=False)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    past_trials_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)

    country: Mapped["CountryORM"] = relationship("CountryORM", back_populates="sites")
    trial_sites: Mapped[List["TrialSiteORM"]] = relationship(
        "TrialSiteORM", back_populates="site", cascade="all, delete-orphan"
    )
    investigators: Mapped[List["InvestigatorORM"]] = relationship(
        "InvestigatorORM", back_populates="site"
    )


class InvestigatorORM(Base):
    """Principal investigator."""

    __tablename__ = "investigators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigator_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("sites.id"), nullable=False)
    specialization: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    past_trials: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)

    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="investigators")
    trial_investigators: Mapped[List["TrialInvestigatorORM"]] = relationship(
        "TrialInvestigatorORM", back_populates="investigator", cascade="all, delete-orphan"
    )


class TrialSiteORM(Base):
    """Association table: Trial <-> Site."""

    __tablename__ = "trial_sites"
    __table_args__ = (
        UniqueConstraint("trial_id", "site_id", name="uq_trial_site"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trial_id: Mapped[int] = mapped_column(Integer, ForeignKey("trials.id"), nullable=False)
    site_id: Mapped[int] = mapped_column(Integer, ForeignKey("sites.id"), nullable=False)

    trial: Mapped["TrialORM"] = relationship("TrialORM", back_populates="trial_sites")
    site: Mapped["SiteORM"] = relationship("SiteORM", back_populates="trial_sites")


class TrialInvestigatorORM(Base):
    """Association table: Trial <-> Investigator."""

    __tablename__ = "trial_investigators"
    __table_args__ = (
        UniqueConstraint("trial_id", "investigator_id", name="uq_trial_investigator"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trial_id: Mapped[int] = mapped_column(Integer, ForeignKey("trials.id"), nullable=False)
    investigator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investigators.id"), nullable=False
    )

    trial: Mapped["TrialORM"] = relationship("TrialORM", back_populates="trial_investigators")
    investigator: Mapped["InvestigatorORM"] = relationship(
        "InvestigatorORM", back_populates="trial_investigators"
    )