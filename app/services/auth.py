from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.repositories.user import create_user, get_user_by_email
from app.schemas.auth import Token, UserRequest, UserResponse


async def register(db: AsyncSession, user_in: UserRequest) -> UserResponse:
    """Building logic for registering a user."""
    existing_user = await get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered."
        )

    user_data = user_in.model_dump()
    user_data["hashed_password"] = hash_password(user_data.pop("password"))

    new_user = await create_user(db, user_data)
    return UserResponse.model_validate(new_user)


async def login(db: AsyncSession, email: str, password: str) -> Token:
    """Business logic for logging in."""
    user = await get_user_by_email(db, email)

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return Token(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )
