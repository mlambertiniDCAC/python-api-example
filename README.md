# Menu API 🍝

API de **menús diarios y pedidos** hecha con FastAPI + MySQL. Los chefs cargan los menús
del día, los clientes piden, el admin manda a cocina, cocina prepara y delivery entrega.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · MySQL 8.4 · JWT · uv · Docker.

## Levantar

El `docker-compose.yml` levanta todo: **MySQL + API + front**. El front se construye desde su
repo, que tiene que estar clonado al lado de este (configurable con `FRONT_PATH`):

```
sandbox/
├── python-api-example/   # este repo
└── node-front-example/   # https://github.com/mlambertiniDCAC/node-front-example
```

```bash
cp .env.example .env      # ajustar contraseñas y JWT_SECRET_KEY
docker compose up -d --build
```

- Front: http://localhost:3000
- API: http://localhost:8000 · Swagger: http://localhost:8000/docs
- MySQL expuesto en el host en el puerto `3310` (para herramientas de datos/BI).

El navegador llama directo a la API (`http://localhost:8000`): esa URL se fija al construir el
front (build arg `VITE_API_URL`) y la API la habilita por CORS con `CORS_ORIGINS`. Si cambiás
`API_PORT` o `WEB_PORT`, ajustá `CORS_ORIGINS` en `.env`.

Al arrancar, el contenedor aplica las migraciones (`alembic upgrade head`) y garantiza el
admin por defecto (ver abajo).

## Admin por defecto

**Siempre existe un usuario administrador** que gestiona todo. Se garantiza en cada arranque de
la API (`app/initial_data.py`):

| Variable               | Valor por defecto   |
|------------------------|---------------------|
| `FIRST_ADMIN_EMAIL`    | `admin@example.com` |
| `FIRST_ADMIN_PASSWORD` | `admin12345`        |

- Si no existe, se crea. Si existe, se asegura que tenga rol `admin`, esté activo y use la
  contraseña del `.env`: el `.env` es la fuente de verdad (para cambiar la contraseña del admin,
  se edita ahí y se reinicia la API).
- Si las variables no están definidas, se usan los valores por defecto. En ese caso el log
  avisa: **cambiá la contraseña en `.env` antes de usarlo en serio.**
- Los admins no se crean ni se modifican por API.

## Primeros pasos

1. Levantar el stack (`docker compose up -d --build`).
2. Entrar a http://localhost:3000 con el admin por defecto.
3. En **Usuarios** (`/admin/usuarios`) crear los empleados con rol **Cocina** o **Delivery**
   (y clientes, si hace falta). Desde ahí también se editan y se dan de baja/reactivan.
4. Los clientes también pueden registrarse solos desde `/registro`.
5. Los empleados de cocina cargan los menús del día en **Mis menús** y ya se pueden hacer pedidos.

Datos de demo (un usuario por rol con contraseña `demo1234` y menús para hoy, idempotente):

```bash
docker compose exec api python scripts/seed_demo.py
```

## Test e2e

Con el stack arriba:

```bash
docker compose exec api python scripts/e2e.py
```

Recorre todas las historias de usuario y verifica que ningún rol pueda hacer tareas de otro.
Es re-ejecutable (usa emails únicos en cada corrida).

## Roles

| Rol        | Qué puede hacer                                                                    |
|------------|------------------------------------------------------------------------------------|
| `admin`    | Gestiona clientes y empleados. Ve todos los pedidos. Manda pedidos a cocina.        |
| `cliente`  | Ve menús con filtros. Hace pedidos y ve los suyos.                                  |
| `cocina`   | Carga/edita sus menús. Ve la cola `en_proceso` y marca pedidos como listos.         |
| `delivery` | Retira pedidos listos y marca como entregados los que retiró.                        |

## Ciclo de vida de un pedido

```
solicitado ──(admin: /process)──▶ en_proceso ──(cocina: /ready)──▶ delivery ──(delivery: /deliver)──▶ entregado
```

Cada transición tiene **un único rol dueño** (`app/services/orders.py::TRANSITIONS`), así los
roles no se pisan. Si el pedido no está en el estado esperado se responde `409`.

