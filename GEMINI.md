# ENEM Data Robotics V2 - Contexto e Regras do Assistente

Este arquivo define o contexto, regras e padrões para o desenvolvimento e manutenção do projeto **Enem Data Robotics V2**.

## 1. Visão Geral do Projeto

O **Enem Data Robotics V2** é um produto de dados avançado projetado para processar, analisar e visualizar microdados do ENEM (1998-2024). O projeto utiliza uma arquitetura moderna de **Lakehouse Local** (Medallion Architecture) e expõe insights através de uma API FastAPI e um Dashboard interativo em React.

### Objetivos
- **Engenharia de Dados:** Pipelines ETL robustos (Raw → Silver → Gold).
- **Governança:** Validação de qualidade de dados (Soda Core) e orquestração agêntica.
- **Analytics:** Visualizações avançadas (mapas, heatmaps, radar charts).
- **IA:** Assistente de Chat integrado para análise de dados (Genkit/LLMs).

---

## 2. Stack Tecnológica

### Backend (Python 3.12+)
- **Gerenciamento de Dependências:** Poetry (`pyproject.toml`).
- **API:** FastAPI, Uvicorn, Pydantic v2.
- **Dados:** Pandas, Polars (implícito), PyArrow, DuckDB.
- **Qualidade de Dados:** Soda Core.
- **CLI:** Typer.
- **IA:** Google Generative AI SDK.
- **Relatórios:** WeasyPrint, XlsxWriter.
- **Testes:** Pytest, Pytest-Asyncio.

### Frontend (React + Vite)
- **Framework:** React 18, Vite 7 (TypeScript).
- **Estilização:** Tailwind CSS, Radix UI, Framer Motion.
- **Visualização de Dados:** AmCharts 5, Highcharts, D3.js, Plotly.js, Recharts (implícito em componentes).
- **Mapas:** TopoJSON Client.
- **Gerenciamento de Estado:** React Context (FilterContext, LayoutContext).
- **Testes E2E:** Playwright.

### Infraestrutura
- **Containerização:** Docker, Docker Compose.
- **Orquestração:** Conceito de "Orquestrador Agêntico" (customizado em `src/enem_project/orchestrator`).

---

## 3. Arquitetura e Estrutura de Diretórios

O projeto segue estritamente uma estrutura modular.

```
/
├── data/                   # Lakehouse (NUNCA COMITE ARQUIVOS AQUI)
│   ├── 00_raw/             # Dados imutáveis (CSVs originais)
│   ├── 01_silver/          # Dados limpos/parquet (Saneados)
│   └── 02_gold/            # Tabelas de negócio/agregadas (DuckDB/Parquet)
├── dashboard/              # Frontend React
│   ├── src/
│   │   ├── api/            # Clientes HTTP (Axios/Fetch)
│   │   ├── components/     # Componentes UI e Gráficos
│   │   ├── context/        # Estado Global
│   │   └── pages/          # Rotas da aplicação
├── src/                    # Código Fonte Backend
│   └── enem_project/
│       ├── api/            # Rotas FastAPI (Routers)
│       ├── config/         # Configurações (Settings, Paths)
│       ├── data/           # Pipelines ETL (raw_to_silver, etc.)
│       ├── infra/          # IO, Database, Logging, Security
│       ├── orchestrator/   # Lógica do Agente Orquestrador
│       └── services/       # Lógica de Negócio (Reports, Analytics)
├── tests/                  # Testes Unitários e de Integração
└── Enem_documentos_e_orquestração/ # Documentação da Arquitetura (LEIA ANTES DE MUDAR ARQUITETURA)
```

---

## 4. Regras de Desenvolvimento (Mandatório)

### 4.1. Engenharia de Dados
1.  **Imutabilidade:** A pasta `data/00_raw` é somente leitura. Nunca altere arquivos originais.
2.  **IO Centralizado:** Use sempre `enem_project.infra.io` ou `enem_project.infra.db` para ler e escrever dados. Não use `open()` ou `pd.read_csv` diretamente nos scripts de negócio.
3.  **Caminhos:** Use `enem_project.config.paths` para resolver diretórios. Nunca faça hardcode de caminhos (ex: `C:/Users/...`).
4.  **DuckDB:** Use DuckDB para consultas analíticas pesadas sobre arquivos Parquet na camada Silver/Gold.

### 4.2. Backend (Python)
1.  **Tipagem:** Use Type Hints estritos em todas as funções.
2.  **Pydantic:** Use modelos Pydantic para validação de entrada/saída da API e Schemas de dados.
3.  **Async:** Rotas de API que fazem IO (banco de dados, chamadas externas) devem ser `async`.
4.  **Logging:** Use `loguru` em vez de `print`.

### 4.3. Frontend (React)
1.  **Componentização:** Crie componentes pequenos e reutilizáveis em `src/components/ui` (padrão shadcn/ui ou similar).
2.  **Gráficos:** Componentes de visualização complexa (AmCharts/D3) devem ser isolados em seus próprios arquivos (ex: `src/components/NotasAmMap.tsx`).
3.  **API Client:** Todas as chamadas ao backend devem passar por `src/api/client.ts` ou serviços específicos em `src/api/`. Não use `fetch` diretamente nos componentes.

---

## 5. Workflows Comuns

### Rodar o Backend
```bash
poetry run uvicorn enem_project.api.main:app --reload --port 8000
```

### Rodar o Frontend
```bash
cd dashboard
npm run dev
```

### Rodar Pipelines de Dados (Exemplo)
```bash
# Via CLI (se implementado)
poetry run enem etl-raw-to-silver --ano 2023
```

### Testes
```bash
# Backend
poetry run pytest

# Frontend E2E
cd dashboard
npx playwright test
```

---

## 6. Instruções para o Agente (Você)

1.  **Contexto Primeiro:** Antes de responder a perguntas sobre arquitetura ou dados, leia os arquivos em `Enem_documentos_e_orquestração/`.
2.  **Segurança:** Nunca exponha chaves de API ou dados sensíveis de `data/00_raw` no chat.
3.  **Consistência:** Ao criar novos componentes React, siga o estilo visual existente (Tailwind CSS, Radix UI). Ao criar scripts Python, siga o padrão do `src/enem_project`.
4.  **Orquestração:** Respeite a lógica de "Orquestrador Agêntico". Se o usuário pedir para criar um novo fluxo de dados, sugira implementá-lo como um Workflow dentro de `src/enem_project/orchestrator/workflows`.
5.  **Genkit:** O projeto possui integração com Genkit (`.genkit/`). Ao trabalhar com IA/Prompts, verifique se há fluxos definidos nessa estrutura.

---
**Data de Atualização:** 06/12/2025
**Versão do Projeto:** V2
