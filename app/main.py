import json
import math
import os

from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import crud, models
from app.auth import require_login_web, get_csrf_token
from app.database import Base, engine, get_db
from app.routers import products, clients, sales, web, auth, users, audit

# Cria as tabelas automaticamente se não existirem (suficiente para o MVP;
# num projeto maior isso vira migração com Alembic).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Gestão - Estoque e Vendas")

# Chave usada para assinar o cookie de sessão. Em produção, defina
# SESSION_SECRET_KEY no .env com um valor longo e aleatório
# (ex: python -c "import secrets; print(secrets.token_hex(32))").
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "troque-esta-chave-em-producao")

# Defina SESSION_COOKIE_SECURE=true no .env quando a aplicação estiver
# exposta via HTTPS (ex: atrás do Cloudflare Tunnel). Deixe em false
# (padrão) para acesso local só por HTTP, como http://192.168.1.8:8000 —
# com https_only=True nesse caso, o login pararia de funcionar.
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.add_middleware(
    SessionMiddleware, secret_key=SESSION_SECRET_KEY, https_only=SESSION_COOKIE_SECURE
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(clients.router)
app.include_router(sales.router)
app.include_router(web.router)
app.include_router(users.router)
app.include_router(audit.router)

templates = Jinja2Templates(directory="app/templates")

PAGE_SIZE = 20


@app.get("/health")
def health_check():
    """Usado pelo pipeline de CI/CD e por load balancers para checar se a app está no ar."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    error: str = None,
    q_products: str = "",
    page_products: int = 1,
    q_clients: str = "",
    page_clients: int = 1,
    page_sales: int = 1,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_login_web),
):
    # Conjuntos completos: usados nos contadores do topo, no alerta de
    # estoque baixo e no dropdown de "Registrar venda" — não paginados,
    # porque essas funções precisam enxergar tudo, não só a página atual.
    all_products = crud.list_all_products(db)
    all_clients = crud.list_all_clients(db)

    page_products = max(page_products, 1)
    page_clients = max(page_clients, 1)
    page_sales = max(page_sales, 1)

    total_products = crud.count_products(db, search=q_products or None)
    products_page = crud.list_products(
        db, skip=(page_products - 1) * PAGE_SIZE, limit=PAGE_SIZE, search=q_products or None
    )

    total_clients = crud.count_clients(db, search=q_clients or None)
    clients_page = crud.list_clients(
        db, skip=(page_clients - 1) * PAGE_SIZE, limit=PAGE_SIZE, search=q_clients or None
    )

    total_sales = crud.count_sales(db)
    sales_page = crud.list_sales(db, skip=(page_sales - 1) * PAGE_SIZE, limit=PAGE_SIZE)

    sales_by_day = crud.sales_by_day(db, days=30)
    top_products = crud.top_products(db, limit=10)

    def to_safe_json(data) -> str:
        # Evita que um nome de produto malicioso (ex: contendo "</script>")
        # escape da tag <script> onde os dados são embutidos no HTML.
        return json.dumps(data).replace("</", "<\\/")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products_page,
            "clients": clients_page,
            "sales": sales_page,
            "products_count": len(all_products),
            "clients_count": len(all_clients),
            "sales_count": total_sales,
            "sales_total": crud.sum_sales_total(db),
            "low_stock": [p for p in all_products if p.stock_quantity <= 5],
            "all_products": all_products,
            "all_clients": all_clients,
            "sales_by_day_json": to_safe_json(sales_by_day),
            "top_products_json": to_safe_json(top_products),
            "has_sales_data": total_sales > 0,
            "error": error,
            "user": user,
            "csrf_token": get_csrf_token(request),
            # busca e paginação
            "q_products": q_products,
            "page_products": page_products,
            "pages_products": max(math.ceil(total_products / PAGE_SIZE), 1),
            "q_clients": q_clients,
            "page_clients": page_clients,
            "pages_clients": max(math.ceil(total_clients / PAGE_SIZE), 1),
            "page_sales": page_sales,
            "pages_sales": max(math.ceil(total_sales / PAGE_SIZE), 1),
        },
    )
