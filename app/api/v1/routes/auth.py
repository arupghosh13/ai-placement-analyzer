"""Auth endpoints. Orchestration only: all rules live in AuthService."""
from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    user = await service.register(body.email, body.password)
    return RegisterResponse(user_id=user.id)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    token = await service.login(body.email, body.password)
    return TokenResponse(access_token=token)