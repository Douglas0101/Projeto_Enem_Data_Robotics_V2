# Arquitetura do Projeto ENEM Data Robotics

## 1. Visão Geral

O projeto **ENEM Data Robotics** implementa um *data platform* completo para os microdados do ENEM (1998–2024), cobrindo:

- Ingestão de dados brutos fornecidos pelo INEP  
- Padronização e persistência em formato **Parquet** (camada *silver*)  
- Auditoria de qualidade, geração de metadados e relatórios (camada *gold*)  
- Exposição dos dados para consumo em **dashboards, notebooks, APIs e modelos de ML**

A arquitetura foi desenhada combinando boas práticas de **engenharia de dados** e **engenharia de software**, com foco em:

- Reprodutibilidade  
- Observabilidade (logging, auditoria, relatórios)  
- Modularidade (agentes, workflows e camadas bem definidas)  
- Escalabilidade (configuração de hardware e I/O separadas)

---

## 2. Camadas da Arquitetura

A arquitetura é organizada em **cinco grandes camadas**:

1. **Dados Brutos (Raw)**  
2. **Dados Padronizados (Silver)**  
3. **Dados Consumíveis (Gold)**  
4. **Orquestração & Aplicação**  
5. **Consumo Analítico (Dashboards e Afins)**

### 2.1. Camada Raw (`data/00_raw`)

Responsável por armazenar **exatamente** os artefatos fornecidos pelo INEP, ano a ano:

- Arquivos CSV de microdados:  
  - `MICRODADOS_ENEM_YYYY.csv`  
- Dicionários de dados:  
  - `Dicionário_Microdados_ENEM_YYYY.xlsx` / `.ods`  
- Provas e gabaritos:  
  - PDFs `PROVAS E GABARITOS` / `PROVAS e GABARITOS`  
- Documentos técnicos e de apoio:  
  - Editais, manuais do inscrito, manuais de redação, relatórios pedagógicos, etc.

**Objetivo:** preservar a fonte oficial, servir como *truth source* e ponto de partida dos pipelines de ETL.

---

### 2.2. Camada Silver (`data/01_silver`)

Camada de dados **padronizados** e otimizados para processamento:

- Arquivos Parquet anuais:
  - `microdados_enem_1998.parquet`  
  - `...`  
  - `microdados_enem_2024.parquet`  

Esses arquivos são o resultado do fluxo de:

- Leitura dos CSVs brutos  
- Aplicação de regras de limpeza e normalização (tipos, nomes de colunas, encoding etc.)  
- Escrita em Parquet, favorecendo:
  - Melhor compressão  
  - Melhor performance de leitura para análises e dashboards  

**Responsáveis principais:**

- `src/enem_project/data/raw_to_silver.py`  
- `src/enem_project/orchestrator/agents/etl.py`  
- `src/enem_project/orchestrator/workflows/etl_workflow.py`

---

### 2.3. Camada Gold (`data/02_gold`)

Camada de dados **consumíveis, auditados e documentados**:

- `parquet_audit_report.parquet`  
  - Consolidado de métricas de qualidade, checks aplicados e resultados por dataset.  
- `variaveis_meta.parquet`  
  - Metadados das variáveis (nome, descrição, tipo lógico, categoria, origem etc.).

**Função principal:**  
Servir de base para:

- Dashboards de monitoramento da qualidade  
- Catálogo de dados / dicionário de variáveis  
- Consumo por times de negócio e ciência de dados com confiança na qualidade do dado

**Responsáveis principais:**

- `src/enem_project/orchestrator/agents/parquet_quality.py`  
- `src/enem_project/orchestrator/agents/validation.py`  
- `src/enem_project/orchestrator/agents/reporting.py`  
- `src/enem_project/orchestrator/workflows/audit_workflow.py`

---

### 2.4. Orquestração & Aplicação (`src/enem_project`)

#### 2.4.1. CLI do Projeto

- `src/enem_project/cli.py`  
  - Ponto de entrada para execução via linha de comando.  
  - Deve expor comandos de alto nível, como:
    - `enem etl --anos 1998-2024`
    - `enem audit --anos 2010-2024`
    - `enem run-all` (exemplo)

