from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import require_login_api
from app.database import get_db

router = APIRouter(prefix="/api/clients", tags=["clients"], dependencies=[Depends(require_login_api)])


@router.post("/", response_model=schemas.ClientOut)
def create_client(client: schemas.ClientCreate, db: Session = Depends(get_db)):
    return crud.create_client(db, client)


@router.get("/", response_model=list[schemas.ClientOut])
def list_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.list_clients(db, skip, limit)