Dentro de `delivery`, el repartidor primero **retira** el pedido (`/pickup`): queda asignado a él
(`delivery_person_id`), desaparece de la cola de los demás y solo él puede marcarlo entregado.
Se registra quién cocinó (`cook_id`) y quién retiró/entregó (`delivery_person_id`).

## Endpoints

| Método | Ruta                      | Rol              | HU  |
|--------|---------------------------|------------------|-----|
| POST   | `/auth/register`          | público          | —   |
| POST   | `/auth/login`             | público          | —   |
| GET    | `/auth/me`                | cualquiera       | —   |
| GET    | `/users`                  | admin            | 4   |
| POST   | `/users`                  | admin            | 4   |
| GET    | `/users/{id}`             | admin            | 4   |
| PATCH  | `/users/{id}`             | admin            | 4   |
| DELETE | `/users/{id}`             | admin            | 4   |
| GET    | `/menus`                  | cualquiera       | 2   |
| GET    | `/menus/{id}`             | cualquiera       | 2   |
| POST   | `/menus`                  | cocina           | 7   |
| PATCH  | `/menus/{id}`             | cocina (autor)   | 7   |
| POST   | `/orders`                 | cliente          | 1   |
| GET    | `/orders`                 | según rol (*)    | 5   |
| GET    | `/orders/{id}`            | según rol (*)    | —   |
| POST   | `/orders/{id}/process`    | admin            | 3   |
| POST   | `/orders/{id}/ready`      | cocina           | 6   |
| POST   | `/orders/{id}/pickup`     | delivery         | 8   |
| POST   | `/orders/{id}/deliver`    | delivery (quien retiró) | 8 |

(*) admin ve todo; cliente ve los suyos; cocina ve los `en_proceso`; delivery ve los listos sin
retirar y los que retiró él. Las colas de empleados van del pedido más viejo al más nuevo.

**Filtros de `/menus`:** `name` (parcial), `chef_id`, `available_on`, `date_from`, `date_to`,
`min_price`, `max_price`, `limit`, `offset`.

### Ejemplo rápido

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -d "username=admin@example.com&password=admin12345" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s localhost:8000/orders -H "Authorization: Bearer $TOKEN"
```

## Decisiones

- **Baja lógica de usuarios:** `DELETE /users/{id}` pone `is_active=false`. Se conserva el
  historial de pedidos/menús y el usuario no puede volver a loguearse.
- **Los admins no se gestionan por API:** el admin por defecto sale de variables de entorno.
- **Pedidos solo de menús del día:** se rechazan menús de otras fechas. El precio se congela
  en `order_items.unit_price` al momento del pedido.
- **"Hoy"** depende de `TZ` (por defecto `America/Argentina/Buenos_Aires`).
- **Concurrencia:** las transiciones usan `SELECT ... FOR UPDATE` para que dos empleados no
  avancen el mismo pedido a la vez.

## Estructura

```
app/
├── api/
│   ├── deps.py          # sesión DB, usuario actual, guardas por rol
│   └── routes/          # auth, users, menus, orders (capa HTTP fina)
├── core/                # config (pydantic-settings), DB, seguridad (JWT + argon2)
├── models/              # modelos SQLAlchemy
├── schemas/             # schemas Pydantic de entrada/salida
├── services/            # lógica de negocio (reutilizable desde scripts/jobs)
└── initial_data.py      # garantiza el admin por defecto
alembic/                 # migraciones
scripts/                 # entrypoint del contenedor, test e2e y seed de demo
```

## Extender hacia automatización de datos

- La lógica vive en `app/services/` y no depende de HTTP: un script o job programado puede
  importarla directamente con una `SessionLocal()` (ver `scripts/seed_demo.py` como ejemplo).
- MySQL está expuesto en el puerto `3310` para conectar herramientas de análisis o ETL.
- Para un job periódico, alcanza con sumar un servicio al `docker-compose.yml` que reutilice
  la misma imagen con otro `command`.

## Desarrollo

```bash
uv sync                          # entorno local (incluye ruff)
uv run ruff check . && uv run ruff format .

# Nueva migración tras cambiar modelos (con el stack arriba):
docker compose run --rm --entrypoint "" -v "$PWD/alembic:/app/alembic" --user "$(id -u)" \
  api alembic revision --autogenerate -m "descripcion"
```