#### 2.4.2. Configuração

- `config/hardware.py` (raiz)  
- `src/enem_project/config/hardware.py`  
- `src/enem_project/config/paths.py`  
- `src/enem_project/config/settings.py`

Esses módulos concentram:

- Parametrização de caminhos de dados (raw, silver, gold)  
- Configuração de recursos de hardware (paralelismo, memória, etc.)  
- *Feature flags* e parâmetros de execução dos workflows

#### 2.4.3. Infraestrutura (I/O e Logging)

- `src/enem_project/infra/io.py`  
  - Abstrações para leitura/escrita de CSV, Parquet e possivelmente outras fontes.  
- `src/enem_project/infra/logging.py`  
  - Configuração de logs centralizada, padronizando:
    - Formato de mensagens  
    - Níveis de log (INFO, WARNING, ERROR, DEBUG)  
    - Integração com workflows e agentes

#### 2.4.4. Orquestração & Segurança

- `src/enem_project/orchestrator/base.py`  
  - Classes base para workflows e agentes (contratos, hooks, etc.).  
- `src/enem_project/orchestrator/context.py`  
  - Contexto de execução (parâmetros globais, ambiente, caminhos, datas de referência).  
- `src/enem_project/orchestrator/security.py`  
  - Políticas de segurança, controle de acesso ou validações de integridade.

#### 2.4.5. Agentes

Localizados em `src/enem_project/orchestrator/agents/`:

- `data_ingestion.py`  
  - Responsável pela **ingestão** dos dados brutos da camada Raw.
- `etl.py`  
  - Aplica transformações e prepara os dados para Parquet (Silver).  
- `cleaning.py`  
  - Aplica regras de limpeza avançada sobre a camada Silver, usando contratos de schema e metadados para filtrar outliers, normalizar domínios e remover duplicados.  
- `class_engineering.py`  
  - Constrói classes analíticas/socioeconômicas (por exemplo, `CLASS_FAIXA_ETARIA`, `CLASS_RENDA_FAMILIAR` e `CLASS_NOTA_GLOBAL`) a partir do dataset limpo, com lógica robusta para lidar com valores ausentes (`NaN`/`pd.NA`) sem quebrar o pipeline.  
- `parquet_quality.py`  
  - Aplica checagens de qualidade sobre arquivos Parquet:
    - Schema esperado  
    - Campos obrigatórios  
    - Percentual de nulos  
    - Regras de consistência  
- `validation.py`  
  - Validações adicionais (regras de negócio, faixas de valores, chaves únicas, etc.).  
- `reporting.py`  
  - Geração de relatórios estruturados de qualidade e metadados (Gold).

#### 2.4.6. Workflows

Localizados em `src/enem_project/orchestrator/workflows/`:

- `etl_workflow.py`  
  - Coordena:
    1. Leitura da configuração  
    2. Execução do agente de ingestão  
    3. Execução do agente de ETL  
    4. Escrita na camada Silver  

- `audit_workflow.py`  
  - Coordena:
    1. Leitura da Silver  
    2. Execução dos agentes de qualidade/validação  
    3. Geração de relatórios de auditoria e metadados  
    4. Escrita na camada Gold  

---

### 2.5. Consumo Analítico (Dashboards)

Embora os dashboards não estejam versionados nesse repositório, a arquitetura **pressupõe**:

- Tools de BI (Power BI, Looker, Superset, etc.) conectados a:
  - **Camada Silver** para análises detalhadas/avançadas  
  - **Camada Gold** para visões consolidadas e monitoramento de qualidade  
- Notebooks de ciência de dados importando diretamente:
  - `data/01_silver/*.parquet`  
  - `data/02_gold/*.parquet`  

---

## 3. Fluxo de Dados Ponta-a-Ponta

### 3.1. Pipeline ETL (Raw → Silver)

1. **Download & armazenamento**  
   - INEP → diretórios anuais em `data/00_raw/microdados_enem_YYYY/`.

2. **Ingestão**  
   - Agente `data_ingestion.py` lê os arquivos de entrada (CSV, dicionário, etc.).  
   - Usa `infra/io.py` para abstrair caminhos e formatos.  

