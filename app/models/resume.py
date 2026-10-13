"""resumes table: extracted text only, the uploaded file is never stored."""
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_col, uuid_pk


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = (
        CheckConstraint("file_type IN ('pdf', 'docx')", name="file_type_valid"),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))
    raw_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[created_at_col]