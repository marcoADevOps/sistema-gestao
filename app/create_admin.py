"""
Cria um usuário para acessar o sistema. Não existe cadastro público por
questão de segurança (principalmente relevante quando a aplicação estiver
exposta à internet) — usuários são criados manualmente por este comando.

Uso (dentro do container da aplicação):
    docker compose -f docker-compose.prod.yml exec app python -m app.create_admin <usuario> <senha>
"""

import sys

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app import models


def main():
    if len(sys.argv) != 3:
        print("Uso: python -m app.create_admin <usuario> <senha>")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            print(f"Usuário '{username}' já existe.")
            return

        user = models.User(username=username, hashed_password=hash_password(password))
        db.add(user)
        db.commit()
        print(f"Usuário '{username}' criado com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
