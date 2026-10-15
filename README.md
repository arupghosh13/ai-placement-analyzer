## Phase 2: accounts, stored resumes and analyses

Run it locally:
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`. Set `DATABASE_URL` (Neon, format `postgresql+asyncpg://...?ssl=require`) and `JWT_SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`).
3. `alembic upgrade head`
4. `uvicorn app.main:app --reload`, then open `/docs`.

Endpoints (all under `/api/v1`): `POST /auth/register`, `POST /auth/login`, `POST /resumes/upload`, `GET /resumes`, `GET|DELETE /resumes/{id}`, `POST /analyses`, `GET /analyses`, `GET /analyses/{id}`.

Tests: `pytest tests/ -m "not integration"` (fast, no database) and `pytest tests/ -m integration` (uses the Neon database, rolled back after every test).

Latency (laptop in India to Neon Singapore, median of 5, `python -m scripts.measure_latency`): upload ___ ms, analysis ___ ms. Re-measured on the deployed app in Phase 10.