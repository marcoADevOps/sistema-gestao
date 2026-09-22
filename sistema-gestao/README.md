# Sistema de Gestão — Estoque e Vendas (v1 — MVP)

Sistema simples de gestão para pequenos negócios: cadastro de produtos, cadastro
de clientes e registro de vendas com baixa automática de estoque. Construído
como projeto de portfólio, pensado desde o início para rodar tanto em
infraestrutura própria (Proxmox) quanto migrar depois para uma cloud (AWS).

## Stack

- **Backend:** Python + FastAPI
- **Banco de dados:** PostgreSQL (SQLite automático se rodar sem Docker, só pra dev rápido)
- **Frontend:** Jinja2 + HTMX (sem build step, dashboard simples em `/`)
- **Empacotamento:** Docker + docker-compose
- **CI/CD:** GitHub Actions (testa → builda imagem → publica no GHCR → deploy via SSH)

## Rodando localmente (sem Docker, mais rápido pra desenvolver)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Acesse `http://localhost:8000` (dashboard) e `http://localhost:8000/docs`
(documentação interativa da API, gerada automaticamente pelo FastAPI).

Sem configurar nada, usa SQLite local (`local_dev.db`) — zero setup.

## Rodando com Docker (local, buildando a imagem)

```bash
cp .env.example .env   # ajuste a senha do Postgres
docker compose up --build
```

Isso usa o `docker-compose.yml` padrão, que builda a imagem na hora a partir do
código local — bom para desenvolvimento.

## Produção (VM/Proxmox) — usa a imagem já publicada

Na VM, o deploy usa `docker-compose.prod.yml`, que **baixa** a imagem pronta
do GHCR em vez de buildar (é isso que o pipeline de CI/CD faz automaticamente
a cada push na `main`). Antes do primeiro deploy manual, edite
`docker-compose.prod.yml` e troque `ghcr.io/SEU_USUARIO/SEU_REPO` pelo nome
real do seu repositório (tudo em minúsculas), ou exporte a variável:

```bash
export IMAGE_NAME=ghcr.io/seu-usuario/seu-repo
docker compose -f docker-compose.prod.yml up -d
```

## Rodando os testes

```bash
pytest -v
```

## Deploy no Proxmox (VM própria)

1. Crie uma VM/container no Proxmox com Docker e docker-compose instalados.
2. Clone o repositório em `/opt/sistema-gestao` nessa VM.
3. Configure os seguintes **secrets** no repositório do GitHub
   (`Settings > Secrets and variables > Actions`):
   - `PROXMOX_HOST` — IP ou hostname da VM
   - `PROXMOX_USER` — usuário SSH
   - `PROXMOX_SSH_KEY` — chave privada SSH com acesso à VM
4. A cada push na branch `main`, o workflow `.github/workflows/ci-cd.yml`
   automaticamente: roda os testes → builda a imagem Docker → publica no
   GitHub Container Registry → conecta na VM via SSH e atualiza o container.

## Migrando para a cloud (AWS) depois

Como a aplicação já é 100% containerizada, a mesma imagem publicada no GHCR
roda sem alterações em qualquer serviço de containers da AWS (ECS Fargate,
App Runner, Lightsail). O workflow já tem um job de exemplo comentado
(`deploy-aws`) mostrando como plugar isso — é só trocar o alvo do deploy,
sem tocar no código da aplicação.

## Roadmap

- [x] **v1** — Cadastro de produtos, clientes, registro de vendas com baixa
      automática de estoque, dashboard básico
- [ ] **v2** — Dashboard com gráficos, autenticação de usuários com perfis,
      exportação de relatórios (Excel/PDF), alerta de estoque baixo
- [ ] **v3** — Notificações automáticas (e-mail/WhatsApp) e exemplo de
      deploy paralelo na AWS
