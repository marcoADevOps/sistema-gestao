import os
import re
from urllib.parse import unquote

os.environ["DATABASE_URL"] = "sqlite:///./test_security.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.auth import hash_password, MAX_LOGIN_ATTEMPTS, _login_attempts
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
    _login_attempts.clear()  # garante isolamento entre testes (estado é em memória do processo)
    yield
    Base.metadata.drop_all(bind=engine)
    _login_attempts.clear()


def test_login_locks_out_after_max_attempts():
    client = TestClient(app, follow_redirects=False)

    for _ in range(MAX_LOGIN_ATTEMPTS):
        response = client.post(
            "/login", data={"username": "admin1", "password": "senha-errada"}
        )
        assert response.status_code == 303
        assert "Usuário ou senha inválidos" in unquote(response.headers["location"])

    # a próxima tentativa, mesmo com a senha CERTA, deve ser bloqueada pelo rate limit
    locked_response = client.post(
        "/login", data={"username": "admin1", "password": "adminpass123"}
    )
    assert locked_response.status_code == 303
    assert "Muitas tentativas" in unquote(locked_response.headers["location"])

    # confirma que realmente não logou
    dashboard = client.get("/")
    assert dashboard.status_code in (307, 200)
    if dashboard.status_code == 200:
        pytest.fail("Login não deveria ter funcionado com o rate limit ativo")


def test_login_rate_limit_is_per_username():
    """Muitas tentativas erradas para um usuário não devem bloquear outro."""
    db = SessionLocal()
    db.add(
        models.User(
            username="outrouser", hashed_password=hash_password("outrasenha123"), role="operador"
        )
    )
    db.commit()
    db.close()

    client = TestClient(app, follow_redirects=False)
    for _ in range(MAX_LOGIN_ATTEMPTS):
        client.post("/login", data={"username": "admin1", "password": "senha-errada"})

    # "outrouser" não foi afetado
    response = client.post(
        "/login", data={"username": "outrouser", "password": "outrasenha123"}
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_successful_login_is_logged():
    client = TestClient(app)
    client.post("/login", data={"username": "admin1", "password": "adminpass123"})

    db = SessionLocal()
    entries = db.query(models.AuditLog).filter_by(action="login").all()
    db.close()
    assert len(entries) == 1
    assert entries[0].username == "admin1"


def test_failed_login_is_logged():
    client = TestClient(app)
    client.post("/login", data={"username": "admin1", "password": "senha-errada"})

    db = SessionLocal()
    entries = db.query(models.AuditLog).filter_by(action="login_failed").all()
    db.close()
    assert len(entries) == 1


def test_audit_log_records_product_actions():
    import re

    client = TestClient(app)
    client.post("/login", data={"username": "admin1", "password": "adminpass123"})

    page = client.get("/")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)

    client.post(
        "/web/products",
        data={"name": "Produto Auditado", "price": "9.9", "stock_quantity": "5", "csrf_token": token},
    )

    db = SessionLocal()
    entries = db.query(models.AuditLog).filter_by(action="create_product").all()
    db.close()
    assert len(entries) == 1
    assert "Produto Auditado" in entries[0].description
    assert entries[0].username == "admin1"


def test_operador_cannot_view_audit_log():
    db = SessionLocal()
    db.add(
        models.User(
            username="op1", hashed_password=hash_password("senhaop123"), role="operador"
        )
    )
    db.commit()
    db.close()

    client = TestClient(app, follow_redirects=False)
    client.post("/login", data={"username": "op1", "password": "senhaop123"})
    response = client.get("/web/audit-log")
    assert response.status_code == 307


def test_admin_can_view_audit_log():
    client = TestClient(app)
    client.post("/login", data={"username": "admin1", "password": "adminpass123"})
    response = client.get("/web/audit-log")
    assert response.status_code == 200
    assert "login" in response.text
