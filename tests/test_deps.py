import uuid

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import get_current_user_id
from app.core.security import NotAuthenticatedError, create_access_token


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_valid_token_returns_user_id():
    user_id = uuid.uuid4()
    assert await get_current_user_id(_creds(create_access_token(user_id))) == user_id


async def test_missing_credentials_rejected():
    with pytest.raises(NotAuthenticatedError):
        await get_current_user_id(None)


async def test_garbage_token_rejected():
    with pytest.raises(NotAuthenticatedError):
        await get_current_user_id(_creds("not.a.jwt"))