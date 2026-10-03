from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Role, User
from app.schemas.user import UserCreate, UserUpdate
from app.services.exceptions import ConflictError, NotFoundError


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, data: UserCreate) -> User:
    if get_by_email(db, data.email):
        raise ConflictError("Ya existe un usuario con ese email")
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: Session, role: Role | None, is_active: bool | None, limit: int, offset: int
) -> list[User]:
    stmt = select(User).where(User.role != Role.ADMIN)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    return list(db.scalars(stmt.order_by(User.id).limit(limit).offset(offset)))


def get_managed_user(db: Session, user_id: int) -> User:
    """Usuarios que el admin puede gestionar: clientes y empleados."""
    user = db.get(User, user_id)
    if not user or user.role == Role.ADMIN:
        raise NotFoundError("Usuario no encontrado")
    return user


def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
    user = get_managed_user(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"] != user.email and get_by_email(db, changes["email"]):
        raise ConflictError("Ya existe un usuario con ese email")
    if password := changes.pop("password", None):
        user.hashed_password = hash_password(password)
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: int) -> None:
    # Baja lógica: se conserva el historial de pedidos y menús del usuario.
    user = get_managed_user(db, user_id)
    user.is_active = False
    db.commit()
