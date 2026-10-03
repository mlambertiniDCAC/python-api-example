from decimal import Decimal
from enum import StrEnum

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, str_enum
from app.models.menu import Menu
from app.models.user import User


class OrderStatus(StrEnum):
    SOLICITADO = "solicitado"
    EN_PROCESO = "en_proceso"
    DELIVERY = "delivery"
    ENTREGADO = "entregado"


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        str_enum(OrderStatus, "order_status"), default=OrderStatus.SOLICITADO, index=True
    )
    delivery_address: Mapped[str] = mapped_column(String(255))
    # Quién cocinó y quién retiró/entregó (trazabilidad para el admin).
    cook_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    delivery_person_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    client: Mapped[User] = relationship(foreign_keys=[client_id], lazy="joined")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def total(self) -> Decimal:
        return sum((item.unit_price * item.quantity for item in self.items), Decimal("0"))


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id"), index=True)
    quantity: Mapped[int]
    # Precio congelado al momento del pedido.
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")
    menu: Mapped[Menu] = relationship(lazy="joined")
