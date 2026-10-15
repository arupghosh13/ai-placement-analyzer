"""Request and response shapes for the analysis endpoints."""
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.analyze import SkillMatchMetrics

JdText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=50, max_length=10000)
]


class CreateAnalysisRequest(BaseModel):
    resume_id: uuid.UUID
    jd_text: JdText
    company_name: str = Field(default="Unknown Company", min_length=1, max_length=100)
    role_title: str = Field(default="Unknown Role", min_length=1, max_length=100)


class AnalysisResponse(BaseModel):
    analysis_id: uuid.UUID
    resume_id: uuid.UUID
    status: str
    company_name: str
    role_title: str
    metrics: SkillMatchMetrics
    interview_preparation: list[str] = Field(default_factory=list)
    ai_insights_ready: bool = False
    matcher_version: str
    created_at: datetime


class AnalysisSummary(BaseModel):
    analysis_id: uuid.UUID
    resume_id: uuid.UUID
    company_name: str
    role_title: str
    match_percentage: float | None
    status: str
    created_at: datetime