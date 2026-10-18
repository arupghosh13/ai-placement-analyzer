"""Request and response shapes for the auth endpoints."""
import uuid

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterResponse(BaseModel):
    user_id: uuid.UUID


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"