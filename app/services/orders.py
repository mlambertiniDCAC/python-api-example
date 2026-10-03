from collections import Counter
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models import Menu, Order, OrderItem, OrderStatus, Role, User
from app.schemas.order import OrderCreate
from app.services.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnprocessableError,
)


class OrderAction(StrEnum):
    PROCESS = "process"
    READY = "ready"
    DELIVER = "deliver"


@dataclass(frozen=True)
class Transition:
    role: Role
    from_status: OrderStatus
    to_status: OrderStatus


# Cada transición tiene un único rol dueño: así los roles no se pisan las tareas.
TRANSITIONS: dict[OrderAction, Transition] = {
    OrderAction.PROCESS: Transition(Role.ADMIN, OrderStatus.SOLICITADO, OrderStatus.EN_PROCESO),
    OrderAction.READY: Transition(Role.COCINA, OrderStatus.EN_PROCESO, OrderStatus.DELIVERY),
    OrderAction.DELIVER: Transition(Role.DELIVERY, OrderStatus.DELIVERY, OrderStatus.ENTREGADO),
}

# Cola de trabajo de cada empleado: los pedidos que le toca procesar.
EMPLOYEE_QUEUE: dict[Role, OrderStatus] = {
    Role.COCINA: OrderStatus.EN_PROCESO,
    Role.DELIVERY: OrderStatus.DELIVERY,
}


def create_order(db: Session, client: User, data: OrderCreate) -> Order:
    quantities = Counter()
    for item in data.items:
        quantities[item.menu_id] += item.quantity

    menus = {
        m.id: m
        for m in db.scalars(
            select(Menu).where(Menu.id.in_(quantities), Menu.available_on == date.today())
        )
    }
    missing = sorted(set(quantities) - set(menus))
    if missing:
        raise UnprocessableError(f"Menús inexistentes o no disponibles hoy: {missing}")

    order = Order(
        client_id=client.id,
        status=OrderStatus.SOLICITADO,
        delivery_address=data.delivery_address,
        items=[
            OrderItem(menu_id=menu_id, quantity=qty, unit_price=menus[menu_id].price)
            for menu_id, qty in quantities.items()
        ],
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _scoped(stmt: Select, user: User) -> Select:
    """Restringe la consulta a los pedidos que el usuario puede ver."""
    if user.role == Role.CLIENTE:
        return stmt.where(Order.client_id == user.id)
    if user.role == Role.DELIVERY:
        # Pedidos listos sin retirar + los que retiró este repartidor.
        return stmt.where(
            Order.status == OrderStatus.DELIVERY,
            or_(Order.delivery_person_id.is_(None), Order.delivery_person_id == user.id),
        )
    if user.role in EMPLOYEE_QUEUE:
        return stmt.where(Order.status == EMPLOYEE_QUEUE[user.role])
    return stmt  # admin: ve todo


def list_orders(
    db: Session, user: User, status: OrderStatus | None, limit: int, offset: int
) -> list[Order]:
    stmt = _scoped(select(Order), user)
    if status:
        stmt = stmt.where(Order.status == status)
    # Empleados: FIFO (el más viejo primero). Resto: lo más reciente primero.
    order_by = Order.created_at.asc() if user.role in EMPLOYEE_QUEUE else Order.created_at.desc()
    stmt = stmt.order_by(order_by, Order.id).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_order(db: Session, user: User, order_id: int) -> Order:
    order = db.scalar(_scoped(select(Order).where(Order.id == order_id), user))
    if not order:
        raise NotFoundError("Pedido no encontrado")
    return order


def _lock_order(db: Session, order_id: int) -> Order:
    # FOR UPDATE: evita que dos empleados modifiquen el mismo pedido a la vez.
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if not order:
        raise NotFoundError("Pedido no encontrado")
    return order


def _expect_status(order: Order, expected: OrderStatus) -> None:
    if order.status != expected:
        raise ConflictError(f"El pedido está '{order.status}', se esperaba '{expected}'")


def pickup_order(db: Session, rider: User, order_id: int) -> Order:
    """El repartidor retira el pedido: queda asignado a él y deja de verlo el resto."""
    order = _lock_order(db, order_id)
    _expect_status(order, OrderStatus.DELIVERY)
    if order.delivery_person_id is not None:
        raise ConflictError("El pedido ya fue retirado por un repartidor")
    order.delivery_person_id = rider.id
    db.commit()
    db.refresh(order)
    return order


def apply_transition(db: Session, user: User, order_id: int, action: OrderAction) -> Order:
    transition = TRANSITIONS[action]
    order = _lock_order(db, order_id)
    _expect_status(order, transition.from_status)
    if action is OrderAction.DELIVER:
        if order.delivery_person_id is None:
            raise ConflictError("El pedido debe retirarse antes de marcarse como entregado")
        if order.delivery_person_id != user.id:
            raise ForbiddenError("El pedido lo retiró otro repartidor")
    order.status = transition.to_status
    if action is OrderAction.READY:
        order.cook_id = user.id
    db.commit()
    db.refresh(order)
    return order
