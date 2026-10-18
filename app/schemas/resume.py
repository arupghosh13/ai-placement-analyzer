"""Request and response shapes for the resume endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel


class ResumeUploadResponse(BaseModel):
    resume_id: uuid.UUID
    file_name: str
    status: str = "parsed"
    character_count: int


class ResumeResponse(BaseModel):
    resume_id: uuid.UUID
    file_name: str
    file_type: str
    created_at: datetime