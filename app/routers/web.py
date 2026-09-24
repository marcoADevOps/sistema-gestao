from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import require_login_web, require_admin_web
from app.database import get_db

router = APIRouter(prefix="/web", tags=["web"], dependencies=[Depends(require_login_web)])
templates = Jinja2Templates(directory="app/templates")


@router.post("/products")
def create_product_web(
    name: str = Form(...),
    price: float = Form(...),
    stock_quantity: int = Form(0),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin_web),
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
        return RedirectResponse(url=f"/?error={exc.detail}", status_code=303)

    return RedirectResponse(url="/", status_code=303)


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
def edit_product_form(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin_web),
):
    product = crud.get_product(db, product_id)
    return templates.TemplateResponse(
        "edit_product.html", {"request": request, "product": product, "user": user}
    )


@router.post("/products/{product_id}/edit")
def edit_product_submit(
    product_id: int,
    name: str = Form(...),
    price: float = Form(...),
    stock_quantity: int = Form(...),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin_web),
):
    crud.update_product(
        db, product_id, schemas.ProductCreate(name=name, price=price, stock_quantity=stock_quantity)
    )
    return RedirectResponse(url="/", status_code=303)


@router.get("/clients/{client_id}/edit", response_class=HTMLResponse)
def edit_client_form(
    client_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_login_web),
):
    client = crud.get_client(db, client_id)
    return templates.TemplateResponse(
        "edit_client.html", {"request": request, "client": client, "user": user}
    )


@router.post("/clients/{client_id}/edit")
def edit_client_submit(
    client_id: int,
    name: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    db: Session = Depends(get_db),
):
    crud.update_client(
        db, client_id, schemas.ClientCreate(name=name, phone=phone or None, email=email or None)
    )
    return RedirectResponse(url="/", status_code=303)


@router.post("/products/{product_id}/delete")
def delete_product_web(
    product_id: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin_web)
):
    try:
        crud.delete_product(db, product_id)
    except HTTPException as exc:
        return RedirectResponse(url=f"/?error={exc.detail}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.post("/clients/{client_id}/delete")
def delete_client_web(
    client_id: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin_web)
):
    try:
        crud.delete_client(db, client_id)
    except HTTPException as exc:
        return RedirectResponse(url=f"/?error={exc.detail}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.post("/sales/{sale_id}/delete")
def delete_sale_web(
    sale_id: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin_web)
):
    crud.delete_sale(db, sale_id)
    return RedirectResponse(url="/", status_code=303)
