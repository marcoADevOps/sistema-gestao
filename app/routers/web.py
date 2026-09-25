from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import require_login_web, require_admin_web, get_csrf_token, verify_csrf
from app.database import get_db

router = APIRouter(prefix="/web", tags=["web"], dependencies=[Depends(require_login_web)])
templates = Jinja2Templates(directory="app/templates")


@router.post("/products", dependencies=[Depends(verify_csrf)])
def create_product_web(
    name: str = Form(...),
    price: float = Form(...),
    stock_quantity: int = Form(0),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin_web),
):
    crud.create_product(
        db, schemas.ProductCreate(name=name, price=price, stock_quantity=stock_quantity)
    )
    crud.log_action(
        db, admin_user.username, "create_product", f"Produto '{name}' cadastrado (estoque: {stock_quantity})"
    )
    return RedirectResponse(url="/", status_code=303)


@router.post("/clients", dependencies=[Depends(verify_csrf)])
def create_client_web(
    name: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_login_web),
):
    crud.create_client(
        db,
        schemas.ClientCreate(name=name, phone=phone or None, email=email or None),
    )
    crud.log_action(db, user.username, "create_client", f"Cliente '{name}' cadastrado")
    return RedirectResponse(url="/", status_code=303)


@router.post("/sales", dependencies=[Depends(verify_csrf)])
def create_sale_web(
    product_id: int = Form(...),
    quantity: int = Form(...),
    client_id: str = Form(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_login_web),
):
    client_id_int = int(client_id) if client_id else None
    try:
        sale = crud.create_sale(
            db,
            schemas.SaleCreate(
                client_id=client_id_int,
                items=[schemas.SaleItemCreate(product_id=product_id, quantity=quantity)],
            ),
        )
    except HTTPException as exc:
        return RedirectResponse(url=f"/?error={exc.detail}", status_code=303)

    crud.log_action(
        db, user.username, "create_sale", f"Venda #{sale.id} registrada (total: R$ {sale.total:.2f})"
    )
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
        "edit_product.html",
        {
            "request": request,
            "product": product,
            "user": user,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("/products/{product_id}/edit", dependencies=[Depends(verify_csrf)])
def edit_product_submit(
    product_id: int,
    name: str = Form(...),
    price: float = Form(...),
    stock_quantity: int = Form(...),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin_web),
):
    crud.update_product(
        db, product_id, schemas.ProductCreate(name=name, price=price, stock_quantity=stock_quantity)
    )
    crud.log_action(db, admin_user.username, "edit_product", f"Produto #{product_id} ('{name}') editado")
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
        "edit_client.html",
        {
            "request": request,
            "client": client,
            "user": user,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("/clients/{client_id}/edit", dependencies=[Depends(verify_csrf)])
def edit_client_submit(
    client_id: int,
    name: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_login_web),
):
    crud.update_client(
        db, client_id, schemas.ClientCreate(name=name, phone=phone or None, email=email or None)
    )
    crud.log_action(db, user.username, "edit_client", f"Cliente #{client_id} ('{name}') editado")
    return RedirectResponse(url="/", status_code=303)


@router.post("/products/{product_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_product_web(
    product_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin_web),
):
    product = crud.get_product(db, product_id)
    name = product.name
    try:
        crud.delete_product(db, product_id)
    except HTTPException as exc:
        return RedirectResponse(url=f"/?error={exc.detail}", status_code=303)
    crud.log_action(db, admin_user.username, "delete_product", f"Produto '{name}' (#{product_id}) excluído")
    return RedirectResponse(url="/", status_code=303)


@router.post("/clients/{client_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_client_web(
    client_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin_web),
):
    client = crud.get_client(db, client_id)
    name = client.name
    try:
        crud.delete_client(db, client_id)
    except HTTPException as exc:
        return RedirectResponse(url=f"/?error={exc.detail}", status_code=303)
    crud.log_action(db, admin_user.username, "delete_client", f"Cliente '{name}' (#{client_id}) excluído")
    return RedirectResponse(url="/", status_code=303)


@router.post("/sales/{sale_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_sale_web(
    sale_id: int,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin_web),
):
    crud.delete_sale(db, sale_id)
    crud.log_action(
        db, admin_user.username, "delete_sale", f"Venda #{sale_id} excluída (estoque devolvido)"
    )
    return RedirectResponse(url="/", status_code=303)
