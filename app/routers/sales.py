from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import require_login_api
from app.database import get_db

router = APIRouter(prefix="/api/sales", tags=["sales"], dependencies=[Depends(require_login_api)])


@router.post("/", response_model=schemas.SaleOut)
def create_sale(sale: schemas.SaleCreate, db: Session = Depends(get_db)):
    return crud.create_sale(db, sale)


@router.get("/", response_model=list[schemas.SaleOut])
def list_sales(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.list_sales(db, skip, limit)
