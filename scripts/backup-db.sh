#!/bin/bash
# Backup automático do banco Postgres do Sistema de Gestão.
# Uso: rodar via cron (diariamente é o recomendado).
# Gera um dump comprimido em backups/ e apaga automaticamente
# backups com mais de RETENTION_DAYS dias.

set -euo pipefail

PROJECT_DIR="/opt/sistema-gestao"
BACKUP_DIR="${PROJECT_DIR}/backups"
RETENTION_DAYS=14
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="gestao_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"
cd "$PROJECT_DIR"

echo "[$(date)] Iniciando backup..."

docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U gestao gestao | gzip > "${BACKUP_DIR}/${FILENAME}"

SIZE=$(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "[$(date)] Backup criado: ${FILENAME} (${SIZE})"

# Remove backups mais antigos que RETENTION_DAYS
DELETED=$(find "$BACKUP_DIR" -name "gestao_*.sql.gz" -mtime +${RETENTION_DAYS} -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$(date)] ${DELETED} backup(s) antigo(s) (>${RETENTION_DAYS} dias) removido(s)."
fi

echo "[$(date)] Backup concluído com sucesso."
