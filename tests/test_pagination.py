import os

os.environ["DATABASE_URL"] = "sqlite:///./test_pagination.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app, PAGE_SIZE
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
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/login", data={"username": "admin1", "password": "adminpass123"})
    return c


def test_dashboard_paginates_products(client):
    for i in range(PAGE_SIZE + 5):
        client.post(
            "/api/products/", json={"name": f"Produto {i:03d}", "price": 10.0, "stock_quantity": 50}
        )

    page1 = client.get("/")
    assert page1.status_code == 200
    assert "Página 1 de 2" in page1.text

    page2 = client.get("/?page_products=2")
    assert page2.status_code == 200
    assert "Página 2 de 2" in page2.text


def test_dashboard_searches_products_by_name(client):
    client.post("/api/products/", json={"name": "Caneta Azul", "price": 2.0, "stock_quantity": 10})
    client.post("/api/products/", json={"name": "Lápis Preto", "price": 1.5, "stock_quantity": 10})

    response = client.get("/?q_products=Caneta")
    assert response.status_code == 200
    # "Caneta Azul" aparece 3x: dropdown de venda, célula da tabela, e texto de confirmação do botão excluir
    assert response.text.count("Caneta Azul") == 3
    # "Lápis Preto" só aparece 1x: no dropdown — sumiu da tabela por causa do filtro
    assert response.text.count("Lápis Preto") == 1


def test_search_does_not_affect_kpi_counts(client):
    """Os contadores do topo devem refletir o total real, não só a página filtrada."""
    for i in range(5):
        client.post(
            "/api/products/", json={"name": f"Produto {i}", "price": 10.0, "stock_quantity": 10}
        )

    response = client.get("/?q_products=inexistente")
    assert response.status_code == 200
    # nenhum produto bate com a busca, mas o card de topo continua mostrando 5
    assert "<div class=\"value\">5</div>" in response.text


def test_all_products_available_in_sale_dropdown_regardless_of_search(client):
    """O dropdown de 'Registrar venda' precisa ver todos os produtos, mesmo
    com um filtro de busca ativo na tabela."""
    client.post("/api/products/", json={"name": "Produto Raro", "price": 5.0, "stock_quantity": 10})
    client.post("/api/products/", json={"name": "Outro Item", "price": 3.0, "stock_quantity": 10})

    response = client.get("/?q_products=Raro")
    assert "Produto Raro" in response.text
    # "Outro Item" some da tabela filtrada, mas continua no <select> do formulário de venda
    assert 'value="2">Outro Item' in response.text or "Outro Item —" in response.text


def test_dashboard_paginates_clients(client):
    for i in range(PAGE_SIZE + 3):
        client.post("/api/clients/", json={"name": f"Cliente {i:03d}"})

    page1 = client.get("/")
    assert "Página 1 de 2" in page1.text
