#!/bin/bash

# ==============================================================================
# 🚀 Docker Safe Launcher - Enem Data Robotics V2 (Docker Desktop Edition v2)
# ==============================================================================

echo "🔍 Verificando ambiente Docker Desktop..."

# 1. Verifica e Captura o Host do Docker Desktop
# Isso é crucial porque ao mudarmos o DOCKER_CONFIG abaixo, perdemos a referência do 'context'.
# Precisamos salvar o endereço do socket explicitamente.
if docker context inspect desktop-linux > /dev/null 2>&1; then
    echo "✅ Contexto 'desktop-linux' encontrado."
    # Captura o endereço do socket (ex: unix:///home/user/.docker/desktop/docker.sock)
    DESKTOP_HOST=$(docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}')
    export DOCKER_HOST="$DESKTOP_HOST"
    echo "🔗 Forçando conexão via: $DOCKER_HOST"
else
    echo "⚠️  Contexto 'desktop-linux' não encontrado. Tentando padrão..."
fi

# 2. Teste de Conectividade
if ! docker info > /dev/null 2>&1; then
    echo "❌ Não foi possível conectar ao Docker Daemon."
    echo "👉 Certifique-se que o Docker Desktop está ABERTO e rodando."
    exit 1
fi

# 3. Configuração de Isolamento de Credenciais
# Cria um config.json limpo para evitar o erro "gpg: descriptografia falhou"
echo "🔒 Isolando configuração de credenciais..."
mkdir -p .docker_isolation
echo '{ "credsStore": "" }' > .docker_isolation/config.json
export DOCKER_CONFIG=$(pwd)/.docker_isolation

# 4. Execução
echo "🐳 Iniciando build e upload dos containers..."
echo "---------------------------------------------------"

docker compose up --build