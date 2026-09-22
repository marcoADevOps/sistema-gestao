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


def list_products(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Product).offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int) -> models.Product:
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


# ---------- Clientes ----------

def create_client(db: Session, client: schemas.ClientCreate) -> models.Client:
    db_client = models.Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


def list_clients(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Client).offset(skip).limit(limit).all()


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
    return db.query(models.Sale).offset(skip).limit(limit).all()
