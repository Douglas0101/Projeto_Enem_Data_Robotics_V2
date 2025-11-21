# ENEM Data Robotics

Pipeline reproducível para processar microdados do ENEM em camadas raw → silver → gold, publicar um backend SQL/REST para consumo analítico e servir dashboards interativos.

## Principais componentes
- CLI Typer `enem` para orquestrar ETL completo, auditorias e preparação de dados de dashboard.
- Medallion architecture em `data/00_raw`, `data/01_silver`, `data/02_gold` com metadados versionados (`variaveis_meta.parquet`).
- Backend DuckDB + FastAPI expondo tabelas `tb_notas*` e agregados geográficos.
- Dashboard React/Vite (Chakra UI) em `dashboard/` consumindo as tabelas gold materializadas.

## Requisitos
- Python 3.12+ e Poetry (ambiente virtual dedicado).
- DuckDB e dependências nativas atendidas via `pip` (já em `pyproject.toml`).
- Node.js 18+ para desenvolver o dashboard (Vite).
- Microdados do ENEM baixados manualmente para `data/00_raw/microdados_enem_YYYY/DADOS/MICRODADOS_ENEM_YYYY.csv` (não versionar PII).

## Instalação rápida
```bash
poetry install
poetry run enem --help
```

## Estrutura de pastas
- `src/enem_project/config/` – caminhos, anos suportados, perfil de hardware.
- `src/enem_project/data/` – pipelines raw → silver (`raw_to_silver.py`) e silver → gold (`silver_to_gold.py`, metadados).
- `src/enem_project/orchestrator/` – agentes e workflows (ETL, classes, auditoria, backend SQL).
- `src/enem_project/api/` – FastAPI (rotas de dashboard + health).
- `data/` – camadas `00_raw`, `01_silver`, `02_gold`, além de `enem.duckdb`.
- `dashboard/` – front-end React/Vite para os datasets gold.
- `tests/` – Pytest para pipelines, qualidade e contratos.
- `Enem_documentos_e_orquestração/` e `AGENTS.md` – guias de arquitetura, orquestração e governança do projeto.

## Camadas de dados e artefatos
- Raw (`data/00_raw/`): microdados originais, imutáveis.
- Silver (`data/01_silver/`): Parquet padronizado por ano (`microdados_enem_YYYY.parquet`).
- Gold (`data/02_gold/`):
  - `cleaned/` microdados limpos por ano; `classes/` com engenharia de classes.
  - `tb_notas.parquet`, `tb_notas_stats.parquet`, `tb_notas_geo.parquet` (tabelas consumidas por API/dashboard).
  - `reports/` com auditorias e relatórios de limpeza; `parquet_audit_report.parquet`.
  - Metadados consolidados em `variaveis_meta.parquet`.
- DuckDB (`data/enem.duckdb`): criado por `enem --sql-backend`, registra views e pode materializar `tb_notas*`.

## Fluxos principais (CLI `enem`)
```bash
# ETL completo (raw -> silver + QA) para anos específicos
poetry run enem --ano 2022
poetry run enem --anos 2019 2020
poetry run enem --ano-inicio 2010 --ano-fim 2015

# Somente auditoria de Parquets (silver + gold)
poetry run enem --anos 2020 2021 --auditoria

# Limpeza avançada + engenharia de classes + tabelas de notas para dashboard
poetry run enem --classe --anos 2020 2021

# Inicializar backend SQL (DuckDB), registrando views e materializando tb_notas*
poetry run enem --sql-backend
```

## API analítica (FastAPI)
```bash
poetry run uvicorn enem_project.api.main:app --host 0.0.0.0 --port 8000
```
- `/health` para monitoramento.
- `/v1/dashboard/anos-disponiveis`
- `/v1/dashboard/notas/stats?ano_inicio=2015&ano_fim=2020`
- `/v1/dashboard/notas/geo?ano=2020&uf=SP&min_count=50&limit=2000`
O startup da API chama `init_sql_backend` para garantir que `enem.duckdb` e `tb_notas*` existam.

## Dashboard (React/Vite)
```bash
cd dashboard
npm install
npm run dev
```
O dashboard consome `tb_notas.parquet`, `tb_notas_stats.parquet` e `tb_notas_geo.parquet` via DuckDB/API. Gere essas tabelas executando os fluxos acima antes de abrir o front-end.

## Configuração e tuning
- Anos e caminhos: `src/enem_project/config/settings.py`.
- Perfil de hardware e streaming: `config/hardware.py` com detecção automática (CPU/RAM).
- Variáveis úteis:
  - `ENEM_MAX_RAM_GB`, `ENEM_CSV_CHUNK_ROWS`, `ENEM_ESTIMATED_ROW_BYTES`, `ENEM_STREAMING_THRESHOLD_GB`
  - `ENEM_FORCE_STREAMING` (raw → silver), `ENEM_PARQUET_STREAM_ROWS` (tb_notas streaming)
  - `ENEM_CLEANING_CHUNK_ROWS`, `ENEM_CLEANING_STREAMING_GB`, `ENEM_FORCE_CLEANING_STREAMING`
  - `ENEM_CLASS_CHUNK_ROWS`, `ENEM_CLASS_STREAMING_GB`, `ENEM_FORCE_CLASS_STREAMING`

## Testes e qualidade
- Testes automatizados: `poetry run pytest`.
- Auditoria de dados: `poetry run enem --auditoria` gera `data/02_gold/parquet_audit_report.parquet`.
- Quality gate no backend SQL: `init_sql_backend` aplica checagens em `tb_notas*` (intervalo de notas, row counts).

## Contribuição e governança
- Leia `AGENTS.md` e os guias em `Enem_documentos_e_orquestração/` antes de alterar pipelines, contratos ou orquestração.
- Nunca altere dados em `data/00_raw/`. Toda mudança em silver/gold deve ser reprodutível via código.
- Ao criar/alterar colunas em silver/gold, atualize metadados (`variaveis_meta.parquet`) e adicione testes de contrato.
- Trate `NU_INSCRICAO/ID_INSCRICAO` como sensível: não logar valores brutos, não versionar PII.
- Commits curtos, focados e imperativos; valide com `pytest` e, quando aplicável, com `enem --auditoria` ou `enem --sql-backend`.
