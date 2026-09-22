from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    name: str
    price: float
    stock_quantity: int = 0


class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class ClientBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientOut(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int


class SaleCreate(BaseModel):
    client_id: Optional[int] = None
    items: list[SaleItemCreate]


class SaleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    quantity: int
    unit_price: float


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: Optional[int]
    total: float
    created_at: datetime
    items: list[SaleItemOut]
