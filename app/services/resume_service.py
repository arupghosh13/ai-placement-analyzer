"""Resume business rules: upload, list, get, delete. No HTTP knowledge here."""
import asyncio
import hashlib
import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Resume
from app.repositories.resume_repository import ResumeRepository
from app.services.extractor import extract_text_from_file

logger = logging.getLogger(__name__)


class ResumeNotFoundError(Exception):
    """Resume does not exist OR belongs to another user (deliberately the same error)."""


def _clean_filename(filename: str) -> str:
    """Keep only the base name, capped at the column length. It is a label, never a path."""
    return filename.replace("\\", "/").split("/")[-1][:255]


class ResumeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.resumes = ResumeRepository(session)

    async def upload(
        self, user_id: uuid.UUID, file_bytes: bytes, filename: str
    ) -> tuple[Resume, int]:
        # pdfplumber is CPU-bound: run it in a worker thread so the event loop stays free.
        text = await asyncio.to_thread(extract_text_from_file, file_bytes, filename)
        text = text.replace("\x00", "")  # PostgreSQL TEXT cannot store NUL characters

        resume = await self.resumes.create(
            user_id=user_id,
            filename=_clean_filename(filename),
            file_type=os.path.splitext(filename)[1].lower().lstrip("."),
            raw_text=text,
            content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
        await self.session.commit()
        logger.info("Resume uploaded: id=%s chars=%d", resume.id, len(text))
        return resume, len(text)

    async def list_resumes(
        self, user_id: uuid.UUID, *, limit: int, offset: int
    ) -> list[Resume]:
        return await self.resumes.list_for_user(user_id, limit=limit, offset=offset)

    async def get(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
        resume = await self.resumes.get_for_user(resume_id, user_id)
        if resume is None:
            raise ResumeNotFoundError()
        return resume

    async def delete(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> None:
        if not await self.resumes.delete_for_user(resume_id, user_id):
            raise ResumeNotFoundError()
        await self.session.commit()
        logger.info("Resume deleted: id=%s", resume_id)