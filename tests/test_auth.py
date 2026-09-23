import os

os.environ["DATABASE_URL"] = "sqlite:///./test_auth.db"

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
    db.add(models.User(username="marco", hashed_password=hash_password("senha-forte-123")))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def test_dashboard_redirects_to_login_when_not_authenticated():
    client = TestClient(app, follow_redirects=False)
    response = client.get("/")
    assert response.status_code == 307
    assert response.headers["location"] == "/login"


def test_api_returns_401_when_not_authenticated():
    client = TestClient(app)
    response = client.get("/api/products/")
    assert response.status_code == 401


def test_health_check_does_not_require_login():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_login_with_wrong_password_fails():
    client = TestClient(app, follow_redirects=False)
    response = client.post("/login", data={"username": "marco", "password": "senha-errada"})
    assert response.status_code == 303
    assert "error=" in response.headers["location"]

    # não deve ter autenticado — dashboard continua bloqueado
    dashboard = client.get("/", follow_redirects=False)
    assert dashboard.status_code == 307


def test_login_with_correct_credentials_grants_access():
    client = TestClient(app)
    response = client.post(
        "/login", data={"username": "marco", "password": "senha-forte-123"}
    )
    assert response.status_code == 200  # já seguiu o redirect até "/"
    assert "Sistema de Gestão" in response.text


def test_logout_revokes_access():
    client = TestClient(app)
    client.post("/login", data={"username": "marco", "password": "senha-forte-123"})

    # confirma que estava logado
    assert client.get("/", follow_redirects=False).status_code == 200

    client.post("/logout")

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/login"
