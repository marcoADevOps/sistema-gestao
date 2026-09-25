from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud, models
from app.auth import hash_password, require_admin_web, get_csrf_token, verify_csrf
from app.database import get_db

router = APIRouter(prefix="/web/users", tags=["users"], dependencies=[Depends(require_admin_web)])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_users(
    request: Request,
    error: str = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin_web),
):
    users = db.query(models.User).order_by(models.User.username).all()
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "users": users,
            "user": user,
            "error": error,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("", dependencies=[Depends(verify_csrf)])
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin_web),
):
    if role not in ("admin", "operador"):
        return RedirectResponse(url="/web/users?error=Papel inválido", status_code=303)

    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        return RedirectResponse(
            url=f"/web/users?error=Usuário '{username}' já existe", status_code=303
        )

    new_user = models.User(username=username, hashed_password=hash_password(password), role=role)
    db.add(new_user)
    db.commit()
    crud.log_action(
        db, admin_user.username, "create_user", f"Usuário '{username}' criado (papel: {role})"
    )
    return RedirectResponse(url="/web/users", status_code=303)


@router.post("/{user_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin_web),
):
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if target.id == current_user.id:
        return RedirectResponse(
            url="/web/users?error=Você não pode excluir seu próprio usuário", status_code=303
        )

    remaining_admins = (
        db.query(models.User).filter(models.User.role == "admin", models.User.id != user_id).count()
    )
    if target.role == "admin" and remaining_admins == 0:
        return RedirectResponse(
            url="/web/users?error=Não é possível excluir o último administrador", status_code=303
        )

    target_username = target.username
    db.delete(target)
    db.commit()
    crud.log_action(
        db, current_user.username, "delete_user", f"Usuário '{target_username}' excluído"
    )
    return RedirectResponse(url="/web/users", status_code=303)
