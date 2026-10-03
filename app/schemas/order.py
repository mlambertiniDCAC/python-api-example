from datetime import datetime
from decimal import Decimal

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.models import OrderStatus


class OrderItemCreate(BaseModel):
    menu_id: int
    quantity: int = Field(ge=1, le=20)


class OrderCreate(BaseModel):
    delivery_address: str = Field(min_length=5, max_length=255)
    items: list[OrderItemCreate] = Field(min_length=1, max_length=20)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_id: int
    menu_name: str = Field(validation_alias=AliasPath("menu", "name"))
    quantity: int
    unit_price: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    client_name: str = Field(validation_alias=AliasPath("client", "full_name"))
    status: OrderStatus
    delivery_address: str
    cook_id: int | None
    delivery_person_id: int | None
    items: list[OrderItemRead]
    total: Decimal
    created_at: datetime
    updated_at: datetime
