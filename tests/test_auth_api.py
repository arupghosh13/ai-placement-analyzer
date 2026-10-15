import uuid

import pytest

pytestmark = pytest.mark.integration

PASSWORD = "StrongPass123"
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


async def test_register_creates_a_user(client):
    response = await client.post(REGISTER, json={"email": _email(), "password": PASSWORD})
    assert response.status_code == 201
    assert uuid.UUID(response.json()["user_id"])


async def test_duplicate_email_is_rejected_ignoring_case(client):
    email = _email()
    first = await client.post(REGISTER, json={"email": email, "password": PASSWORD})
    assert first.status_code == 201
    second = await client.post(REGISTER, json={"email": email.upper(), "password": PASSWORD})
    assert second.status_code == 409
    assert second.json()["error_code"] == "EMAIL_ALREADY_REGISTERED"


async def test_short_password_is_rejected_without_echoing_it(client):
    secret = "Zq9!kLm"  # 7 characters
    response = await client.post(REGISTER, json={"email": _email(), "password": secret})
    assert response.status_code == 422
    assert secret not in response.text


async def test_invalid_email_is_rejected(client):
    response = await client.post(REGISTER, json={"email": "not-an-email", "password": PASSWORD})
    assert response.status_code == 422


async def test_login_returns_a_bearer_token(client):
    body = {"email": _email(), "password": PASSWORD}
    await client.post(REGISTER, json=body)
    response = await client.post(LOGIN, json=body)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"].count(".") == 2  # header.payload.signature


async def test_wrong_password_and_unknown_email_look_identical(client):
    email = _email()
    await client.post(REGISTER, json={"email": email, "password": PASSWORD})
    wrong = await client.post(LOGIN, json={"email": email, "password": "WrongPass999"})
    unknown = await client.post(LOGIN, json={"email": _email(), "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error_code"] == unknown.json()["error_code"] == "INVALID_CREDENTIALS"
    assert wrong.json()["message"] == unknown.json()["message"]


async def test_protected_route_needs_a_valid_token(client):
    missing = await client.get("/api/v1/resumes")
    assert missing.status_code == 401
    assert missing.json()["error_code"] == "NOT_AUTHENTICATED"
    garbage = await client.get("/api/v1/resumes", headers={"Authorization": "Bearer abc"})
    assert garbage.status_code == 401


async def test_password_is_stored_as_an_argon2id_hash(client, db_scalar):
    email = _email()
    await client.post(REGISTER, json={"email": email, "password": PASSWORD})
    stored = await db_scalar("SELECT password_hash FROM users WHERE email = :e", e=email)
    assert stored.startswith("$argon2id$")
    assert PASSWORD not in stored