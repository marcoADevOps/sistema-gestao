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
