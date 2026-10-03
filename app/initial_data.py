"""Garantiza que exista el admin por defecto. Idempotente: se corre en cada arranque.

El admin se define por entorno (FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD) y el `.env` es la
fuente de verdad: si el usuario no existe se crea; si existe, se asegura que sea admin, esté
activo y tenga la contraseña configurada.
"""

import logging

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password, verify_password
from app.models import Role, User
from app.services.users import get_by_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PASSWORD = "admin12345"


def main() -> None:
    email, password = settings.FIRST_ADMIN_EMAIL, settings.FIRST_ADMIN_PASSWORD
    with SessionLocal() as db:
        admin = get_by_email(db, email)
        if not admin:
            db.add(
                User(
                    email=email,
                    full_name="Administrador",
                    hashed_password=hash_password(password),
                    role=Role.ADMIN,
                )
            )
            logger.info("Admin creado: %s", email)
        else:
            admin.role = Role.ADMIN
            admin.is_active = True
            if not verify_password(password, admin.hashed_password):
                admin.hashed_password = hash_password(password)
                logger.info("Contraseña del admin actualizada desde el entorno")
            logger.info("Admin verificado: %s", email)
        db.commit()

    if password == DEFAULT_PASSWORD:
        logger.warning("El admin usa la contraseña por defecto: cambiala en .env")


if __name__ == "__main__":
    main()
