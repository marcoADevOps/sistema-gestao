import secrets
from collections import defaultdict
from datetime import datetime, timedelta

import bcrypt
from fastapi import Request, HTTPException, Depends, Form
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


def require_admin_web(user: models.User = Depends(require_login_web)) -> models.User:
    """Para rotas HTML restritas a administradores: operador é redirecionado pro dashboard."""
    if user.role != "admin":
        raise HTTPException(status_code=307, headers={"Location": "/"})
    return user


def require_admin_api(user: models.User = Depends(require_login_api)) -> models.User:
    """Para rotas de API restritas a administradores: operador recebe 403."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user


# ---------------------------------------------------------------------------
# Rate limiting de login (proteção contra força bruta)
#
# Guardado em memória do processo — reseta se o container reiniciar, e não é
# compartilhado entre múltiplas réplicas. É uma limitação aceitável para uma
# aplicação rodando numa única instância (nosso caso); num cenário com vários
# workers/réplicas, isso precisaria virar uma tabela no banco ou um Redis.
# ---------------------------------------------------------------------------
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

_login_attempts: dict[str, list[datetime]] = defaultdict(list)


def is_login_rate_limited(username: str) -> tuple[bool, int]:
    """Retorna (esta_bloqueado, minutos_restantes)."""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=LOGIN_LOCKOUT_MINUTES)

    attempts = [t for t in _login_attempts[username] if t > window_start]
    _login_attempts[username] = attempts

    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        oldest = min(attempts)
        elapsed_minutes = (now - oldest).total_seconds() / 60
        remaining = max(int(LOGIN_LOCKOUT_MINUTES - elapsed_minutes) + 1, 1)
        return True, remaining

    return False, 0


def record_failed_login(username: str) -> None:
    _login_attempts[username].append(datetime.utcnow())


def reset_login_attempts(username: str) -> None:
    _login_attempts.pop(username, None)


# ---------------------------------------------------------------------------
# Proteção CSRF
#
# Cada sessão recebe um token aleatório. Todo formulário que altera dados
# (POST) precisa devolver esse mesmo token — impede que outro site consiga
# forjar uma requisição usando o cookie de sessão do usuário sem ele saber.
# ---------------------------------------------------------------------------
def get_csrf_token(request: Request) -> str:
    """Garante que a sessão tem um token CSRF, criando um se ainda não existir."""
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def verify_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    session_token = request.session.get("csrf_token")
    if not session_token or session_token != csrf_token:
        raise HTTPException(
            status_code=403,
            detail="Token de segurança inválido ou expirado. Recarregue a página e tente novamente.",
        )
