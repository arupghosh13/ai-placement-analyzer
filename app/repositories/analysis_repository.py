"""Data access for analyses and their skill rows.

analyses has no user_id, so ownership is checked by joining to resumes.user_id.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Analysis, JobDescription, Resume, SkillGap, SkillMatch


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_with_results(
        self,
        analysis: Analysis,
        matches: list[dict],
        gaps: list[dict],
    ) -> Analysis:
        self.session.add(analysis)
        await self.session.flush()  # INSERT analyses; analysis.id is now set

        self.session.add_all([SkillMatch(analysis_id=analysis.id, **m) for m in matches])
        self.session.add_all([SkillGap(analysis_id=analysis.id, **g) for g in gaps])
        await self.session.flush()
        return analysis

    async def get_by_hash(self, analysis_hash: str) -> Analysis | None:
        stmt = select(Analysis).where(Analysis.analysis_hash == analysis_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_user(
        self, analysis_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[Analysis, JobDescription] | None:
        stmt = (
            select(Analysis, JobDescription)
            .select_from(Analysis)
            .join(Resume, Analysis.resume_id == Resume.id)
            .join(JobDescription, Analysis.job_description_id == JobDescription.id)
            .where(Analysis.id == analysis_id, Resume.user_id == user_id)
        )
        row = (await self.session.execute(stmt)).first()
        return (row[0], row[1]) if row else None

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[tuple[Analysis, JobDescription]]:
        stmt = (
            select(Analysis, JobDescription)
            .select_from(Analysis)
            .join(Resume, Analysis.resume_id == Resume.id)
            .join(JobDescription, Analysis.job_description_id == JobDescription.id)
            .where(Resume.user_id == user_id)
            .order_by(Analysis.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_matches(self, analysis_id: uuid.UUID) -> list[SkillMatch]:
        stmt = (
            select(SkillMatch)
            .where(SkillMatch.analysis_id == analysis_id)
            .order_by(SkillMatch.normalized_skill)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_gaps(self, analysis_id: uuid.UUID) -> list[SkillGap]:
        stmt = (
            select(SkillGap)
            .where(SkillGap.analysis_id == analysis_id)
            .order_by(SkillGap.normalized_skill)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())