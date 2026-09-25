from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud, models
from app.auth import (
    verify_password,
    is_login_rate_limited,
    record_failed_login,
    reset_login_attempts,
)
from app.database import get_db

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    limited, minutes_left = is_login_rate_limited(username)
    if limited:
        return RedirectResponse(
            url=f"/login?error=Muitas tentativas com este usuário. Tente novamente em {minutes_left} min.",
            status_code=303,
        )

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        record_failed_login(username)
        crud.log_action(db, username, "login_failed", "Tentativa de login com senha incorreta")
        return RedirectResponse(url="/login?error=Usuário ou senha inválidos", status_code=303)

    reset_login_attempts(username)
    crud.log_action(db, user.username, "login", "Login realizado")
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            crud.log_action(db, user.username, "logout", "Logout realizado")
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
