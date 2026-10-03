from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Enum de MySQL que persiste los *valores* (no los nombres) del StrEnum."""
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])
