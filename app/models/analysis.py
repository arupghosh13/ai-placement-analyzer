"""analyses, skill_matches, skill_gaps: one scorecard and its per-skill rows."""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, uuid_pk


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint("match_score BETWEEN 0 AND 100", name="match_score_range"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="status_valid",
        ),
    )

    id: Mapped[uuid_pk]
    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    job_description_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True
    )
    analysis_hash: Mapped[str] = mapped_column(String(64), unique=True)
    matcher_version: Mapped[str] = mapped_column(
        String(20), default="v1", server_default="v1"
    )
    match_score: Mapped[float | None] = mapped_column(Float)
    total_jd_skills: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    total_resume_skills: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    created_at: Mapped[created_at_col]
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SkillMatch(Base):
    __tablename__ = "skill_matches"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "normalized_skill",
            name="uq_skill_matches_analysis_id_normalized_skill",
        ),
        CheckConstraint(
            "match_type IN ('exact', 'partial', 'related')", name="match_type_valid"
        ),
    )

    id: Mapped[uuid_pk]
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE")
    )
    skill_name: Mapped[str] = mapped_column(String(100))
    normalized_skill: Mapped[str] = mapped_column(String(100))
    match_type: Mapped[str] = mapped_column(String(20))
    evidence: Mapped[str | None] = mapped_column(Text)


class SkillGap(Base):
    __tablename__ = "skill_gaps"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "normalized_skill",
            name="uq_skill_gaps_analysis_id_normalized_skill",
        ),
        CheckConstraint(
            "gap_type IN ('missing', 'partial', 'weak')", name="gap_type_valid"
        ),
        CheckConstraint(
            "importance IN ('low', 'medium', 'high', 'critical')",
            name="importance_valid",
        ),
    )

    id: Mapped[uuid_pk]
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE")
    )
    skill_name: Mapped[str] = mapped_column(String(100))
    normalized_skill: Mapped[str] = mapped_column(String(100))
    gap_type: Mapped[str] = mapped_column(String(20))
    importance: Mapped[str | None] = mapped_column(String(20))
    evidence: Mapped[str | None] = mapped_column(Text)