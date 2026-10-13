# app/core/exceptions.py

import logging
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.services.extractor import (
    DocumentParsingError,
    InsufficientContextError,
)

from app.services.auth_service import EmailAlreadyRegisteredError, InvalidCredentialsError

from app.core.security import NotAuthenticatedError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# HELPER
# Single place that builds every error response
# Change the shape here → changes everywhere
# ─────────────────────────────────────────

def _build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    extra: dict | None = None,
) -> JSONResponse:

    content = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if extra:
        content.update(extra)

    return JSONResponse(
        status_code=status_code,
        content=content,
    )


# ─────────────────────────────────────────
# HANDLER 1: Document Parsing Errors
# Triggered by extractor.py when file is
# broken, encrypted, wrong type, too large
# ─────────────────────────────────────────

async def document_parsing_error_handler(
    request: Request,
    exc: DocumentParsingError,
) -> JSONResponse:
    logger.error(
        f"DocumentParsingError on {request.url.path} — "
        f"code: {exc.error_code} | message: {exc.message}"
    )
    return _build_error_response(
        status_code=400,
        error_code=exc.error_code,
        message=exc.message,
    )


# ─────────────────────────────────────────
# HANDLER 2: Insufficient Context
# Triggered when extracted text < 50 chars
# Returns your "I don't have enough context" response
# ─────────────────────────────────────────

async def insufficient_context_handler(
    request: Request,
    exc: InsufficientContextError,
) -> JSONResponse:
    logger.warning(
        f"InsufficientContextError on {request.url.path} — "
        f"text too short to analyze safely"
    )
    return _build_error_response(
        status_code=400,
        error_code=exc.error_code,
        message="Insufficient context for analysis.",
        extra={
            "has_sufficient_context": False,
            "missing_skills_analysis": [],
            "interview_questions": [],
            "fallback_message": (
                "I don't know. The provided resume or "
                "job description does not contain enough explicit context "  
                "to safely extract or analyze these placement metrics."
            ),
        },
    )


# ─────────────────────────────────────────
# HANDLER 3: Pydantic Validation Errors
# Triggered automatically when request data
# fails schema validation (wrong type,
# missing required field, too short, etc.)
# ─────────────────────────────────────────

async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    # Extract the first validation error for a clean message
    errors = exc.errors()
    first_error = errors[0] if errors else {}

    field = " → ".join(str(loc) for loc in first_error.get("loc", []))
    reason = first_error.get("msg", "Invalid input")

    logger.warning(
        f"ValidationError on {request.url.path} — "
        f"field: '{field}' | reason: '{reason}'"
    )
    return _build_error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message=f"Invalid input at '{field}': {reason}",
    )


# ─────────────────────────────────────────
# HANDLER 4: Catch-All
# Last line of defense — catches anything
# not handled above (unexpected crashes,
# library errors, etc.)
# Never exposes internal details to user
# ─────────────────────────────────────────

async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        f"Unhandled exception on {request.url.path} — "
        f"type: {type(exc).__name__} | detail: {str(exc)}",
        exc_info=True,   # Logs full traceback to console
    )
    return _build_error_response(
        status_code=500,
        error_code="INTERNAL_SERVER_ERROR",
        message=(
            "An unexpected error occurred. "
            "Please try again later."
        ),
    )




async def email_already_registered_handler(request: Request, exc: EmailAlreadyRegisteredError):
    return _build_error_response(
        409, "EMAIL_ALREADY_REGISTERED", "An account with this email already exists."
    )


async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
    return _build_error_response(401, "INVALID_CREDENTIALS", "Incorrect email or password.")


async def not_authenticated_handler(request: Request, exc: NotAuthenticatedError):
    return _build_error_response(
        401, "NOT_AUTHENTICATED", "Authentication required: missing, invalid or expired token."
    )