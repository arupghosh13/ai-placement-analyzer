"""Shared FastAPI dependencies."""
import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import NotAuthenticatedError, TokenError, decode_access_token
from app.db.session import get_db
from app.services.auth_service import AuthService
from app.services.resume_service import ResumeService
from app.services.analysis_service import AnalysisService

# auto_error=False: a missing header gives None here, so we raise our own 401
# in our own error shape instead of FastAPI's built-in one.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> uuid.UUID:
    """Stateless check: signature, expiry and type only. No database query."""
    if credentials is None:
        raise NotAuthenticatedError()
    try:
        return decode_access_token(credentials.credentials)
    except TokenError:
        raise NotAuthenticatedError() from None


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]


async def get_resume_service(db: AsyncSession = Depends(get_db)) -> ResumeService:
    return ResumeService(db)


async def get_analysis_service(db: AsyncSession = Depends(get_db)) -> AnalysisService:
    return AnalysisService(db)