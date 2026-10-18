"""Data access for job descriptions."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobDescription


class JobDescriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        company_name: str,
        role_title: str,
        raw_text: str,
        content_hash: str,
    ) -> JobDescription:
        jd = JobDescription(
            user_id=user_id,
            company_name=company_name,
            role_title=role_title,
            raw_text=raw_text,
            content_hash=content_hash,
        )
        self.session.add(jd)
        await self.session.flush()
        return jd