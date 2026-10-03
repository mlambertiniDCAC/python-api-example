from fastapi import APIRouter

from app.api.deps import (
    AdminUser,
    ClientUser,
    CurrentUser,
    DbSession,
    DeliveryUser,
    KitchenUser,
    Limit,
    Offset,
)
from app.models import OrderStatus
from app.schemas.order import OrderCreate, OrderRead
from app.services import orders as order_service
from app.services.orders import OrderAction

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=201)
def create_order(db: DbSession, client: ClientUser, data: OrderCreate):
    """El cliente pide uno o más menús del día. El pedido arranca `solicitado`."""
    return order_service.create_order(db, client, data)


@router.get("", response_model=list[OrderRead])
def list_orders(
    db: DbSession,
    user: CurrentUser,
    status: OrderStatus | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    """
    Según el rol:
    - **admin**: todos los pedidos.
    - **cliente**: sus pedidos.
    - **cocina**: pedidos `en_proceso` (su cola, el más viejo primero).
    - **delivery**: pedidos en `delivery` sin retirar o retirados por él.
    """
    return order_service.list_orders(db, user, status, limit, offset)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(db: DbSession, user: CurrentUser, order_id: int):
    return order_service.get_order(db, user, order_id)


@router.post("/{order_id}/process", response_model=OrderRead)
def process_order(db: DbSession, admin: AdminUser, order_id: int):
    """Admin: `solicitado` → `en_proceso` (lo manda a cocina)."""
    return order_service.apply_transition(db, admin, order_id, OrderAction.PROCESS)


@router.post("/{order_id}/ready", response_model=OrderRead)
def mark_ready(db: DbSession, cook: KitchenUser, order_id: int):
    """Cocina: `en_proceso` → `delivery` (listo para que lo retire el delivery)."""
    return order_service.apply_transition(db, cook, order_id, OrderAction.READY)


@router.post("/{order_id}/pickup", response_model=OrderRead)
def pickup_order(db: DbSession, rider: DeliveryUser, order_id: int):
    """Delivery: retira un pedido listo (queda asignado a este repartidor)."""
    return order_service.pickup_order(db, rider, order_id)


@router.post("/{order_id}/deliver", response_model=OrderRead)
def mark_delivered(db: DbSession, rider: DeliveryUser, order_id: int):
    """Delivery: `delivery` → `entregado`. Solo el repartidor que lo retiró."""
    return order_service.apply_transition(db, rider, order_id, OrderAction.DELIVER)
