from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, verify_password
from app.models import Role
from app.schemas.user import ClientRegister, Token, UserCreate, UserRead
from app.services import users as user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """Login con email (campo `username`) y contraseña."""
    user = user_service.get_by_email(db, form.username)
    if not user or not user.is_active or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos")
    return Token(access_token=create_access_token(user.id))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(db: DbSession, data: ClientRegister):
    """Alta pública: siempre crea un usuario con rol `cliente`."""
    return user_service.create_user(db, UserCreate(**data.model_dump(), role=Role.CLIENTE))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser):
    return user
