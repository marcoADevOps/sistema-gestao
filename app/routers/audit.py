from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud, models
from app.auth import require_admin_web
from app.database import get_db

router = APIRouter(prefix="/web/audit-log", tags=["audit"], dependencies=[Depends(require_admin_web)])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def view_audit_log(
    request: Request, db: Session = Depends(get_db), user: models.User = Depends(require_admin_web)
):
    entries = crud.list_audit_log(db, limit=200)
    return templates.TemplateResponse(
        "audit_log.html", {"request": request, "entries": entries, "user": user}
    )
