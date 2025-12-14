#!/bin/bash
# =============================================================================
# Script de limpeza Docker para o projeto ENEM Data Robotics
# Uso: ./scripts/docker-cleanup.sh
# =============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🧹 Parando e removendo containers do projeto..."
docker compose down --remove-orphans 2>/dev/null || true

echo "🔌 Removendo redes não utilizadas..."
docker network prune -f

echo "🗑️ Removendo containers órfãos do projeto (se existirem)..."
docker rm -f enem_data_robotics_api enem_data_robotics_frontend 2>/dev/null || true

echo "✅ Limpeza concluída!"
echo ""
echo "📦 Para reiniciar os serviços, execute:"
echo "   cd $PROJECT_DIR && docker compose up -d"
