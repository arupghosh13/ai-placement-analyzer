"""Auth business rules: register and login. No HTTP knowledge here."""
import asyncio
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# Hashed once at import. Login verifies against it when the email does not exist,
# so "unknown email" and "wrong password" take about the same time.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class EmailAlreadyRegisteredError(Exception):
    """The email already belongs to another account."""


class InvalidCredentialsError(Exception):
    """Unknown email OR wrong password. Deliberately one error for both."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def register(self, email: str, password: str) -> User:
        password_hash = await asyncio.to_thread(hash_password, password)
        try:
            user = await self.users.create(
                email=normalize_email(email), password_hash=password_hash
            )
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise EmailAlreadyRegisteredError() from None
        logger.info("User registered: id=%s", user.id)
        return user

    async def login(self, email: str, password: str) -> str:
        user = await self.users.get_by_email(normalize_email(email))
        stored_hash = user.password_hash if user else _DUMMY_HASH
        password_ok = await asyncio.to_thread(verify_password, password, stored_hash)
        if user is None or not password_ok:
            logger.warning("Failed login attempt")
            raise InvalidCredentialsError()
        return create_access_token(user.id)