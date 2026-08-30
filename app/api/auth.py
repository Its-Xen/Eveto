from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import Token, UserRequest, UserResponse
from app.services.auth import login, register

router = APIRouter()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_api(
    user_in: UserRequest, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Register a new user"""
    return await register(db, user_in)


@router.post("/login", response_model=Token)
async def login_api(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> Token:
    """Login and get access/refresh tokens"""
    return await login(db, form_data.username, form_data.password)
