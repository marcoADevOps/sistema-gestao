import os

os.environ["DATABASE_URL"] = "sqlite:///./test_charts.db"

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.auth import hash_password
from app import crud, models, schemas


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


def test_sales_by_day_fills_gaps_with_zero():
    db = SessionLocal()
    product = models.Product(name="Item", price=10.0, stock_quantity=100)
    db.add(product)
    db.commit()
    db.refresh(product)

    # uma venda só, há 5 dias
    sale = models.Sale(total=50.0, created_at=datetime.utcnow() - timedelta(days=5))
    db.add(sale)
    db.commit()

    result = crud.sales_by_day(db, days=10)
    db.close()

    assert len(result) == 10
    totals = {r["date"]: r["total"] for r in result}
    non_zero_days = [v for v in totals.values() if v > 0]
    assert non_zero_days == [50.0]


def test_top_products_orders_by_quantity_sold():
    db = SessionLocal()
    p1 = models.Product(name="Mais vendido", price=10.0, stock_quantity=100)
    p2 = models.Product(name="Menos vendido", price=10.0, stock_quantity=100)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    crud.create_sale(db, schemas.SaleCreate(items=[schemas.SaleItemCreate(product_id=p1.id, quantity=8)]))
    crud.create_sale(db, schemas.SaleCreate(items=[schemas.SaleItemCreate(product_id=p2.id, quantity=2)]))

    result = crud.top_products(db, limit=10)
    db.close()

    assert result[0]["name"] == "Mais vendido"
    assert result[0]["quantity"] == 8
    assert result[1]["name"] == "Menos vendido"


def test_dashboard_hides_charts_when_no_sales(client):
    response = client.get("/")
    assert "chartSalesByDay" not in response.text


def test_dashboard_shows_charts_when_sales_exist(client):
    product = client.post(
        "/api/products/", json={"name": "Produto X", "price": 10.0, "stock_quantity": 50}
    ).json()
    client.post("/api/sales/", json={"items": [{"product_id": product["id"], "quantity": 2}]})

    response = client.get("/")
    assert "chartSalesByDay" in response.text
    assert "chartTopProducts" in response.text
    assert "Produto X" in response.text


def test_product_name_with_script_tag_does_not_break_out(client):
    """Nome de produto malicioso não deve conseguir fechar a tag <script>
    onde os dados do gráfico são embutidos."""
    malicious_name = "Item</script><script>alert(1)</script>"
    product = client.post(
        "/api/products/", json={"name": malicious_name, "price": 5.0, "stock_quantity": 10}
    ).json()
    client.post("/api/sales/", json={"items": [{"product_id": product["id"], "quantity": 1}]})

    response = client.get("/")
    # o payload não pode conter a sequência literal "</script>" dentro do JSON embutido
    assert "</script><script>alert(1)" not in response.text
    # mas o nome real do produto continua presente (escapado), sem quebrar a página
    assert "alert(1)" in response.text
