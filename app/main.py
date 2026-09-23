import os

from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import crud, models
from app.auth import require_login_web
from app.database import Base, engine, get_db
from app.routers import products, clients, sales, web, auth

# Cria as tabelas automaticamente se não existirem (suficiente para o MVP;
# num projeto maior isso vira migração com Alembic).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Gestão - Estoque e Vendas")

# Chave usada para assinar o cookie de sessão. Em produção, defina
# SESSION_SECRET_KEY no .env com um valor longo e aleatório
# (ex: python -c "import secrets; print(secrets.token_hex(32))").
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "troque-esta-chave-em-producao")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(clients.router)
app.include_router(sales.router)
app.include_router(web.router)

templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
def health_check():
    """Usado pelo pipeline de CI/CD e por load balancers para checar se a app está no ar."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    error: str = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_login_web),
):
    products_list = crud.list_products(db)
    clients_list = crud.list_clients(db)
    sales_list = crud.list_sales(db)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products_list,
            "clients": clients_list,
            "sales": sales_list,
            "low_stock": [p for p in products_list if p.stock_quantity <= 5],
            "error": error,
            "user": user,
        },
    )
