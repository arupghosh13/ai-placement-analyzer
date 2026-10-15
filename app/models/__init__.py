"""Importing this package registers every model on Base.metadata (Alembic needs that)."""
from app.models.analysis import Analysis, SkillGap, SkillMatch
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.models.user import User

__all__ = ["Analysis", "JobDescription", "Resume", "SkillGap", "SkillMatch", "User"]