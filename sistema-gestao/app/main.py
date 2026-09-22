from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud
from app.database import Base, engine, get_db
from app.routers import products, clients, sales

# Cria as tabelas automaticamente se não existirem (suficiente para o MVP;
# num projeto maior isso vira migração com Alembic).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Gestão - Estoque e Vendas")

app.include_router(products.router)
app.include_router(clients.router)
app.include_router(sales.router)

templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
def health_check():
    """Usado pelo pipeline de CI/CD e por load balancers para checar se a app está no ar."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
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
        },
    )
