# ENEM Data Robotics – AGENTS & REPO GUIDELINES

Este arquivo consolida, em forma operacional, as diretrizes dos documentos:

- `Enem_documentos_e_orquestração/arquitetura_enem_data_robotics.md`
- `Enem_documentos_e_orquestração/arquitetura_projeto_enem_data_robotics.md`
- `Enem_documentos_e_orquestração/guia_avancado_de_engenharia_de_dados_para_ciencia_de_dados.md`
- `Enem_documentos_e_orquestração/guia_avancado_de_engenharia_de_software_para_ciencia_de_dados.md`
- `Enem_documentos_e_orquestração/guia_orquestrado_mcp_para_projetos_de_ciencia_de_dados.md`
- `orquestracao_fluxo_backend_ciencia_dados_dashboard.md`
- `orquestracao_e_agentes_sql_projetos_ciencia_dados.md`

Aplica-se a desenvolvedores e a agentes MCP que atuem neste repositório.

---

## 1. Runtime, Build & Execução

**Stack principal (referência):**

- Python 3.11+
- Poetry para gestão de dependências / virtualenv
- Typer para CLI
- Pytest para testes
- DuckDB/Parquet como engine analítica local/offline (podendo ser substituído/espelhado para warehouses na nuvem)

### 1.1. Instalação & Ambiente

- Sempre trabalhar com virtualenv isolado:
  - `poetry install`
  - `poetry run enem --help`
- Nunca instalar dependências globais sem necessidade.
- Sempre commitar o `poetry.lock` para garantir reprodutibilidade.

### 1.2. Execução

- Comandos de referência:

  - Listar comandos disponíveis:
    - `poetry run enem --help`
  - Processar microdados “fim a fim” para um ano:
    - `poetry run enem run-all --year 2022`
  - Rodar apenas pipeline de raw → silver:
    - `poetry run enem raw-to-silver --year 2022`
  - Rodar apenas silver → gold:
    - `poetry run enem silver-to-gold --year 2022`

- Sempre preferir a CLI oficial (Typer) em vez de chamar scripts “na mão”.

---

## 2. Arquitetura & Camadas de Dados (Medallion)

### 2.1. Estrutura de diretórios

- `data/`
  - `00_raw/` – microdados originais do ENEM (CSV, dicionários, PDFs, etc.). **Imutável**.
  - `01_silver/` – dados padronizados por ano (Parquet), ex.: `microdados_enem_YYYY.parquet`.
  - `02_gold/` – dados consumíveis:
    - `cleaned/` – microdados limpos por ano.
    - `classes/` – classes analíticas e resumos por ano.
    - `reports/` – relatórios de limpeza e auditoria.
    - `parquet_audit_report.parquet`, `variaveis_meta.parquet`, tabelas temáticas (`tb_*`).
- `src/enem_project/`
  - `config/` – `settings.py`, `paths.py`, `hardware.py`; **fonte única de caminhos, anos e perfil de hardware**.
  - `infra/` – I/O (CSV/Parquet/DuckDB), logging, utilitários de baixo nível.
  - `data/` – lógica de ETL e datasets analíticos (`raw_to_silver.py`, `silver_to_gold.py`, `metadata.py`, etc.).
  - `orchestrator/` – agentes, workflows, contexto, segurança.
  - `cli.py` – ponto de entrada Typer (`enem`).
- `tests/` – testes Pytest (`test_*.py`).
- `Enem_documentos_e_orquestração/` – documentação de arquitetura, guias e orquestração MCP.

### 2.2. Princípios de dados

- Camada Raw (`data/00_raw/`) **nunca** deve ser alterada pelos pipelines.
- Todos os artefatos de Silver e Gold devem ser **reconstruíveis a partir de código**.
- Contratos de dados (schemas, níveis de granularidade) devem ser estáveis e documentados.
- Sempre que inserir/alterar colunas em Silver ou Gold:
  - Atualizar os metadados (`variaveis_meta.parquet` via `metadata.py`).
  - Atualizar ou criar testes de contrato em `tests/`.

---

## 3. Camada Gold & Dashboards

- Gold é a camada **diretamente consumida** por dashboards e análises.
- Tabelas Gold devem ser:
  - Estáveis (sem mudanças frequentes de schema).
  - Documentadas (descrição de colunas, unidades, granularidade).
  - Otimizadas para leitura (tipos corretos, colunas particionadas/chave, etc.).

### 3.1. Convenções de nomenclatura

- Tabelas temáticas: `tb_<tema>.parquet`
  - Ex.: `tb_notas.parquet`, `tb_notas_stats.parquet`, `tb_notas_geo.parquet`.
- Colunas:
  - `ANO` sempre presente e inteiro.
  - Identificadores derivados (ex.: `ID_INSCRICAO`) quando necessário.
  - Medidas com prefixos ou sufixos descritivos: `_mean`, `_std`, `_min`, `_max`, etc.

### 3.2. Exemplos de contratos

