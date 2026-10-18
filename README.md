# AI Placement Analyzer — Phase 1: deterministic matching engine

Upload a resume (.pdf or .docx) and a job description, and get back matched skills, missing skills and a match percentage. No database, no LLM, no login. Matching is plain Python set math, and nothing is written to disk (files are parsed in memory).

Run it locally:

1. `python -m venv venv`, then `venv\Scripts\activate` (Windows PowerShell)
2. `pip install -r requirements.txt`
3. `uvicorn app.main:app --reload`, then open `/docs`

Endpoints: `GET /health` and `POST /api/v1/analyze/` (note the trailing slash).

`POST /api/v1/analyze/` takes `multipart/form-data`:
- `resume_file`: .pdf or .docx, max 5 MB
- `jd_text`: 50 to 10000 characters
- `company_name`, `role_title`: optional

Example response:

```json
{
  "analysis_id": "3f9983c8-4a9a-4e3a-86c3-1a85ed6850af",
  "status": "completed",
  "company_name": "Google",
  "role_title": "Backend Engineer",
  "metrics": {
    "match_percentage": 62.5,
    "matched_skills": ["fastapi", "git", "postgresql", "python", "rest"],
    "missing_skills": ["api", "docker", "pytest"],
    "total_jd_skills": 8,
    "total_resume_skills": 25
  },
  "ai_insights_ready": false,
  "created_at": "2026-10-08T07:49:35.565323+00:00"
}
```

Errors always use one shape: `{success, error_code, message, timestamp}`. Codes: `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, `DOCUMENT_PARSING_FAILED`, `EMPTY_DOCUMENT`, `INSUFFICIENT_CONTEXT` (extracted text under 50 characters, returns the "I don't know" fallback fields), `VALIDATION_ERROR`, `INTERNAL_SERVER_ERROR`.

How matching works: skills are found by keyword and phrase lookup against a dictionary of about 200 skills. A small synonym map lets, for example, PostgreSQL satisfy a SQL requirement. Missing = JD skills minus resume skills, and match % = matched / JD skills x 100.

Known limits (planned for Phase 4): generic words such as "api" and "rest" can be picked up as skills, and skills outside the dictionary are not detected.

Tests: `pytest tests/ -v` (no database or network needed).
Latency (local, Postman, real PDF resume + JD): 124 ms for `POST /api/v1/analyze/` (target under 2000 ms).
## Phase 2: accounts, stored resumes and analyses

Run it locally:
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`. Set `DATABASE_URL` (Neon, format `postgresql+asyncpg://...?ssl=require`) and `JWT_SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`).
3. `alembic upgrade head`
4. `uvicorn app.main:app --reload`, then open `/docs`.

Endpoints (all under `/api/v1`): `POST /auth/register`, `POST /auth/login`, `POST /resumes/upload`, `GET /resumes`, `GET|DELETE /resumes/{id}`, `POST /analyses`, `GET /analyses`, `GET /analyses/{id}`.

Tests: `pytest tests/ -m "not integration"` (fast, no database) and `pytest tests/ -m integration` (uses the Neon database, rolled back after every test).

Latency (laptop in India to Neon Singapore, median of 5, `python -m scripts.measure_latency`): upload ___ ms, analysis ___ ms. Re-measured on the deployed app in Phase 10.