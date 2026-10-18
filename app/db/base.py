"""Declarative base, constraint naming convention and reusable column recipes."""
import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.orm import DeclarativeBase, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

uuid_pk = Annotated[
    uuid.UUID,
    mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    ),
]

created_at_col = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now()),
]


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)