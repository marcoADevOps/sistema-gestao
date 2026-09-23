#!/bin/bash
# Restaura um backup do Postgres a partir de um arquivo .sql.gz gerado pelo backup-db.sh
# Uso: ./scripts/restore-db.sh backups/gestao_20260924_030000.sql.gz
#
# ATENÇÃO: isso sobrescreve os dados atuais do banco. Use com cuidado.

set -euo pipefail

PROJECT_DIR="/opt/sistema-gestao"

if [ $# -ne 1 ]; then
    echo "Uso: $0 <caminho-do-backup.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Arquivo não encontrado: $BACKUP_FILE"
    exit 1
fi

read -p "Isso vai SOBRESCREVER o banco atual com o conteúdo de ${BACKUP_FILE}. Continuar? (digite 'sim' para confirmar) " CONFIRM
if [ "$CONFIRM" != "sim" ]; then
    echo "Cancelado."
    exit 0
fi

cd "$PROJECT_DIR"

echo "Restaurando..."
gunzip -c "$BACKUP_FILE" | docker compose -f docker-compose.prod.yml exec -T db psql -U gestao gestao

echo "Restauração concluída."
