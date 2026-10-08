# app/schemas/analyze.py

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime, timezone
import uuid


# ─────────────────────────────────────────
# REQUEST SCHEMA
# What the API receives from the user
# ─────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """
    The user sends:
    - A resume file (handled at route level as UploadFile, not here)
    - The job description as plain text
    - Optional: company name and role title for context
    """
    jd_text: str = Field(
        ...,
        min_length=50,
        max_length=10000,
        description="The full job description text"
    )
    company_name: str = Field(
        default="Unknown Company",
        max_length=100,
        description="Name of the company"
    )
    role_title: str = Field(
        default="Unknown Role",
        max_length=100,
        description="Title of the job role"
    )


# ─────────────────────────────────────────
# INNER SCHEMAS
# Building blocks used inside the response
# ─────────────────────────────────────────

class SkillMatchMetrics(BaseModel):
    """
    The core numbers from the deterministic matching engine.
    This is what proves zero-hallucination — pure set math.
    """
    match_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of JD skills found in resume"
    )
    matched_skills: List[str] = Field(
        default_factory=list,
        description="Skills present in BOTH resume and JD"
    )
    missing_skills: List[str] = Field(
        default_factory=list,
        description="Skills in JD but NOT found in resume"
    )
    total_jd_skills: int = Field(
        ...,
        description="Total number of skills extracted from JD"
    )
    total_resume_skills: int = Field(
        ...,
        description="Total number of skills extracted from resume"
    )


# ─────────────────────────────────────────
# RESPONSE SCHEMA
# What the API sends back to the user
# ─────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    """
    Phase 1 response — deterministic only.
    No LLM. No embeddings. Pure string matching.
    ai_insights_ready is always False in Phase 1.
    """
    analysis_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ID for this analysis"
    )
    status: str = Field(
        default="completed",
        description="Status of the analysis"
    )
    company_name: str
    role_title: str
    metrics: SkillMatchMetrics
    ai_insights_ready: bool = Field(
        default=False,
        description="Always False in Phase 1. True only after Phase 6 LLM integration."
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp of analysis"
    )


# ─────────────────────────────────────────
# ERROR RESPONSE SCHEMA
# Consistent error format across all endpoints
# ─────────────────────────────────────────

class ErrorResponse(BaseModel):
    """
    Every error in this system returns this exact shape.
    No raw Python errors ever reach the user.
    """
    success: bool = False
    error_code: str = Field(
        ...,
        description="Machine-readable error code e.g. DOCUMENT_PARSING_FAILED"
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of what went wrong"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )