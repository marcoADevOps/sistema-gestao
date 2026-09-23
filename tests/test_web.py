import os

os.environ["DATABASE_URL"] = "sqlite:///./test_web.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_dashboard_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "Sistema de Gestão" in response.text


def test_create_product_via_form_redirects_and_persists():
    response = client.post(
        "/web/products",
        data={"name": "Borracha", "price": "1.5", "stock_quantity": "20"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    products = client.get("/api/products/").json()
    assert any(p["name"] == "Borracha" for p in products)


def test_create_client_via_form():
    response = client.post(
        "/web/clients",
        data={"name": "Maria Souza", "phone": "61988887777", "email": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303

    clients = client.get("/api/clients/").json()
    assert any(c["name"] == "Maria Souza" for c in clients)


def test_create_sale_via_form_reduces_stock():
    product = client.post(
        "/api/products/", json={"name": "Régua", "price": 3.0, "stock_quantity": 10}
    ).json()

    response = client.post(
        "/web/sales",
        data={"product_id": str(product["id"]), "quantity": "4", "client_id": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    updated = client.get(f"/api/products/{product['id']}").json()
    assert updated["stock_quantity"] == 6


def test_create_sale_via_form_insufficient_stock_redirects_with_error():
    product = client.post(
        "/api/products/", json={"name": "Tesoura", "price": 8.0, "stock_quantity": 1}
    ).json()

    response = client.post(
        "/web/sales",
        data={"product_id": str(product["id"]), "quantity": "5", "client_id": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=" in response.headers["location"]


def test_edit_product_form_loads_with_current_values():
    product = client.post(
        "/api/products/", json={"name": "Apontador", "price": 4.0, "stock_quantity": 15}
    ).json()

    response = client.get(f"/web/products/{product['id']}/edit")
    assert response.status_code == 200
    assert "Apontador" in response.text


def test_edit_product_submit_updates_values():
    product = client.post(
        "/api/products/", json={"name": "Lapiseira", "price": 6.0, "stock_quantity": 5}
    ).json()

    response = client.post(
        f"/web/products/{product['id']}/edit",
        data={"name": "Lapiseira 0.7mm", "price": "7.5", "stock_quantity": "12"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    updated = client.get(f"/api/products/{product['id']}").json()
    assert updated["name"] == "Lapiseira 0.7mm"
    assert updated["price"] == 7.5
    assert updated["stock_quantity"] == 12


def test_edit_client_submit_updates_values():
    created = client.post(
        "/api/clients/", json={"name": "Ana Lima", "phone": "61911112222"}
    ).json()

    response = client.post(
        f"/web/clients/{created['id']}/edit",
        data={"name": "Ana Lima Souza", "phone": "61999998888", "email": "ana@exemplo.com"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    updated = client.get("/api/clients/").json()
    match = next(c for c in updated if c["id"] == created["id"])
    assert match["name"] == "Ana Lima Souza"
    assert match["email"] == "ana@exemplo.com"


def test_delete_product_without_sales_succeeds():
    product = client.post(
        "/api/products/", json={"name": "Clipe", "price": 0.5, "stock_quantity": 100}
    ).json()

    response = client.post(f"/web/products/{product['id']}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert "error=" not in response.headers["location"]

    remaining = client.get("/api/products/").json()
    assert all(p["id"] != product["id"] for p in remaining)


def test_delete_product_with_sales_is_blocked():
    product = client.post(
        "/api/products/", json={"name": "Grampeador", "price": 20.0, "stock_quantity": 5}
    ).json()
    client.post(
        "/api/sales/", json={"items": [{"product_id": product["id"], "quantity": 1}]}
    )

    response = client.post(f"/web/products/{product['id']}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert "error=" in response.headers["location"]

    # continua existindo, não foi excluído
    remaining = client.get("/api/products/").json()
    assert any(p["id"] == product["id"] for p in remaining)


def test_delete_client_with_sales_is_blocked():
    created_client = client.post("/api/clients/", json={"name": "Pedro Alves"}).json()
    product = client.post(
        "/api/products/", json={"name": "Fita adesiva", "price": 3.0, "stock_quantity": 10}
    ).json()
    client.post(
        "/api/sales/",
        json={
            "client_id": created_client["id"],
            "items": [{"product_id": product["id"], "quantity": 1}],
        },
    )

    response = client.post(f"/web/clients/{created_client['id']}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert "error=" in response.headers["location"]


def test_delete_sale_restores_stock():
    product = client.post(
        "/api/products/", json={"name": "Cola", "price": 5.0, "stock_quantity": 10}
    ).json()
    sale = client.post(
        "/api/sales/", json={"items": [{"product_id": product["id"], "quantity": 4}]}
    ).json()

    updated = client.get(f"/api/products/{product['id']}").json()
    assert updated["stock_quantity"] == 6  # baixou com a venda

    response = client.post(f"/web/sales/{sale['id']}/delete", follow_redirects=False)
    assert response.status_code == 303

    restored = client.get(f"/api/products/{product['id']}").json()
    assert restored["stock_quantity"] == 10  # devolvido após excluir a venda

    remaining_sales = client.get("/api/sales/").json()
    assert all(s["id"] != sale["id"] for s in remaining_sales)
