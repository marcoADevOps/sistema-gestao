from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/web", tags=["web"])


@router.post("/products")
def create_product_web(
    name: str = Form(...),
    price: float = Form(...),
    stock_quantity: int = Form(0),
    db: Session = Depends(get_db),
):
    crud.create_product(
        db, schemas.ProductCreate(name=name, price=price, stock_quantity=stock_quantity)
    )
    return RedirectResponse(url="/", status_code=303)


@router.post("/clients")
def create_client_web(
    name: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    db: Session = Depends(get_db),
):
    crud.create_client(
        db,
        schemas.ClientCreate(name=name, phone=phone or None, email=email or None),
    )
    return RedirectResponse(url="/", status_code=303)


@router.post("/sales")
def create_sale_web(
    product_id: int = Form(...),
    quantity: int = Form(...),
    client_id: str = Form(None),
    db: Session = Depends(get_db),
):
    client_id_int = int(client_id) if client_id else None
    try:
        crud.create_sale(
            db,
            schemas.SaleCreate(
                client_id=client_id_int,
                items=[schemas.SaleItemCreate(product_id=product_id, quantity=quantity)],
            ),
        )
    except HTTPException as exc:
        # Redireciona de volta ao dashboard mostrando o motivo do erro
        # (ex: estoque insuficiente), em vez de deixar uma tela de erro crua.
        return RedirectResponse(url=f"/?error={exc.detail}", status_code=303)

    return RedirectResponse(url="/", status_code=303)