- `data/02_gold/tb_notas.parquet`
  - Nível: 1 linha por inscrito/ano (após anonimização).
  - Colunas:
    - `ANO`
    - `ID_INSCRICAO` (derivado de `NU_INSCRICAO` quando necessário)
    - `NOTA_CIENCIAS_NATUREZA`
    - `NOTA_CIENCIAS_HUMANAS`
    - `NOTA_LINGUAGENS_CODIGOS`
    - `NOTA_MATEMATICA`
    - `NOTA_REDACAO`

- `data/02_gold/tb_notas_stats.parquet`
  - Nível: 1 linha por ano.
  - Colunas:
    - `ANO`
    - Para cada `NOTA_*`: `*_count`, `*_mean`, `*_std`, `*_min`, `*_median`, `*_max`.

- `data/02_gold/tb_notas_geo.parquet`
  - Nível: 1 linha por combinação `ANO` + região/UF/município (conforme design).
  - Colunas: métricas de notas agregadas por geografia.

---

## 4. Metadados & Dicionários de Dados

- `variaveis_meta.parquet` é a **fonte da verdade** sobre variáveis dos microdados.
  - Contém nome original, descrição, tipo, categoria, mapeamentos, etc.
- Todo pipeline que adiciona ou remove variáveis em Silver/Gold deve:
  - Atualizar esse metaparquet.
  - Manter a consistência da documentação com os arquivos oficiais do INEP.

---

## 5. Estilo de Código & Organização

- Seguir PEP8 e boas práticas de Python.
- Estruturar funções pequenas, puras e testáveis.
- Evitar “scripts monolíticos”; preferir módulos coesos em `infra/`, `data/`, `orchestrator/`.

---

## 6. Testes, Qualidade & Contratos

- Cobrir com testes:
  - Principais funções de transformação (raw → silver, silver → gold).
  - Regras de limpeza e imputação.
  - Contratos de schema (colunas obrigatórias, tipos, ranges).
- Usar Pytest com organização clara:
  - `tests/test_raw_to_silver.py`
  - `tests/test_silver_to_gold.py`
  - `tests/test_metadata.py`
- É aceitável não ter 100% de cobertura, mas priorizar código de alto impacto (pipelines, orquestrador, geração de tabelas Gold).

---

## 7. Orquestração MCP / Agentes neste Repositório

Agentes (MCP, backend e SQL) que atuem neste projeto devem seguir, além dos guias de arquitetura ENEM, os fluxos de referência descritos em:

- `orquestracao_fluxo_backend_ciencia_dados_dashboard.md` (fluxo de engenharia de dados e backend para dashboards em TypeScript/JavaScript).
- `orquestracao_e_agentes_sql_projetos_ciencia_dados.md` (orquestração de pipelines SQL e camada de agentes de dados).

Em outras palavras: qualquer automação ou código gerado por agentes aqui dentro deve respeitar **camadas bem definidas**, **orquestração explícita** e **acesso controlado a banco de dados**.

### 7.1. Fluxo orquestrado de backend e dashboards (TS/JS)

Quando o usuário solicitar construção ou evolução de APIs, ingestão de eventos ou dashboards, o agente deve:

- Pensar o fluxo fim a fim em 5 camadas, conforme o documento de backend:
  1. **Ingestão de dados** – APIs/serviços que recebem eventos, validam payloads e empilham em filas ou camadas brutas.
  2. **Orquestrador de jobs de ciência de dados** – workers/schedulers que executam pipelines de transformação, feature engineering e scoring.
  3. **Camada de dados analíticos** – banco/warehouse otimizado para leitura, com tabelas de fatos e dimensões.
  4. **API de métricas para dashboards** – endpoints REST/GraphQL para exposição de métricas, agregações e time series.
  5. **Dashboards** – front-end em JS/TS consumindo a API de métricas.

- Ao propor ou gerar código:
  - Separar claramente **ingestão**, **orquestração** (workers/cron), **camada analítica** e **API de leitura**.
  - Evitar que dashboards consultem diretamente bancos transacionais; sempre passar pela API/marts.
  - Garantir que qualquer exemplo de código em TS/JS siga padrões de:
    - Tratamento de erros e logs.
    - Paginação e filtros na API de métricas.
    - Uso de variáveis de ambiente para credenciais e URIs, nunca hard-coded.

### 7.2. Fluxo orquestrado de banco de dados e SQL (Data Agents)

Quando o usuário solicitar trabalho direto com bancos relacionais, pipelines SQL ou ajustes em tabelas analíticas, o agente deve seguir o modelo de **agente de dados** descrito no documento SQL:

- **Sem acesso direto “na unha” ao banco em produção**:
  - Toda conexão deve ser abstraída por um *SqlAgent* (ou equivalente), responsável por autenticação, timeouts e pooling.
  - Queries devem passar por guardrails: `LIMIT` automático em SELECTs exploratórios, bloqueio de comandos DDL destrutivos (`DROP`, `TRUNCATE`, etc.) e configuração de `statement_timeout` quando aplicável.

- **Scripts SQL versionados e organizados**:
  - Manter scripts em uma árvore clara (`sql/raw`, `sql/staging`, `sql/marts`, `sql/quality_checks`, etc.).
  - Parametrizar por partição/data (`{{partition}}`), ambiente e, quando fizer sentido, por tenant.
  - Evitar SQL “inline” gigantesco dentro do código da aplicação; preferir `runScript('build_user_behavior_mart.sql', { partition: ... })`.

