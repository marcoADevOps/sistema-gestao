import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.auth import hash_password
from app import models


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


@pytest.fixture(autouse=True)
def login_test_user(setup_and_teardown_db):
    """Cria um usuário de teste e autentica o client antes de cada teste,
    já que todas as rotas de API/web exigem sessão válida."""
    db = SessionLocal()
    db.add(
        models.User(
            username="testuser", hashed_password=hash_password("testpass123"), role="admin"
        )
    )
    db.commit()
    db.close()

    client.post("/login", data={"username": "testuser", "password": "testpass123"})
    yield


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_list_product():
    response = client.post(
        "/api/products/",
        json={"name": "Caneta", "price": 2.5, "stock_quantity": 100},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Caneta"
    assert data["stock_quantity"] == 100

    response = client.get("/api/products/")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_create_client():
    response = client.post(
        "/api/clients/",
        json={"name": "João Silva", "phone": "61999999999"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "João Silva"


def test_sale_reduces_stock():
    product = client.post(
        "/api/products/", json={"name": "Caderno", "price": 15.0, "stock_quantity": 10}
    ).json()

    sale_response = client.post(
        "/api/sales/",
        json={"items": [{"product_id": product["id"], "quantity": 3}]},
    )
    assert sale_response.status_code == 200
    sale_data = sale_response.json()
    assert sale_data["total"] == 45.0

    updated_product = client.get(f"/api/products/{product['id']}").json()
    assert updated_product["stock_quantity"] == 7


def test_sale_fails_with_insufficient_stock():
    product = client.post(
        "/api/products/", json={"name": "Mochila", "price": 120.0, "stock_quantity": 1}
    ).json()

    sale_response = client.post(
        "/api/sales/",
        json={"items": [{"product_id": product["id"], "quantity": 5}]},
    )
    assert sale_response.status_code == 400
    assert "Estoque insuficiente" in sale_response.json()["detail"]
