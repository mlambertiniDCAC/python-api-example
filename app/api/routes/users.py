from fastapi import APIRouter, status

from app.api.deps import AdminUser, DbSession, Limit, Offset
from app.models import Role
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users (admin)"])


@router.get("", response_model=list[UserRead])
def list_users(
    db: DbSession,
    _: AdminUser,
    role: Role | None = None,
    is_active: bool | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    return user_service.list_users(db, role, is_active, limit, offset)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(db: DbSession, _: AdminUser, data: UserCreate):
    return user_service.create_user(db, data)


@router.get("/{user_id}", response_model=UserRead)
def get_user(db: DbSession, _: AdminUser, user_id: int):
    return user_service.get_managed_user(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(db: DbSession, _: AdminUser, user_id: int, data: UserUpdate):
    return user_service.update_user(db, user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(db: DbSession, _: AdminUser, user_id: int) -> None:
    """Baja lógica (`is_active=false`): el usuario no puede volver a loguearse."""
    user_service.deactivate_user(db, user_id)
