"""Analysis business rules: run the matcher, store the scorecard, read it back."""
import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Analysis, JobDescription
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.job_description_repository import JobDescriptionRepository
from app.repositories.resume_repository import ResumeRepository
from app.services.matcher import compute_match
from app.services.resume_service import ResumeNotFoundError

logger = logging.getLogger(__name__)

MATCHER_VERSION = "v1"


class AnalysisNotFoundError(Exception):
    """Analysis does not exist OR belongs to another user (deliberately the same error)."""


@dataclass
class Scorecard:
    analysis: Analysis
    job_description: JobDescription
    matched_skills: list[str]
    missing_skills: list[str]


def _sha256(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


class AnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.resumes = ResumeRepository(session)
        self.jds = JobDescriptionRepository(session)
        self.analyses = AnalysisRepository(session)

    async def create(
        self,
        user_id: uuid.UUID,
        *,
        resume_id: uuid.UUID,
        jd_text: str,
        company_name: str,
        role_title: str,
    ) -> Scorecard:
        started = time.perf_counter()

        resume = await self.resumes.get_for_user(resume_id, user_id)
        if resume is None:
            raise ResumeNotFoundError()

        jd_hash = _sha256(" ".join(jd_text.split()).lower())
        analysis_hash = _sha256(
            str(resume.id), jd_hash, company_name.lower(), role_title.lower(), MATCHER_VERSION
        )

        result = await asyncio.to_thread(compute_match, resume.raw_text, jd_text)
        now = datetime.now(timezone.utc)

        try:
            jd = await self.jds.create(
                user_id=user_id,
                company_name=company_name,
                role_title=role_title,
                raw_text=jd_text,
                content_hash=jd_hash,
            )
            analysis = Analysis(
                resume_id=resume.id,
                job_description_id=jd.id,
                analysis_hash=analysis_hash,
                matcher_version=MATCHER_VERSION,
                match_score=result.match_percentage,
                total_jd_skills=result.total_jd_skills,
                total_resume_skills=result.total_resume_skills,
                status="completed",
                created_at=now,
                completed_at=now,
            )
            await self.analyses.create_with_results(
                analysis,
                matches=[
                    {"skill_name": s, "normalized_skill": s, "match_type": "exact"}
                    for s in result.matched_skills
                ],
                gaps=[
                    {"skill_name": s, "normalized_skill": s, "gap_type": "missing"}
                    for s in result.missing_skills
                ],
            )
            await self.session.commit()
        except IntegrityError:
            # UNIQUE analysis_hash: this exact request is already stored. Return it.
            await self.session.rollback()
            existing = await self.analyses.get_by_hash(analysis_hash)
            if existing is None:
                raise
            logger.info("Duplicate analysis request: returning id=%s", existing.id)
            return await self.get(user_id, existing.id)

        logger.info(
            "Analysis created: id=%s score=%.2f in %d ms",
            analysis.id,
            result.match_percentage,
            (time.perf_counter() - started) * 1000,
        )
        return Scorecard(analysis, jd, result.matched_skills, result.missing_skills)

    async def get(self, user_id: uuid.UUID, analysis_id: uuid.UUID) -> Scorecard:
        row = await self.analyses.get_for_user(analysis_id, user_id)
        if row is None:
            raise AnalysisNotFoundError()
        analysis, jd = row
        matches = await self.analyses.get_matches(analysis.id)
        gaps = await self.analyses.get_gaps(analysis.id)
        return Scorecard(
            analysis,
            jd,
            sorted(m.skill_name for m in matches),
            sorted(g.skill_name for g in gaps),
        )

    async def list_analyses(
        self, user_id: uuid.UUID, *, limit: int, offset: int
    ) -> list[tuple[Analysis, JobDescription]]:
        return await self.analyses.list_for_user(user_id, limit=limit, offset=offset)