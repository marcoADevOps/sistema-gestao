import bcrypt
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Retorna o usuário logado (via sessão) ou None, sem lançar erro."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()


def require_login_web(request: Request, db: Session = Depends(get_db)) -> models.User:
    """Para rotas que servem HTML: sem sessão válida, redireciona para /login."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user


def require_login_api(request: Request, db: Session = Depends(get_db)) -> models.User:
    """Para rotas de API (JSON): sem sessão válida, retorna 401."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user
