"""Test e2e manual: recorre todas las HU contra la API levantada.

Uso (con el stack arriba):
    docker compose exec api python scripts/e2e.py

Es re-ejecutable: cada corrida usa emails únicos.
"""

import os
import sys
import time

import httpx

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.environ["FIRST_ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["FIRST_ADMIN_PASSWORD"]
RUN = int(time.time())
PASSWORD = "secreto123"

client = httpx.Client(base_url=BASE_URL, timeout=10)
failures = 0


def check(description: str, response: httpx.Response, expected: int) -> dict | list | None:
    global failures
    ok = response.status_code == expected
    failures += not ok
    mark = "OK  " if ok else "FAIL"
    print(f"[{mark}] {description} -> {response.status_code}")
    if not ok:
        print(f"       esperado {expected}: {response.text}")
    return response.json() if response.content else None


def assert_true(description: str, condition: bool) -> None:
    global failures
    failures += not condition
    print(f"[{'OK  ' if condition else 'FAIL'}] {description}")


def login(email: str, password: str = PASSWORD) -> dict[str, str]:
    r = client.post("/auth/login", data={"username": email, "password": password})
    token = check(f"login {email}", r, 200)["access_token"]
    return {"Authorization": f"Bearer {token}"}


print("== Setup ==")
check("health", client.get("/health"), 200)
admin = login(ADMIN_EMAIL, ADMIN_PASSWORD)

print("\n== HU4: admin gestiona clientes y empleados ==")
users = {}
for role in ("cliente", "cocina", "delivery", "delivery2"):
    body = {
        "email": f"{role}.{RUN}@example.com",
        "full_name": f"{role} {RUN}",
        "password": PASSWORD,
    }
    users[role] = check(
        f"admin crea {role}",
        client.post("/users", json=body | {"role": role.rstrip("2")}, headers=admin),
        201,
    )

check(
    "email duplicado -> 409",
    client.post("/users", json=body | {"role": "cocina"}, headers=admin),
    409,
)
check(
    "admin no puede crear admins -> 422",
    client.post(
        "/users", json=body | {"email": f"x.{RUN}@example.com", "role": "admin"}, headers=admin
    ),
    422,
)
check(
    "admin modifica cliente",
    client.patch(
        f"/users/{users['cliente']['id']}", json={"full_name": "Cliente Renombrado"}, headers=admin
    ),
    200,
)
temp = check(
    "admin crea empleado temporal",
    client.post(
        "/users",
        json={
            "email": f"temp.{RUN}@example.com",
            "full_name": "Temp",
            "password": PASSWORD,
            "role": "delivery",
        },
        headers=admin,
    ),
    201,
)
check("admin elimina empleado", client.delete(f"/users/{temp['id']}", headers=admin), 204)
r = client.post("/auth/login", data={"username": temp["email"], "password": PASSWORD})
check("usuario eliminado no puede loguearse -> 401", r, 401)
check(
    "registro público crea cliente",
    client.post(
        "/auth/register",
        json={"email": f"web.{RUN}@example.com", "full_name": "Web", "password": PASSWORD},
    ),
    201,
)

cliente = login(users["cliente"]["email"])
cocina = login(users["cocina"]["email"])
delivery = login(users["delivery"]["email"])
delivery2 = login(users["delivery2"]["email"])

check("cliente no gestiona usuarios -> 403", client.get("/users", headers=cliente), 403)
check("cocina no gestiona usuarios -> 403", client.get("/users", headers=cocina), 403)

print("\n== HU7: cocina carga los menús del día ==")
milanesa = check(
    "cocina crea menú 'Milanesa napolitana'",
    client.post(
        "/menus",
        json={
            "name": f"Milanesa napolitana {RUN}",
            "description": "Con papas fritas",
            "price": "8500.00",
        },
        headers=cocina,
    ),
    201,
)
ravioles = check(
    "cocina crea menú 'Ravioles'",
    client.post(
        "/menus",
        json={"name": f"Ravioles {RUN}", "description": "De ricota con tuco", "price": "7200.50"},
        headers=cocina,
    ),
    201,
)
assert_true("el chef autor queda registrado", milanesa["chef"]["id"] == users["cocina"]["id"])
check(
    "cliente no puede cargar menús -> 403",
    client.post("/menus", json={"name": "X", "description": "X", "price": "1"}, headers=cliente),
    403,
)
check(
    "delivery no puede cargar menús -> 403",
    client.post("/menus", json={"name": "Xx", "description": "Xx", "price": "1"}, headers=delivery),
    403,
)
check(
    "menú en fecha pasada -> 422",
    client.post(
        "/menus",
        json={"name": "Viejo", "description": "Ayer", "price": "1", "available_on": "2000-01-01"},
        headers=cocina,
    ),
    422,
)

print("\n== HU2: cliente ve menús con filtros ==")
found = check(
    "filtro por nombre",
    client.get("/menus", params={"name": f"ravioles {RUN}"}, headers=cliente),
    200,
)
assert_true(
    "filtro por nombre devuelve solo Ravioles", [m["id"] for m in found] == [ravioles["id"]]
)
found = check(
    "filtro por chef + rango de precio",
    client.get(
        "/menus",
        params={"chef_id": users["cocina"]["id"], "min_price": 8000, "max_price": 9000},
        headers=cliente,
    ),
    200,
)
assert_true(
    "filtro por precio devuelve solo Milanesa", [m["id"] for m in found] == [milanesa["id"]]
)
found = check(
    "filtro por fecha de hoy",
    client.get("/menus", params={"available_on": milanesa["available_on"]}, headers=cliente),
    200,
)
assert_true("hoy incluye ambos menús", {milanesa["id"], ravioles["id"]} <= {m["id"] for m in found})

print("\n== HU1: cliente hace un pedido ==")
order = check(
    "cliente crea pedido",
    client.post(
        "/orders",
        json={
            "delivery_address": "Av. Siempreviva 742",
            "items": [
                {"menu_id": milanesa["id"], "quantity": 2},
                {"menu_id": ravioles["id"], "quantity": 1},
            ],
        },
        headers=cliente,
    ),
    201,
)
assert_true("pedido arranca 'solicitado'", order["status"] == "solicitado")
assert_true("total = 2*8500 + 7200.50", order["total"] == "24200.50")
check(
    "menú inexistente -> 422",
    client.post(
        "/orders",
        json={
            "delivery_address": "Av. Siempreviva 742",
            "items": [{"menu_id": 999999, "quantity": 1}],
        },
        headers=cliente,
    ),
    422,
)
check(
    "cocina no puede hacer pedidos -> 403",
    client.post(
        "/orders",
        json={
            "delivery_address": "Av. Siempreviva 742",
            "items": [{"menu_id": milanesa["id"], "quantity": 1}],
        },
        headers=cocina,
    ),
    403,
)
oid = order["id"]
mine = check("cliente ve sus pedidos", client.get("/orders", headers=cliente), 200)
assert_true("el pedido aparece en 'mis pedidos'", oid in [o["id"] for o in mine])

print("\n== HU3: admin manda a procesar ==")
check(
    "cocina no puede saltear al admin -> 403",
    client.post(f"/orders/{oid}/process", headers=cocina),
    403,
)
check(
    "cocina no puede marcar listo un pedido 'solicitado' -> 409",
    client.post(f"/orders/{oid}/ready", headers=cocina),
    409,
)
r = check("admin manda a procesar", client.post(f"/orders/{oid}/process", headers=admin), 200)
assert_true("estado 'en_proceso'", r["status"] == "en_proceso")
check("procesar dos veces -> 409", client.post(f"/orders/{oid}/process", headers=admin), 409)

print("\n== HU5: empleados ven su cola de trabajo ==")
queue = check("cocina ve su cola", client.get("/orders", headers=cocina), 200)
assert_true("el pedido está en la cola de cocina", oid in [o["id"] for o in queue])
assert_true(
    "la cola de cocina solo tiene 'en_proceso'", all(o["status"] == "en_proceso" for o in queue)
)
queue = check("delivery ve su cola", client.get("/orders", headers=delivery), 200)
assert_true("el pedido todavía no está en la cola de delivery", oid not in [o["id"] for o in queue])

print("\n== HU6: cocina termina el pedido ==")
check(
    "delivery no puede marcar listo -> 403",
    client.post(f"/orders/{oid}/ready", headers=delivery),
    403,
)
check("admin no puede marcar listo -> 403", client.post(f"/orders/{oid}/ready", headers=admin), 403)
r = check("cocina marca listo", client.post(f"/orders/{oid}/ready", headers=cocina), 200)
assert_true(
    "estado 'delivery' y cocinero registrado",
    r["status"] == "delivery" and r["cook_id"] == users["cocina"]["id"],
)
queue = check("delivery ve su cola", client.get("/orders", headers=delivery), 200)
assert_true("el pedido ahora está en la cola de delivery", oid in [o["id"] for o in queue])

print("\n== HU8: delivery retira y entrega el pedido ==")
check(
    "entregar sin retirar -> 409",
    client.post(f"/orders/{oid}/deliver", headers=delivery),
    409,
)
check("cocina no puede retirar -> 403", client.post(f"/orders/{oid}/pickup", headers=cocina), 403)
r = check("delivery retira el pedido", client.post(f"/orders/{oid}/pickup", headers=delivery), 200)
assert_true("repartidor asignado", r["delivery_person_id"] == users["delivery"]["id"])
assert_true("el pedido trae el nombre del cliente", r["client_name"] == "Cliente Renombrado")
check(
    "otro repartidor no puede retirarlo -> 409",
    client.post(f"/orders/{oid}/pickup", headers=delivery2),
    409,
)
queue = check("otro repartidor ve su cola", client.get("/orders", headers=delivery2), 200)
assert_true(
    "el pedido retirado no aparece para otro repartidor", oid not in [o["id"] for o in queue]
)
check(
    "cocina no puede marcar entregado -> 403",
    client.post(f"/orders/{oid}/deliver", headers=cocina),
    403,
)
check(
    "cliente no puede marcar entregado -> 403",
    client.post(f"/orders/{oid}/deliver", headers=cliente),
    403,
)
check(
    "otro repartidor no puede entregarlo -> 403",
    client.post(f"/orders/{oid}/deliver", headers=delivery2),
    403,
)
r = check("delivery marca entregado", client.post(f"/orders/{oid}/deliver", headers=delivery), 200)
assert_true(
    "estado 'entregado' y repartidor registrado",
    r["status"] == "entregado" and r["delivery_person_id"] == users["delivery"]["id"],
)
check("delivery ya no lo ve en su cola -> 404", client.get(f"/orders/{oid}", headers=delivery), 404)

print("\n== Admin controla todo ==")
r = check(
    "admin ve el pedido entregado",
    client.get("/orders", params={"status": "entregado"}, headers=admin),
    200,
)
assert_true("el pedido figura como entregado", oid in [o["id"] for o in r])
otro = login(f"web.{RUN}@example.com")
check("otro cliente no ve pedidos ajenos -> 404", client.get(f"/orders/{oid}", headers=otro), 404)

print(f"\n{'TODO OK' if failures == 0 else f'{failures} FALLA(S)'}")
sys.exit(1 if failures else 0)
