"""Shared fixtures for the API tests.

Every API test runs inside ONE database transaction that is rolled back at the end,
so tests leave no rows behind. With join_transaction_mode="create_savepoint",
session.commit() inside the app only releases a SAVEPOINT and session.rollback()
only rolls back to it. Nothing is ever really committed.
"""
import io
import uuid
from types import SimpleNamespace

import pytest_asyncio
from docx import Document
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app

PASSWORD = "StrongPass123"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
RESUME_TEXT = (
    "Backend developer with two years of experience building services in Python "
    "and FastAPI. Comfortable with code reviews and clear documentation."
)
JD_TEXT = (
    "We are hiring a backend engineer with Python, FastAPI and Docker experience "
    "for our platform team."
)


def _docx_bytes(content: str) -> bytes:
    document = Document()
    document.add_paragraph(content)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest_asyncio.fixture
async def db_connection():
    # A fresh engine per test: each test has its own event loop.
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        yield connection
        await transaction.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_connection):
    session_factory = async_sessionmaker(
        bind=db_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_scalar(db_connection):
    """Run one raw SQL query inside the test's transaction and return one value."""

    async def run(sql: str, **params):
        result = await db_connection.execute(text(sql), params)
        return result.scalar_one()

    return run


@pytest_asyncio.fixture
async def make_user(client):
    """Register + log in a brand-new user and return its Authorization headers."""

    async def create() -> dict:
        email = f"user-{uuid.uuid4().hex[:10]}@example.com"
        body = {"email": email, "password": PASSWORD}
        registered = await client.post("/api/v1/auth/register", json=body)
        assert registered.status_code == 201, registered.text
        logged_in = await client.post("/api/v1/auth/login", json=body)
        assert logged_in.status_code == 200, logged_in.text
        return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}

    return create


@pytest_asyncio.fixture
async def upload_resume(client):
    async def upload(headers: dict, content: str = RESUME_TEXT, filename: str = "cv.docx"):
        files = {"resume_file": (filename, _docx_bytes(content), DOCX_MIME)}
        return await client.post("/api/v1/resumes/upload", files=files, headers=headers)

    return upload


@pytest_asyncio.fixture
async def create_analysis(client):
    async def create(
        headers: dict,
        resume_id: str,
        *,
        company: str = "Google",
        role: str = "Backend Engineer",
        jd_text: str = JD_TEXT,
    ):
        body = {
            "resume_id": resume_id,
            "company_name": company,
            "role_title": role,
            "jd_text": jd_text,
        }
        return await client.post("/api/v1/analyses", json=body, headers=headers)

    return create


@pytest_asyncio.fixture
async def owner(make_user, upload_resume):
    """A user who already has one uploaded resume."""
    headers = await make_user()
    response = await upload_resume(headers)
    assert response.status_code == 201, response.text
    return SimpleNamespace(headers=headers, resume_id=response.json()["resume_id"])