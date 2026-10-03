from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Menu, User
from app.schemas.menu import MenuCreate, MenuFilters, MenuUpdate
from app.services.exceptions import ForbiddenError, NotFoundError, UnprocessableError


def _ensure_not_past(available_on: date) -> None:
    if available_on < date.today():
        raise UnprocessableError("No se pueden cargar menús en fechas pasadas")


def create_menu(db: Session, chef: User, data: MenuCreate) -> Menu:
    _ensure_not_past(data.available_on)
    menu = Menu(**data.model_dump(), chef_id=chef.id)
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


def list_menus(db: Session, filters: MenuFilters) -> list[Menu]:
    stmt = select(Menu)
    if filters.name:
        stmt = stmt.where(Menu.name.contains(filters.name, autoescape=True))
    if filters.chef_id:
        stmt = stmt.where(Menu.chef_id == filters.chef_id)
    if filters.available_on:
        stmt = stmt.where(Menu.available_on == filters.available_on)
    if filters.date_from:
        stmt = stmt.where(Menu.available_on >= filters.date_from)
    if filters.date_to:
        stmt = stmt.where(Menu.available_on <= filters.date_to)
    if filters.min_price is not None:
        stmt = stmt.where(Menu.price >= filters.min_price)
    if filters.max_price is not None:
        stmt = stmt.where(Menu.price <= filters.max_price)
    stmt = (
        stmt.order_by(Menu.available_on.desc(), Menu.name)
        .limit(filters.limit)
        .offset(filters.offset)
    )
    return list(db.scalars(stmt))


def get_menu(db: Session, menu_id: int) -> Menu:
    menu = db.get(Menu, menu_id)
    if not menu:
        raise NotFoundError("Menú no encontrado")
    return menu


def update_menu(db: Session, chef: User, menu_id: int, data: MenuUpdate) -> Menu:
    menu = get_menu(db, menu_id)
    if menu.chef_id != chef.id:
        raise ForbiddenError("Solo el chef autor puede modificar este menú")
    changes = data.model_dump(exclude_unset=True)
    if "available_on" in changes:
        _ensure_not_past(changes["available_on"])
    for field, value in changes.items():
        setattr(menu, field, value)
    db.commit()
    db.refresh(menu)
    return menu
