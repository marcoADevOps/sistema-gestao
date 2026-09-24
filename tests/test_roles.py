import os

os.environ["DATABASE_URL"] = "sqlite:///./test_roles.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.auth import hash_password
from app import models


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(
        models.User(username="admin1", hashed_password=hash_password("adminpass123"), role="admin")
    )
    db.add(
        models.User(
            username="operador1", hashed_password=hash_password("operpass123"), role="operador"
        )
    )
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def login_as(client, username, password):
    return client.post("/login", data={"username": username, "password": password})


def test_operador_cannot_create_product_via_web():
    client = TestClient(app, follow_redirects=False)
    login_as(client, "operador1", "operpass123")

    response = client.post(
        "/web/products", data={"name": "Caneta", "price": "2.5", "stock_quantity": "10"}
    )
    assert response.status_code == 307
    assert response.headers["location"] == "/"

    # confirma que realmente não criou
    client_admin = TestClient(app)
    login_as(client_admin, "admin1", "adminpass123")
    products = client_admin.get("/api/products/").json()
    assert len(products) == 0


def test_operador_cannot_create_product_via_api():
    client = TestClient(app)
    login_as(client, "operador1", "operpass123")

    response = client.post(
        "/api/products/", json={"name": "Caneta", "price": 2.5, "stock_quantity": 10}
    )
    assert response.status_code == 403


def test_operador_can_create_sale_and_client():
    client = TestClient(app)
    login_as(client, "admin1", "adminpass123")
    product = client.post(
        "/api/products/", json={"name": "Caderno", "price": 15.0, "stock_quantity": 10}
    ).json()

    op_client = TestClient(app)
    login_as(op_client, "operador1", "operpass123")

    client_response = op_client.post(
        "/web/clients", data={"name": "Cliente Teste"}, follow_redirects=False
    )
    assert client_response.status_code == 303

    sale_response = op_client.post(
        "/web/sales",
        data={"product_id": str(product["id"]), "quantity": "1", "client_id": ""},
        follow_redirects=False,
    )
    assert sale_response.status_code == 303


def test_operador_cannot_delete_product():
    client = TestClient(app)
    login_as(client, "admin1", "adminpass123")
    product = client.post(
        "/api/products/", json={"name": "Grampeador", "price": 20.0, "stock_quantity": 5}
    ).json()

    op_client = TestClient(app, follow_redirects=False)
    login_as(op_client, "operador1", "operpass123")
    response = op_client.post(f"/web/products/{product['id']}/delete")
    assert response.status_code == 307

    # continua existindo
    remaining = client.get("/api/products/").json()
    assert any(p["id"] == product["id"] for p in remaining)


def test_operador_cannot_access_user_management():
    client = TestClient(app, follow_redirects=False)
    login_as(client, "operador1", "operpass123")
    response = client.get("/web/users")
    assert response.status_code == 307


def test_admin_can_access_user_management_and_create_user():
    client = TestClient(app)
    login_as(client, "admin1", "adminpass123")

    response = client.get("/web/users")
    assert response.status_code == 200
    assert "operador1" in response.text

    create_response = client.post(
        "/web/users",
        data={"username": "novooperador", "password": "senha123456", "role": "operador"},
        follow_redirects=False,
    )
    assert create_response.status_code == 303

    users_page = client.get("/web/users").text
    assert "novooperador" in users_page


def test_admin_cannot_delete_own_user():
    client = TestClient(app, follow_redirects=False)
    login_as(client, "admin1", "adminpass123")

    admin_user = SessionLocal().query(models.User).filter_by(username="admin1").first()
    response = client.post(f"/web/users/{admin_user.id}/delete")
    assert response.status_code == 303
    assert "error=" in response.headers["location"]


def test_cannot_delete_last_admin():
    client = TestClient(app, follow_redirects=False)
    login_as(client, "admin1", "adminpass123")

    db = SessionLocal()
    other_admin = models.User(
        username="admin2", hashed_password=hash_password("adminpass456"), role="admin"
    )
    db.add(other_admin)
    db.commit()
    db.refresh(other_admin)
    other_admin_id = other_admin.id
    db.close()

    # com dois admins, deletar um funciona
    response = client.post(f"/web/users/{other_admin_id}/delete")
    assert response.status_code == 303
    assert "error=" not in response.headers["location"]

    # tenta deletar o operador — não afeta a regra de "último admin"
    op = SessionLocal().query(models.User).filter_by(username="operador1").first()
    response2 = client.post(f"/web/users/{op.id}/delete")
    assert response2.status_code == 303
    assert "error=" not in response2.headers["location"]
