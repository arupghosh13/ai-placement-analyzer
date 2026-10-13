# app/main.py

import logging
import logging.config
from contextlib import asynccontextmanager 

from fastapi import FastAPI, Request
from sqlalchemy import text  
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.analyze import router as analyze_router
from app.core.exceptions import (
    document_parsing_error_handler,
    insufficient_context_handler,
    validation_error_handler,
    global_exception_handler,
)
from app.db.session import engine 
from app.services.extractor import (
    DocumentParsingError,
    InsufficientContextError,
)

# ─────────────────────────────────────────
# LOGGING SETUP
# Simple console logging for Phase 1
# Phase 9 upgrades this to structured
# JSON file logging with request_id tracking
# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,   # ← This line. Forces reconfiguration even if
)                 #   uvicorn already set up the root logger first
logging.getLogger("app").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# LIFESPAN
# Everything before `yield` runs at startup,
# everything after it runs at shutdown
# ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("AI Placement Analyzer starting up")
    logger.info("Phase 2 — Database + Auth")
    logger.info("Docs available at: http://127.0.0.1:8000/docs")
    logger.info("=" * 50)

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Database connection failed at startup: %s", type(exc).__name__)
        raise
    logger.info("Database connection OK")

    yield

    await engine.dispose()
    logger.info("Database engine closed. AI Placement Analyzer shutting down. Goodbye.")


# ─────────────────────────────────────────
# APP INITIALIZATION
# ─────────────────────────────────────────

app = FastAPI(
    title="AI Placement Analyzer",
    description=(
        "Deterministic resume-to-JD gap analyzer. "
        "Phase 1: zero-hallucination set-based matching. "
        "No LLM in this phase — pure Python."
    ),
    version="0.1.0",
    docs_url="/docs",       # Swagger UI at /docs
    redoc_url="/redoc",     # ReDoc UI at /redoc
    lifespan=lifespan,
)


# ─────────────────────────────────────────
# CORS MIDDLEWARE
# Allows your future React frontend (Phase 10)
# to call this API from a different port
# ─────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Tightened in production Phase 10
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# EXCEPTION HANDLERS
# Registered here, fire automatically
# on any matching exception anywhere in app
# ─────────────────────────────────────────

app.add_exception_handler(
    DocumentParsingError,
    document_parsing_error_handler,
)
app.add_exception_handler(
    InsufficientContextError,
    insufficient_context_handler,
)
app.add_exception_handler(
    RequestValidationError,
    validation_error_handler,
)
app.add_exception_handler(
    Exception,
    global_exception_handler,
)


# ─────────────────────────────────────────
# ROUTERS
# Each router is a group of related endpoints
# Phase 2 adds: auth_router, resume_router
# Phase 3 adds: insights_router
# ─────────────────────────────────────────

app.include_router(
    analyze_router,
    prefix="/api/v1",
)


# ─────────────────────────────────────────
# HEALTH CHECK
# Always the first endpoint you test
# Confirms server is alive before anything else
# Standard in every production backend
# ─────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "phase": "Phase 1 — Deterministic Matching Engine",
        "message": "AI Placement Analyzer is running.",
    }
