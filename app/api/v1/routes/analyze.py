# app/api/v1/routes/analyze.py

import logging
import time

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.analyze import (
    AnalyzeResponse,
    SkillMatchMetrics,
)
from app.services.extractor import extract_text_from_file
from app.services.matcher import compute_match

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# ROUTER
# This router is registered in main.py
# with prefix /api/v1
# Final path: POST /api/v1/analyze
# ─────────────────────────────────────────

router = APIRouter(
    prefix="/analyze",
    tags=["Analysis"],
)


# ─────────────────────────────────────────
# POST /api/v1/analyze
# Phase 1 core endpoint
# Accepts: resume file + JD text
# Returns: deterministic skill gap scorecard
# Target: < 2 seconds response time
# ─────────────────────────────────────────

@router.post(
    "/",
    response_model=AnalyzeResponse,
    summary="Analyze resume against job description",
    description=(
        "Upload a resume (PDF or DOCX) and provide a job description. "
        "Returns a deterministic skill gap analysis with match percentage, "
        "matched skills, and missing skills. Phase 1: no LLM, pure set math."
    ),
)
async def analyze_resume(
    resume_file: UploadFile = File(
        ...,
        description="Resume file — .pdf or .docx only, max 5MB"
    ),
    jd_text: str = Form(
        ...,
        min_length=50,
        max_length=10000,
        description="Full job description text"
    ),
    company_name: str = Form(
        default="Unknown Company",
        max_length=100,
        description="Company name for context"
    ),
    role_title: str = Form(
        default="Unknown Role",
        max_length=100,
        description="Job role title for context"
    ),
):
    # ── Start latency timer ─────────────────
    # Your Phase 1 milestone requires < 2 seconds
    # We measure and log it on every request
    start_time = time.perf_counter()

    logger.info(
        f"Analysis started — "
        f"file: '{resume_file.filename}' | "
        f"company: '{company_name}' | "
        f"role: '{role_title}'"
    )

    # ── Step 1: Read file bytes ─────────────
    # FastAPI gives us an UploadFile object
    # We read all bytes into memory
    # extractor.py handles everything from here
    file_bytes = await resume_file.read()

    # ── Step 2: Extract text from resume ────
    # Raises DocumentParsingError or
    # InsufficientContextError on failure
    # Both are caught by handlers in main.py
    resume_text = extract_text_from_file(
        file_bytes=file_bytes,
        filename=resume_file.filename,
    )

    # ── Step 3: Run deterministic matcher ───
    # Pure set math — zero hallucination
    # Formula: Missing = JD Skills - Resume Skills
    match_result = compute_match(
        resume_text=resume_text,
        jd_text=jd_text,
    )

    # ── Step 4: Measure latency ─────────────
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    logger.info(
        f"Analysis completed — "
        f"score: {match_result.match_percentage}% | "
        f"matched: {len(match_result.matched_skills)} | "
        f"missing: {len(match_result.missing_skills)} | "
        f"time: {elapsed_ms}ms"
    )

    # ── Step 5: Warn if latency target missed
    if elapsed_ms > 2000:
        logger.warning(
            f"LATENCY TARGET MISSED — "
            f"{elapsed_ms}ms exceeds 2000ms target. "
            f"Check extractor and matcher performance."
        )

    # ── Step 6: Build and return response ───
    return AnalyzeResponse(
        company_name=company_name,
        role_title=role_title,
        metrics=SkillMatchMetrics(
            match_percentage=match_result.match_percentage,
            matched_skills=match_result.matched_skills,
            missing_skills=match_result.missing_skills,
            total_jd_skills=match_result.total_jd_skills,
            total_resume_skills=match_result.total_resume_skills,
        ),
        ai_insights_ready=False,
    )