3. **Transformação & Padronização**  
   - `etl.py` + `raw_to_silver.py`:
     - Padronizam tipos de dados.  
     - Normalizam nomes de colunas e categorias.  
     - Preparam a estrutura final de microdados.

4. **Gravação em Silver**  
   - Escrita de `microdados_enem_YYYY.parquet` em `data/01_silver/`.

---

### 3.2. Pipeline de Qualidade & Auditoria (Silver → Gold)

1. **Leitura da Silver**  
   - `audit_workflow.py` carrega os Parquets da camada Silver.

2. **Checks de Qualidade**  
   - `parquet_quality.py` aplica checks técnicos (schema, nulos, tamanhos, etc.).  
   - `validation.py` aplica checks de negócio (faixas válidas, consistência entre campos, etc.).

3. **Geração de Relatórios & Metadados**  
   - `reporting.py` consolida resultados em:
     - `parquet_audit_report.parquet`  
     - `variaveis_meta.parquet`  

4. **Gravação em Gold**  
   - Arquivos são salvos em `data/02_gold/`.

---

### 3.3. Consumo em Dashboards

1. Ferramentas de BI / notebooks são configurados para ler:  
   - Diretamente de `data/01_silver/*.parquet` (visões analíticas avançadas)  
   - De `data/02_gold/*.parquet` (visões consolidadas, metadados, qualidade)

2. Algumas possíveis visões:
   - Evolução de notas do ENEM por ano, região, rede de ensino etc.  
   - Painel de qualidade dos dados (percentual de nulos, valores atípicos, anos com issues).  
   - Catálogo de variáveis do ENEM com descrição e tipo.

---

## 4. Qualidade, Testes e Documentação

### 4.1. Testes Automatizados (`tests/`)

- `tests/test_data_pipelines.py`  
  - Testa a integridade do fluxo de dados (Raw → Silver → Gold).  
- `tests/test_quality_audit.py`  
  - Testa regras de auditoria, formato de saídas e consistência de relatórios.

Esses testes devem ser executados em:

- Desenvolvimento local  
- Pipeline de CI/CD (quando configurado)

### 4.2. Documentação (`Enem_documentos_e_orquestração/`)

Os arquivos:

- `arquitetura_projeto_enem_data_robotics.md` / `.pdf`  
- `guia_avancado_de_engenharia_de_dados_para_ciencia_de_dados.*`  
- `guia_avancado_de_engenharia_de_software_para_ciencia_de_dados.*`  
- `guia_orquestrado_mcp_para_projetos_de_ciencia_de_dados.*`  
- `orquestrador_qualidade_nativa_ds_ia_seguranca.*`

servem como base conceitual e guia de boas práticas para:

- Evolução da arquitetura  
- Padronização de novos pipelines  
- Governança, qualidade e segurança

---

## 5. Boas Práticas de Desenvolvimento

- **Separação de responsabilidades**  
  - Configuração, infra, agentes e workflows em módulos distintos.  
- **Logs ricos**  
  - Mensagens claras para cada etapa do pipeline, facilitando depuração.  
- **Imutabilidade das camadas de dados**  
  - Camada Raw não deve ser modificada após ingestão.  
- **Testes como parte do fluxo de desenvolvimento**  
  - Toda alteração relevante nos pipelines deve vir acompanhada de testes.  
- **Documentação sempre atualizada**  
  - Alterações na arquitetura → atualização dos arquivos em `Enem_documentos_e_orquestração/`.

---

## 6. Próximos Passos Possíveis

Algumas evoluções naturais dessa arquitetura:

1. **Pipeline de CI/CD**  
   - Rodar `pytest` + lint a cada commit.  
   - Publicar artefatos (por exemplo, relatórios de qualidade) automaticamente.

2. **Camada de API**  
   - Expor consultas básicas sobre Silver/Gold via API (FastAPI, por exemplo).  

3. **Feature Store / Camadas temáticas**  
   - Criar datasets analíticos específicos (ex.: desempenho por escola, por município, etc.).  

4. **Monitoramento contínuo**  
   - Métricas de qualidade do dado integradas a dashboards de observabilidade.
