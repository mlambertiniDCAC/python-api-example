"""Carga datos de demo: un usuario por rol y menús para hoy. Idempotente.

Uso (con el stack arriba):
    docker compose exec api python scripts/seed_demo.py
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Menu, Role
from app.schemas.menu import MenuCreate
from app.schemas.user import UserCreate
from app.services import menus as menu_service
from app.services import users as user_service

PASSWORD = "demo1234"

USERS = [
    ("cliente@example.com", "Carla Cliente", Role.CLIENTE),
    ("cocina@example.com", "Martín Cocinero", Role.COCINA),
    ("delivery@example.com", "Diego Delivery", Role.DELIVERY),
]

MENUS = [
    ("Milanesa napolitana", "Con papas fritas caseras", "8500"),
    ("Ravioles de ricota", "Con salsa fileto o crema", "7200"),
    ("Ensalada César", "Pollo grillado, croutons y parmesano", "6400"),
    ("Flan casero", "Con dulce de leche y crema", "3500"),
]


def main() -> None:
    with SessionLocal() as db:
        users = {}
        for email, name, role in USERS:
            user = user_service.get_by_email(db, email)
            if not user:
                data = UserCreate(email=email, full_name=name, password=PASSWORD, role=role)
                user = user_service.create_user(db, data)
            users[role] = user

        chef = users[Role.COCINA]
        has_menus_today = db.scalar(
            select(Menu.id).where(Menu.chef_id == chef.id, Menu.available_on == date.today())
        )
        if not has_menus_today:
            for name, description, price in MENUS:
                data = MenuCreate(name=name, description=description, price=Decimal(price))
                menu_service.create_menu(db, chef, data)

    print(f"Usuarios demo (contraseña '{PASSWORD}'):")
    for email, _, role in USERS:
        print(f"  {role:<9} {email}")


if __name__ == "__main__":
    main()
