"""Latency check for Phase 2: upload (< 1 s) and analysis (< 2 s).

Start the API first (uvicorn app.main:app), then run from the project root:
    python -m scripts.measure_latency                        (generates a small DOCX resume)
    python -m scripts.measure_latency "C:\\path\\resume.pdf"   (uses your real resume)

It creates a temporary user and deletes that user (and everything it owns) at the end.
Set API_BASE_URL to test a deployed API instead of localhost.
"""
import asyncio
import io
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

import httpx
from docx import Document
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
ROUNDS = 6  # the first round is a warm-up and is dropped
UPLOAD_LIMIT_MS = 1000
ANALYSIS_LIMIT_MS = 2000
PASSWORD = "StrongPass123"
JD_TEXT = (
    "We are hiring a backend engineer with Python, FastAPI, PostgreSQL, Docker, "
    "REST API development, Git and pytest experience."
)
MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def sample_resume() -> tuple[str, bytes, str]:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        return path.name, path.read_bytes(), MIME[path.suffix.lower()]
    document = Document()
    for _ in range(12):
        document.add_paragraph(
            "Backend developer building REST services with Python, FastAPI and PostgreSQL. "
            "Used Git daily, wrote unit tests, and reviewed pull requests with the team."
        )
    buffer = io.BytesIO()
    document.save(buffer)
    return "latency-resume.docx", buffer.getvalue(), MIME[".docx"]


async def timed(call):
    start = time.perf_counter()
    response = await call
    return response, (time.perf_counter() - start) * 1000


def report(label: str, samples: list[float], limit: float | None = None) -> float:
    samples = samples[1:]  # drop the warm-up round
    median = statistics.median(samples)
    verdict = ""
    if limit is not None:
        verdict = f"   limit {limit:.0f} ms: {'PASS' if median < limit else 'FAIL'}"
    print(
        f"{label:<14} min {min(samples):>5.0f} | median {median:>5.0f} | "
        f"max {max(samples):>5.0f} ms{verdict}"
    )
    return median


def require(response: httpx.Response, expected: int, what: str) -> None:
    if response.status_code != expected:
        print(f"{what} failed: {response.status_code} {response.text[:200]}")
        raise SystemExit(1)


async def main() -> None:
    filename, content, mime = sample_resume()
    engine = create_async_engine(get_settings().database_url)
    email = f"latency-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))  # warm-up: connect and SSL handshake
            rtts = []
            for _ in range(10):
                start = time.perf_counter()
                await conn.execute(text("SELECT 1"))
                rtts.append((time.perf_counter() - start) * 1000)
        rtt = statistics.median(rtts)
        print(f"Database round trip (median of 10): {rtt:.0f} ms\n")

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
            body = {"email": email, "password": PASSWORD}
            registered, reg_ms = await timed(client.post("/auth/register", json=body))
            require(registered, 201, "register")
            logged_in, login_ms = await timed(client.post("/auth/login", json=body))
            require(logged_in, 200, "login")
            headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
            print(f"register {reg_ms:.0f} ms | login {login_ms:.0f} ms (informational)\n")

            uploads, resume_ids = [], []
            for _ in range(ROUNDS):
                files = {"resume_file": (filename, content, mime)}
                response, ms = await timed(client.post("/resumes/upload", files=files, headers=headers))
                require(response, 201, "upload")
                uploads.append(ms)
                resume_ids.append(response.json()["resume_id"])

            analyses, analysis_ids = [], []
            for i in range(ROUNDS):  # a different company each time, so none is a duplicate
                payload = {
                    "resume_id": resume_ids[0],
                    "company_name": f"Company {i}",
                    "role_title": "Backend Engineer",
                    "jd_text": JD_TEXT,
                }
                response, ms = await timed(client.post("/analyses", json=payload, headers=headers))
                require(response, 200, "analysis")
                analyses.append(ms)
                analysis_ids.append(response.json()["analysis_id"])

            details, listings = [], []
            for analysis_id in analysis_ids:
                response, ms = await timed(client.get(f"/analyses/{analysis_id}", headers=headers))
                require(response, 200, "get analysis")
                details.append(ms)
                response, ms = await timed(client.get("/analyses", headers=headers))
                require(response, 200, "list analyses")
                listings.append(ms)

        upload_median = report("upload", uploads, UPLOAD_LIMIT_MS)
        analysis_median = report("analysis", analyses, ANALYSIS_LIMIT_MS)
        report("get analysis", details)
        report("list analyses", listings)
        print(
            f"\nIn database-round-trip units: upload ~ {upload_median / rtt:.1f}, "
            f"analysis ~ {analysis_median / rtt:.1f}"
        )
    except httpx.ConnectError:
        print("Cannot reach the API. Start it first: uvicorn app.main:app")
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM users WHERE email = :e"), {"e": email})
        await engine.dispose()
        print("Temporary user removed.")


asyncio.run(main())