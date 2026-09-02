from typing import Annotated, Any, Awaitable, Callable

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import get_credentials_exception, get_forbidden_exception
from app.core.settings import settings
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user import get_user_by_id

# This tells FastAPI how to extract the token from the request header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# The tokenUrl is just for Swagger UI to know where the login endpoint is.


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Decodes the JWT and returns the current active user."""
    credentials_exception = get_credentials_exception()

    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt.public_key, algorithms=[settings.jwt.algorithm]
        )
        user_id_str: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if user_id_str is None or token_type != "access":
            raise credentials_exception

    except jwt.PyJWTError:
        raise credentials_exception

    user = await get_user_by_id(db, int(user_id_str))
    if user is None:
        raise credentials_exception

    return user


def require_role(required_role: UserRole) -> Callable[..., Awaitable[User]]:
    """Dependency factory to enforce specific roles (e.g., Admin only)."""

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role != required_role:
            raise get_forbidden_exception(required_role.value)
        return current_user

    return role_checker
