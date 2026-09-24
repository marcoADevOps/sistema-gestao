from sqlalchemy.orm import Session
from fastapi import HTTPException

from app import models, schemas


# ---------- Produtos ----------

def create_product(db: Session, product: schemas.ProductCreate) -> models.Product:
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def list_products(db: Session, skip: int = 0, limit: int = 100, search: str | None = None):
    query = db.query(models.Product)
    if search:
        query = query.filter(models.Product.name.ilike(f"%{search}%"))
    return query.order_by(models.Product.name).offset(skip).limit(limit).all()


def list_all_products(db: Session):
    """Sem paginação — usado onde é preciso o conjunto completo (dropdown de
    venda, cálculo de estoque baixo, contadores do dashboard)."""
    return db.query(models.Product).order_by(models.Product.name).all()


def count_products(db: Session, search: str | None = None) -> int:
    query = db.query(models.Product)
    if search:
        query = query.filter(models.Product.name.ilike(f"%{search}%"))
    return query.count()


def get_product(db: Session, product_id: int) -> models.Product:
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


def update_product(db: Session, product_id: int, product: schemas.ProductCreate) -> models.Product:
    db_product = get_product(db, product_id)
    db_product.name = product.name
    db_product.price = product.price
    db_product.stock_quantity = product.stock_quantity
    db.commit()
    db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int) -> None:
    db_product = get_product(db, product_id)
    if db_product.sale_items:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir '{db_product.name}': já existem vendas registradas com esse produto.",
        )
    db.delete(db_product)
    db.commit()


# ---------- Clientes ----------

def create_client(db: Session, client: schemas.ClientCreate) -> models.Client:
    db_client = models.Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


def list_clients(db: Session, skip: int = 0, limit: int = 100, search: str | None = None):
    query = db.query(models.Client)
    if search:
        query = query.filter(models.Client.name.ilike(f"%{search}%"))
    return query.order_by(models.Client.name).offset(skip).limit(limit).all()


def list_all_clients(db: Session):
    """Sem paginação — usado no dropdown de venda e nos contadores do dashboard."""
    return db.query(models.Client).order_by(models.Client.name).all()


def count_clients(db: Session, search: str | None = None) -> int:
    query = db.query(models.Client)
    if search:
        query = query.filter(models.Client.name.ilike(f"%{search}%"))
    return query.count()


def get_client(db: Session, client_id: int) -> models.Client:
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


def update_client(db: Session, client_id: int, client: schemas.ClientCreate) -> models.Client:
    db_client = get_client(db, client_id)
    db_client.name = client.name
    db_client.phone = client.phone
    db_client.email = client.email
    db.commit()
    db.refresh(db_client)
    return db_client


def delete_client(db: Session, client_id: int) -> None:
    db_client = get_client(db, client_id)
    if db_client.sales:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir '{db_client.name}': já existem vendas registradas para esse cliente.",
        )
    db.delete(db_client)
    db.commit()


# ---------- Vendas ----------

def create_sale(db: Session, sale: schemas.SaleCreate) -> models.Sale:
    if not sale.items:
        raise HTTPException(status_code=400, detail="A venda precisa ter ao menos um item")

    db_sale = models.Sale(client_id=sale.client_id, total=0.0)
    db.add(db_sale)
    db.flush()  # garante db_sale.id antes de criar os itens

    total = 0.0
    for item in sale.items:
        product = get_product(db, item.product_id)
        if product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Estoque insuficiente para '{product.name}' "
                       f"(disponível: {product.stock_quantity}, pedido: {item.quantity})",
            )

        product.stock_quantity -= item.quantity
        subtotal = product.price * item.quantity
        total += subtotal

        db_item = models.SaleItem(
            sale_id=db_sale.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_price=product.price,
        )
        db.add(db_item)

    db_sale.total = total
    db.commit()
    db.refresh(db_sale)
    return db_sale


def list_sales(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Sale)
        .order_by(models.Sale.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_sales(db: Session) -> int:
    return db.query(models.Sale).count()


def sum_sales_total(db: Session) -> float:
    from sqlalchemy import func

    result = db.query(func.sum(models.Sale.total)).scalar()
    return result or 0.0


def sales_by_day(db: Session, days: int = 30):
    """Retorna uma lista de (data, total) para os últimos `days` dias,
    incluindo dias sem venda nenhuma (total = 0), na ordem cronológica —
    pronto pra virar um gráfico de linha/barra sem buracos."""
    from datetime import datetime, timedelta
    from sqlalchemy import func

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days - 1)

    rows = (
        db.query(
            func.date(models.Sale.created_at).label("day"),
            func.sum(models.Sale.total).label("total"),
        )
        .filter(models.Sale.created_at >= start_date)
        .group_by(func.date(models.Sale.created_at))
        .all()
    )
    totals_by_day = {str(row.day): float(row.total) for row in rows}

    result = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        key = day.isoformat()
        result.append({"date": key, "total": round(totals_by_day.get(key, 0.0), 2)})
    return result


def top_products(db: Session, limit: int = 10):
    """Os produtos mais vendidos por quantidade total, com a receita gerada."""
    from sqlalchemy import func

    rows = (
        db.query(
            models.Product.name,
            func.sum(models.SaleItem.quantity).label("qty"),
            func.sum(models.SaleItem.quantity * models.SaleItem.unit_price).label("revenue"),
        )
        .join(models.SaleItem, models.SaleItem.product_id == models.Product.id)
        .group_by(models.Product.id, models.Product.name)
        .order_by(func.sum(models.SaleItem.quantity).desc())
        .limit(limit)
        .all()
    )
    return [
        {"name": r.name, "quantity": int(r.qty), "revenue": round(float(r.revenue), 2)}
        for r in rows
    ]


def get_sale(db: Session, sale_id: int) -> models.Sale:
    sale = db.query(models.Sale).filter(models.Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    return sale


def delete_sale(db: Session, sale_id: int) -> None:
    """Exclui a venda e devolve as quantidades ao estoque dos produtos envolvidos."""
    sale = get_sale(db, sale_id)
    for item in sale.items:
        item.product.stock_quantity += item.quantity
    db.delete(sale)  # cascade="all, delete-orphan" no relacionamento já apaga os itens
    db.commit()
