from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, KitchenUser
from app.schemas.menu import MenuCreate, MenuFilters, MenuRead, MenuUpdate
from app.services import menus as menu_service

router = APIRouter(prefix="/menus", tags=["menus"])


@router.get("", response_model=list[MenuRead])
def list_menus(
    db: DbSession,
    _: CurrentUser,
    filters: Annotated[MenuFilters, Query()],
):
    return menu_service.list_menus(db, filters)


@router.get("/{menu_id}", response_model=MenuRead)
def get_menu(db: DbSession, _: CurrentUser, menu_id: int):
    return menu_service.get_menu(db, menu_id)


@router.post("", response_model=MenuRead, status_code=status.HTTP_201_CREATED)
def create_menu(db: DbSession, chef: KitchenUser, data: MenuCreate):
    """El chef carga un menú (por defecto para hoy). Queda como autor."""
    return menu_service.create_menu(db, chef, data)


@router.patch("/{menu_id}", response_model=MenuRead)
def update_menu(db: DbSession, chef: KitchenUser, menu_id: int, data: MenuUpdate):
    return menu_service.update_menu(db, chef, menu_id, data)