- **Pipelines SQL como DAGs**:
  - Representar pipelines como DAGs com tarefas do tipo `ingest_raw_*`, `transform_*`, `build_marts_*`, `quality_checks_*`, etc.
  - Garantir **idempotência** por partição: reprocessar uma data não deve duplicar linhas nem corromper agregados.
  - Controlar dependências (ex.: `build_marts_*` só roda após `transform_*` bem-sucedido).
  - Usar *schedulers* (cron/orquestrador externo) para execuções diárias/horárias, com retries e alertas.

- **Auditoria e governança**:
  - Registrar quem acionou o agente, o SQL normalizado, parâmetros (com PII mascarada) e contagem de linhas afetadas.
  - Quando usar LLM para sugerir SQL, sempre:
    - Validar o SQL no agente antes de executar.
    - Rodar primeiro em modo `dryRun`/EXPLAIN quando possível.
    - Impor `rowLimit` e filtros obrigatórios em ambientes multi-tenant.

### 7.3. Fases macro e regras gerais para agentes MCP

Independente da tecnologia (Python, TS/JS, SQL), os agentes devem seguir as fases macro dos guias orquestrados (adaptadas ao projeto ENEM):

1. Contexto e definição de problema (o que o usuário quer ver no dashboard/análise).
2. Planejamento da solução (quais tabelas Silver/Gold, quais anos, quais métricas, quais APIs/marts).
3. Aquisição, qualidade e engenharia de dados (usar pipelines existentes, não “atalhos” diretos em Raw ou queries manuais em produção).
4. Exploração e baseline (EDA e métricas descritivas a partir de Gold/marts).
5. Design e experimentação (quando há modelagem ou novas métricas).
6. Avaliação e alinhamento com negócio (validar se o que foi entregue responde à pergunta original).
7. Industrialização (CLI, workflows, testes automatizados, integração com orquestrador).
8. Monitoramento e melhoria contínua (logs, relatórios, dashboards de saúde de dados e jobs).

Regras específicas para agentes:

- **Sempre**:
  - Ler e respeitar este `AGENTS.md` e os documentos de arquitetura/orquestração listados no início antes de grandes mudanças.
  - Propor ou atualizar **testes** quando alterar comportamento de pipelines, APIs de backend ou tabelas Gold/marts.
  - Trabalhar com planos claros (passos) e manter o usuário informado, registrando limitações ou falhas em vez de ocultá-las.

- **Nunca**:
  - Modificar dados em `data/00_raw/` ou ignorar convenções de diretórios e nomenclatura de tabelas.
  - Introduzir colunas/arquivos “ad-hoc” fora das convenções (ex.: `tb_*`, pastas `cleaned/`, `classes/`, `reports/`) sem atualizar documentação e metadados.
  - Ignorar falhas de qualidade (dados nulos inesperados, schemas diferentes, quebras de contrato) sem pelo menos logar, documentar e, quando possível, propor correção.

---

## 8. Quality Gates & Segurança Nativa (Policy as Code)

- Toda mudança relevante em pipelines, contratos de dados ou orquestração deve ser acompanhada por:
  - Testes automatizados (Pytest).
  - Verificações de qualidade (data quality checks).
  - Revisão de código (PR) com pelo menos 1 revisor.
- Política de segurança:
  - Nunca versionar credenciais, chaves ou tokens.
  - Não introduzir algoritmos de criptografia customizados.
  - Evitar dependências inseguras ou não mantidas.

Para futuras integrações com CI/CD e orquestradores externos, espera-se que este arquivo sirva como base para um conjunto de quality gates e política de qualidade formal (Policy as Code) específico deste projeto.

---

## 9. Commits, PRs & Segurança

- Commits:
  - Mensagens imperativas e claras (`Add ETL validation step`, `Refine tb_notas_geo aggregation`, etc.).
  - Mantê-los focados (uma mudança lógica por commit).
- Pull Requests:
  - Descrição curta do que foi feito.
  - Racional técnico e link para seções relevantes dos documentos de arquitetura, se aplicável.
  - Comandos para reproduzir: `pytest`, `enem` com parâmetros relevantes.
  - Impacto em dados: explicar se/como muda layout ou contratos de tabelas Silver/Gold.

- Segurança & configuração:
  - Jamais versionar CSVs brutos reais do ENEM, credenciais ou chaves.
  - Usar apenas `settings.py` e `config/hardware.py` para parametrizações de caminhos/hardware.
  - Tratar dados de inscrição (`NU_INSCRICAO`, `ID_INSCRICAO`) como sensíveis: não logar valores brutos nem expor em exemplos públicos.

Este arquivo deve ser mantido em sincronia com os documentos em `Enem_documentos_e_orquestração/` e com os artefatos de orquestração (`orquestracao_fluxo_backend_ciencia_dados_dashboard.md`, `orquestracao_e_agentes_sql_projetos_ciencia_dados.md`) sempre que a arquitetura ou os contratos de dados evoluírem.
