from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class MenuCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=2, max_length=2000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    available_on: date = Field(default_factory=date.today)


class MenuUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, min_length=2, max_length=2000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    available_on: date | None = None


class ChefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class MenuRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: Decimal
    available_on: date
    chef: ChefRead


class MenuFilters(Pagination):
    """Filtros de búsqueda de menús + paginación (se reciben como query params)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Búsqueda parcial por nombre")
    chef_id: int | None = None
    available_on: date | None = Field(default=None, description="Fecha exacta (YYYY-MM-DD)")
    date_from: date | None = None
    date_to: date | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
