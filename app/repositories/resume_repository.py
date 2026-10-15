"""Data access for resumes. Every read and delete is scoped to the owning user."""
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Resume


class ResumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        filename: str,
        file_type: str,
        raw_text: str,
        content_hash: str,
    ) -> Resume:
        resume = Resume(
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            raw_text=raw_text,
            content_hash=content_hash,
        )
        self.session.add(resume)
        await self.session.flush()
        return resume

    async def get_for_user(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> Resume | None:
        stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Resume]:
        stmt = (
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_for_user(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = delete(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0