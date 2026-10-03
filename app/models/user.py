from enum import StrEnum

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, str_enum


class Role(StrEnum):
    ADMIN = "admin"
    CLIENTE = "cliente"
    COCINA = "cocina"
    DELIVERY = "delivery"


EMPLOYEE_ROLES = {Role.COCINA, Role.DELIVERY}


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(str_enum(Role, "user_role"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
