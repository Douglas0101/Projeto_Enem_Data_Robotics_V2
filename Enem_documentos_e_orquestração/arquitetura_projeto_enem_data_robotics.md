# Projeto ENEM Data Robotics – Arquitetura Profissional

## 1. Visão Geral

O projeto ENEM Data Robotics é um **produto de dados** baseado em todos os microdados do ENEM de 1998 a 2024.

Objetivos principais:
- Organizar os microdados em um **data lake/lakehouse local** com camadas de dados bem definidas.
- Aplicar **engenharia de software + engenharia de dados + ciência de dados** de forma integrada.
- Viabilizar análises reprodutíveis, modelagem estatística/ML e visualizações de alta qualidade sobre o ENEM.

Camadas principais da arquitetura:
1. **Infraestrutura (infra)** – paths, IO, DuckDB, logging, config.
2. **Dados (data/ETL)** – pipelines raw → silver → gold (microdados limpos e consolidados).
3. **Domínio (domain)** – regras de negócio do ENEM, entidades e serviços.
4. **Analytics & ML** – EDA, métricas, fairness, modelos preditivos.
5. **Aplicações** – notebooks, dashboards, relatórios, CLI, orquestração futura.

---

## 2. Estrutura de Diretórios

### 2.1. Raiz do Projeto

```bash
Projeto_Enem_Data_Robotics_V2/
├── data/
│   ├── 00_raw/        # microdados originais (intocáveis)
│   ├── 01_silver/     # dados limpos/padronizados por ano
│   └── 02_gold/       # tabelas consolidadas (painéis, métricas)
├── notebooks/
│   ├── 00_exploracao/
│   ├── 10_analises_tematicas/
│   └── 90_debug_sanity/
├── src/
│   └── enem_project/
│       ├── __init__.py
│       ├── config/
│       │   ├── settings.py
│       │   └── paths.py
│       ├── infra/
│       │   ├── io.py
│       │   ├── logging.py
│       │   ├── db.py
│       │   └── schedulers/   # (futuro) Prefect/Airflow
│       ├── data/
│       │   ├── metadata.py
│       │   ├── raw_to_silver.py
│       │   ├── silver_to_gold.py
│       │   └── features.py
│       ├── domain/
│       │   ├── entities.py
│       │   ├── enums.py
│       │   └── services.py
│       ├── analytics/
│       │   ├── eda.py
│       │   ├── metrics.py
│       │   └── fairness.py
│       ├── ml/
│       │   ├── datasets.py
│       │   ├── models.py
│       │   └── evaluation.py
│       └── cli.py
├── tests/
│   ├── test_infra_io.py
│   ├── test_data_pipelines.py
│   └── test_domain_services.py
├── pyproject.toml ou setup.cfg
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

### 2.2. Camadas de Dados

- `data/00_raw/`: microdados originais do ENEM (CSV, docs, PDFs, etc.). **Nunca alterar**.
- `data/01_silver/`: dados já limpos, padronizados por ano, normalmente em Parquet.
- `data/02_gold/`: tabelas consolidadas/painéis (por exemplo: `tb_notas.parquet`, `tb_participantes.parquet`, etc.).

---

## 3. Configuração e Infraestrutura

### 3.1. Configuração (config/settings.py)

Responsável por centralizar configurações do projeto:

- Root do projeto.
- Diretórios de dados.
- Lista de anos disponíveis.
- Flags de uso de DuckDB, Polars etc.

Exemplo conceitual:

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Settings:
    project_root: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = project_root / "data"
    years: tuple[int, ...] = tuple(range(1998, 2025))
    use_duckdb: bool = True

settings = Settings()
```

### 3.2. Paths (config/paths.py)

Funções utilitárias para gerar caminhos padronizados:

```python
from pathlib import Path
from .settings import settings

def raw_dir() -> Path:
    return settings.data_dir / "00_raw"

def silver_dir() -> Path:
    return settings.data_dir / "01_silver"

def gold_dir() -> Path:
    return settings.data_dir / "02_gold"
```

### 3.3. IO e DuckDB (infra/io.py, infra/db.py)

Responsáveis por **como** ler/escrever dados (CSV, Parquet, DuckDB), independentemente do domínio ENEM.

```python
# infra/db.py
import duckdb
from .logging import logger
from ..config.paths import silver_dir

def get_duckdb_conn(db_path: str | None = None):
    path = db_path or (silver_dir().parent / "enem.duckdb")
    logger.info(f"Conectando ao DuckDB: {path}")
    return duckdb.connect(path.as_posix())
```

```python
# infra/io.py
import pandas as pd
from .logging import logger


def read_csv(path: str, sep=";", encoding="latin-1") -> pd.DataFrame:
    logger.info(f"Lendo CSV: {path}")
    return pd.read_csv(path, sep=sep, encoding=encoding, low_memory=False)


def write_parquet(df: pd.DataFrame, path: str):
    logger.info(f"Salvando Parquet: {path}")
    df.to_parquet(path, index=False)
```

### 3.4. Logging (infra/logging.py)

Configuração única de logging para o projeto (formato, nível, etc.), de forma a substituir `print()` por `logger.info()`, `logger.warning()` e `logger.error()`.

---

## 4. Camada de Dados (ETL/ELT)

### 4.1. Metadados (data/metadata.py)

Centraliza informações de variáveis ao longo dos anos:

- Nome original por ano.
- Nome padrão (padronizado ao longo da série histórica).
- Tipo de dado (int, float, category, string).
- Domínio de valores (categorias possíveis).

A partir dos dicionários XLSX/ODS de cada ano, criar uma tabela mestre de metadados:

- `ano`
- `nome_original`
- `nome_padrao`
- `descricao`
- `tipo_padrao`
- `dominio_valores`

Essa tabela pode ser salva em `data/02_gold/variaveis_meta.parquet` e/ou carregada via `metadata.py`.

### 4.2. Pipeline raw → silver (data/raw_to_silver.py)

Objetivo: transformar CSVs brutos por ano em dados limpos/padronizados, armazenados em Parquet na camada silver.

Passos:
1. Ler CSV cru a partir de `data/00_raw/microdados_enem_YYYY/DADOS/`.
2. Renomear colunas conforme metadados.
3. Incluir coluna `ANO` (se ainda não existir).
4. Ajustar tipos e codificações básicas.
5. Salvar em `data/01_silver/microdados_enem_YYYY.parquet`.

Exemplo conceitual:

```python
from ..infra.io import read_csv, write_parquet
from ..config.paths import raw_dir, silver_dir
from .metadata import get_rename_map, get_dtypes


def load_raw_microdados(ano: int):
    path = raw_dir() / f"microdados_enem_{ano}" / "DADOS" / f"MICRODADOS_ENEM_{ano}.csv"
    return read_csv(path.as_posix())


def clean_and_standardize(df, ano: int):
    rename_map = get_rename_map(ano)
    df = df.rename(columns=rename_map)
    df["ANO"] = ano
    # casts de tipos, normalização de categorias, etc.
    return df


def run_raw_to_silver(ano: int):
    df_raw = load_raw_microdados(ano)
    df_clean = clean_and_standardize(df_raw, ano)
    out_path = silver_dir() / f"microdados_enem_{ano}.parquet"
    write_parquet(df_clean, out_path.as_posix())
```

### 4.3. Pipeline silver → gold (data/silver_to_gold.py)

Objetivo: construir tabelas temáticas consolidadas, por exemplo:

- `tb_participantes` – 1 linha por participante/ano, com dados socioeconômicos.
- `tb_notas` – notas por área e redação.
- `tb_itens` – informação em nível de item, usando `ITENS_PROVA_YYYY.csv`.
- `tb_quest_hab_estudo` – a partir de 2022.

Exemplo conceitual para `tb_notas`:

```python
from ..infra.io import write_parquet
from ..config.paths import silver_dir, gold_dir
import pandas as pd


def load_silver(ano: int) -> pd.DataFrame:
    path = silver_dir() / f"microdados_enem_{ano}.parquet"
    return pd.read_parquet(path)


def build_tb_notas(anos: list[int]):
    dfs = []
    for ano in anos:
        df = load_silver(ano)
        cols = [
            "ANO", "ID_PARTICIPANTE",
            "NU_NOTA_CN", "NU_NOTA_CH",
            "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO",
        ]
        dfs.append(df[cols])
    tb_notas = pd.concat(dfs, ignore_index=True)
    write_parquet(tb_notas, (gold_dir() / "tb_notas.parquet").as_posix())
```

### 4.4. Features (data/features.py)

- Construção de variáveis derivadas (ex.: indicadores de desigualdade, agrupamentos de escolas, índices socioeconômicos compósitos).
- Funções puras, recebendo e retornando DataFrames.

---

## 5. Camada de Domínio (domain)

### 5.1. Entidades (domain/entities.py)

Representam conceitos centrais do domínio ENEM, facilitando a integração com APIs, serviços e modelos.

Exemplos:

```python
from dataclasses import dataclass


@dataclass
class Participante:
    id: int
    ano: int
    sexo: str | None
    cor_raca: str | None
    tipo_escola: str | None


@dataclass
class Resultado:
    participante_id: int
    ano: int
    nota_cn: float | None
    nota_ch: float | None
    nota_lc: float | None
    nota_mt: float | None
    nota_redacao: float | None
```

### 5.2. Enums e Constantes (domain/enums.py)

- Listas de categorias padronizadas (ex.: tipos de escola, regiões, cores/raças, etc.).
- Evitar magic strings espalhadas pelo código.

### 5.3. Serviços de Domínio (domain/services.py)

Funções que implementam regras de negócio e cálculos recorrentes, isoladas de IO e paths.

Exemplo: médias de notas por tipo de escola e ano.

```python
import pandas as pd


def media_notas_por_tipo_escola(tb_notas: pd.DataFrame, participantes: pd.DataFrame):
    df = tb_notas.merge(
        participantes[["ID_PARTICIPANTE", "TIPO_ESCOLA"]],
        on="ID_PARTICIPANTE",
        how="left",
    )

    return (
        df.groupby(["ANO", "TIPO_ESCOLA"])[
            ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
        ]
        .mean()
        .reset_index()
    )
```

Essas funções são ideais para testes unitários e reuso em notebooks, APIs, dashboards, etc.

---

## 6. Camada de Analytics & Ciência de Dados

### 6.1. Analytics (analytics/)

- `eda.py`: funções de exploração padronizadas (histogramas, boxplots, perfis de participação, etc.).
- `metrics.py`: indicadores de interesse (ex.: médias, desvios, taxas de participação, índices de desigualdade).
- `fairness.py`: análise de fairness (desempenho por gênero, cor/raça, tipo de escola, etc.).

As funções aqui devem:
- Receber DataFrames já prontos (gold).
- Produzir DataFrames com resultados ou figuras.
- Ser reutilizadas em notebooks, scripts e APIs.

### 6.2. Módulo de Modelagem (ml/)

- `datasets.py`: monta conjuntos de dados (X, y) para modelos com base nas tabelas gold.
- `models.py`: definição de modelos (sklearn, LightGBM, etc.).
- `evaluation.py`: métricas, gráficos de avaliação, comparação de modelos.

Integração futura possível com MLflow para rastrear experimentos.

---

## 7. Notebooks

### 7.1. Organização

- `notebooks/00_exploracao/`
  - EDA inicial, exploração de variáveis, sanity checks de distribuição.

- `notebooks/10_analises_tematicas/`
  - `01_desigualdade_regional.ipynb`
  - `02_escola_publica_vs_privada.ipynb`
  - etc.

- `notebooks/90_debug_sanity/`
  - Notebooks de checagem, debug de pipelines, investigações pontuais.

### 7.2. Boa Prática Fundamental

Notebooks **nunca** devem ler CSV diretamente da camada raw. Em vez disso:

```python
from enem_project.infra.io import read_parquet  # ou funções de alto nível
from enem_project.config.paths import gold_dir

tb_notas = read_parquet((gold_dir() / "tb_notas.parquet").as_posix())
```

Ou funções ainda mais semânticas construídas dentro de `enem_project`.

---

## 8. CLI e Orquestração

### 8.1. CLI (cli.py)

Uma interface de linha de comando para rodar pipelines e tarefas comuns.

Exemplo conceitual usando Typer:

```python
import typer
from .data.raw_to_silver import run_raw_to_silver
from .data.silver_to_gold import build_tb_notas
from .config.settings import settings

app = typer.Typer()


@app.command()
def etl_raw_to_silver(ano: int = None):
    anos = [ano] if ano else settings.years
    for a in anos:
        run_raw_to_silver(a)


@app.command()
def build_gold():
    build_tb_notas(list(settings.years))


if __name__ == "__main__":
    app()
```

Uso:

```bash
python -m enem_project.cli etl-raw-to-silver --ano 2010
python -m enem_project.cli build-gold
```

### 8.2. Orquestrador (futuro)

- Migrar a lógica do CLI para um orquestrador como **Prefect** ou **Airflow** para agendar pipelines.
- Permite reprocessar dados automaticamente quando saírem novos microdados (ex.: ENEM 2025 em diante).

---

## 9. Boas Práticas de Engenharia de Software

### 9.1. Controle de Ambiente

Arquivo `environment.yml` ou `pyproject.toml` declarando as dependências:

- Python 3.11+
- pandas / polars
- pyarrow
- duckdb
- jupyter
- matplotlib / seaborn (ou outra stack de visualização)
- tqdm
- pytest
- typer (para CLI)

### 9.2. Qualidade de Código

- `black` + `ruff` para formatação e lint.
- `mypy` para checagem de tipos.
- `pre-commit` configurado em `.pre-commit-config.yaml`.

### 9.3. Testes (tests/)

Testes unitários e de integração básicos:

- `test_infra_io.py` – testa funções de IO com arquivos de exemplo.
- `test_data_pipelines.py` – testa pipelines raw → silver e silver → gold em amostras pequenas.
- `test_domain_services.py` – testa funções de domínio (médias, coortes, etc.) com dados artificiais.

Objetivo: garantir reprodutibilidade e evitar regressões quando houver mudanças.

---

## 10. Roadmap de Implementação

### Fase 1 – Fundamentos

1. Criar estrutura de diretórios (`src/enem_project`, `data/01_silver`, `data/02_gold`, `notebooks/` etc.).
2. Implementar `config/settings.py` e `config/paths.py`.
3. Implementar `infra/io.py`, `infra/logging.py` e opcionalmente `infra/db.py`.
4. Criar o pipeline inicial `raw_to_silver.py` para alguns anos (ex.: 1998–2000).
5. Criar função simples em `silver_to_gold.py` para gerar `tb_notas.parquet`.

### Fase 2 – Padronização Avançada

6. Construir metadados de variáveis a partir dos dicionários XLSX/ODS e salvar em `data/02_gold/variaveis_meta.parquet`.
7. Usar esses metadados em `raw_to_silver.py` para padronizar nomes, tipos e categorias.
8. Ampliar pipelines para todos os anos 1998–2024.

### Fase 3 – Domínio & Analytics

9. Implementar entidades e serviços de domínio (`domain/`).
10. Implementar funções de analytics (`analytics/`) e alguns notebooks temáticos em `notebooks/10_analises_tematicas/`.

### Fase 4 – ML & Orquestração

11. Implementar módulo `ml/` para tarefas de modelagem.
12. Criar CLI robusta (`cli.py`) para facilitar execuções de pipelines.
13. (Opcional) Integrar com orquestrador (Prefect/Airflow) e MLflow.

---

## 11. Princípios Gerais

- **Dados brutos são imutáveis**: `data/00_raw/` nunca é modificado.
- **Tudo é reprodutível via código**: qualquer tabela em `01_silver` e `02_gold` deve ser reconstruível rodando o pipeline.
- **Separação de responsabilidades**:
  - Infra cuida de IO, logging e DB.
  - Data cuida de ETL/ELT.
  - Domain cuida de regras de negócio.
  - Analytics/ML cuida de análises e modelos.
  - Notebooks são apenas interfaces de exploração, não lugar de lógica crítica.
- **Tipagem e testes** são obrigatórios para qualquer parte central do pipeline.
- **Documentação sempre atualizada** neste canvas/README conforme a arquitetura evoluir.


---

## 12. Orquestrador Agêntico de Algoritmos

Esta seção define a arquitetura de um **orquestrador agêntico** para o projeto ENEM Data Robotics, responsável por coordenar a geração profissional de algoritmos (ETL, métricas, modelos, análises) com foco em **segurança**, **governança de dados** e **reprodutibilidade**.

### 12.1. Visão Conceitual

O orquestrador agêntico é uma camada acima dos módulos `infra`, `data`, `domain`, `analytics` e `ml`, composta por:

- **Agentes especializados** (agents) para tarefas específicas (ingestão, validação, segurança, analytics, ML, relatórios).
- Um **núcleo de orquestração** que define workflows (fluxos de trabalho) como grafos de dependências entre agentes.
- Um **contexto compartilhado** com controle de acesso (segurança) que carrega o estado da execução.
- Um **mecanismo de políticas de segurança/governança** que limita o que cada agente pode fazer/ver.

Objetivo: permitir que novas rotinas/"algoritmos" sejam compostos a partir de blocos seguros e testados, sem virar um caos de scripts soltos.

### 12.2. Estrutura de Diretórios do Orquestrador

Sugestão de estrutura dentro de `src/enem_project/`:

```bash
src/enem_project/
├── orchestrator/
│   ├── __init__.py
│   ├── base.py            # classes base de Agent, Orchestrator, Context
│   ├── context.py         # definição do contexto compartilhado
│   ├── security.py        # políticas de segurança e governança
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── data_ingestion.py
│   │   ├── validation.py
│   │   ├── security_agent.py
│   │   ├── analytics.py
│   │   ├── model_training.py
│   │   └── reporting.py
│   └── workflows/
│       ├── etl_workflow.py
│       ├── analytics_workflow.py
│       ├── ml_workflow.py
│       └── governance_workflow.py
```

### 12.3. Contexto do Orquestrador

O contexto é o "estado" que flui entre agentes. Ele deve ser:

- Tipado (com dataclasses ou pydantic).
- Versionado (possível registrar a versão do pipeline, data, parâmetros).
- Segregado por nível de sensibilidade (dados brutos, dados anonimizados, resultados agregados).

Exemplo conceitual (não definitivo):

```python
# orchestrator/context.py
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class DataHandle:
    name: str
    sensitivity: str  # "RAW", "SENSITIVE", "AGGREGATED"
    payload: Any      # DataFrame, caminho de arquivo, etc.


@dataclass
class OrchestratorContext:
    run_id: str
    params: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, DataHandle] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)

    def add_data(self, key: str, handle: DataHandle):
        self.data[key] = handle

    def get_data(self, key: str) -> DataHandle:
        return self.data[key]
```

### 12.4. Classe base de Agent e Orchestrator

#### Agent

Cada agente representa uma etapa autocontida (por exemplo: carregar dados raw, validar schema, treinar modelo, gerar relatório).

Características:

- Nome único.
- Declaração de **entradas** e **saídas**.
- Declaração de **nível de acesso** (quais tipos de dados pode ler/escrever).

Exemplo conceitual:

```python
# orchestrator/base.py
from abc import ABC, abstractmethod
from typing import List
from .context import OrchestratorContext


class Agent(ABC):
    name: str = "agent-base"
    allowed_sensitivity_read: List[str] = ["AGGREGATED", "SENSITIVE", "RAW"]
    allowed_sensitivity_write: List[str] = ["AGGREGATED", "SENSITIVE", "RAW"]

    @abstractmethod
    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        ...
```

#### Orchestrator

Responsável por:

- Registrar agentes.
- Definir a ordem de execução / grafo de dependência.
- Aplicar políticas de segurança antes/depois da execução de cada agente.
- Registrar logs e resultados.

```python
# orchestrator/base.py (continuação)

class Orchestrator:
    def __init__(self, agents: list[Agent], security_manager: "SecurityManager"):
        self.agents = agents
        self.security_manager = security_manager

    def run(self, ctx: OrchestratorContext) -> OrchestratorContext:
        for agent in self.agents:
            self.security_manager.check_agent_permissions(agent, ctx)
            ctx = agent.run(ctx)
        return ctx
```

### 12.5. Segurança e Governança

A segurança no orquestrador agêntico atua em múltiplos níveis:

1. **Classificação de dados**: cada `DataHandle` no contexto deve ter um `sensitivity`:
   - `RAW` – microdados originais, potencialmente com informações sensíveis.
   - `SENSITIVE` – dados transformados que ainda podem identificar indivíduos.
   - `AGGREGATED` – agregações estatísticas, adequadas para divulgação.

2. **Políticas de acesso por agente**:
   - Agentes como `ReportingAgent` só podem ler `AGGREGATED`.
   - `ModelTrainingAgent` pode ler `SENSITIVE`, mas não necessariamente `RAW` direto.
   - `SecurityAgent` pode inspecionar mais coisas, mas tem regras rígidas de logging.

3. **Arquivo de políticas** (ex.: `config/policies.yaml`):
   - Define quais agentes podem acessar quais tipos de dados.
   - Define restrições de uso (ex.: proibir exportar microdados brutos para fora do ambiente).

4. **Auditoria e logging estruturado**:
   - Cada execução de workflow gera um `run_id` único.
   - Logs são anexados ao contexto e também salvos em arquivo/DB.

Exemplo conceitual de `SecurityManager`:

```python
# orchestrator/security.py
from .context import OrchestratorContext, DataHandle
from .base import Agent


class SecurityException(Exception):
    ...


class SecurityManager:
    def __init__(self, policies: dict):
        self.policies = policies

    def check_agent_permissions(self, agent: Agent, ctx: OrchestratorContext):
        # Exemplo simplificado: valida apenas sensitividades
        for key, handle in ctx.data.items():
            if handle.sensitivity not in agent.allowed_sensitivity_read:
                # se agente não pode ler esse nível, tudo bem desde que ele não tente acessar
                # validação mais profunda pode ser feita se necessário
                continue

    def sanitize_output(self, handle: DataHandle) -> DataHandle:
        # ponto central para anonimização/mascaramento, se necessário
        return handle
```

### 12.6. Tipos de Agentes

#### 12.6.1. DataIngestionAgent

- Lê arquivos de `data/00_raw/`.
- Transforma em DataFrames iniciais ou em handles para processamento.
- Classificação usual: saída como `RAW`.

Local: `orchestrator/agents/data_ingestion.py`.

#### 12.6.2. ValidationAgent

- Valida schemas, tipos, domínios de valores.
- Verifica se o número de linhas bate, se não há valores impossíveis, etc.
- Em caso de falha, pode levantar exceções ou marcar o contexto como `failed`.

Local: `orchestrator/agents/validation.py`.

#### 12.6.3. SecurityAgent

- Verifica se dados sensíveis estão adequadamente mascarados/anonimizados antes de avançar de `SENSITIVE` para `AGGREGATED` ou para camadas externas.
- Aplica regras de pseudo-anonimização, remoção de identificadores, etc.

Local: `orchestrator/agents/security_agent.py`.

#### 12.6.4. AnalyticsAgent

- Usa funções de `analytics/` para produzir métricas, painéis e datasets analíticos.
- Gera saídas de nível `AGGREGATED`.

Local: `orchestrator/agents/analytics.py`.

#### 12.6.5. ModelTrainingAgent

- Usa funções de `ml/` para montar datasets, treinar modelos e salvar artefatos.
- Pode trabalhar com dados `SENSITIVE` internamente, mas sempre que possível gera resultados `AGGREGATED` para consumo externo.

Local: `orchestrator/agents/model_training.py`.

#### 12.6.6. ReportingAgent

- Gera relatórios finais (tabelas, gráficos, arquivos para dashboards) apenas a partir de dados `AGGREGATED`.

Local: `orchestrator/agents/reporting.py`.

### 12.7. Workflows Padrão

Cada workflow é um script/módulo que instancia agentes em determinada ordem e roda o `Orchestrator`.

#### 12.7.1. Workflow ETL Completo (raw → silver → gold)

Arquivo: `orchestrator/workflows/etl_workflow.py`.

Passos típicos:

1. **DataIngestionAgent** – carrega microdados de um ano.
2. **ValidationAgent** – valida o bruto.
3. **Agent(s) de ETL** (podem ser agentes específicos ou reaproveitar funções de `data/raw_to_silver.py` e `data/silver_to_gold.py`).
4. **SecurityAgent** – valida que o que vai para `gold` está dentro da política.
5. **ReportingAgent** (opcional) – gera um mini-relatório de QA.

#### 12.7.2. Workflow de Analytics

Arquivo: `orchestrator/workflows/analytics_workflow.py`.

- Lê tabelas `gold`.
- Roda um conjunto de `AnalyticsAgent`s (por tema: desigualdade regional, rede pública vs privada, etc.).
- Gera datasets agregados e relatórios.

#### 12.7.3. Workflow de Modelagem (ML)

Arquivo: `orchestrator/workflows/ml_workflow.py`.

- Carrega dados curated.
- `ValidationAgent` garante a consistência.
- `ModelTrainingAgent` treina e avalia modelos.
- `SecurityAgent` verifica fairness e restrições de uso, se configurado.

#### 12.7.4. Workflow de Governança

Arquivo: `orchestrator/workflows/governance_workflow.py`.

- Varre tabelas e artefatos.
- Verifica se estão em conformidade com níveis de sensibilidade.
- Gera relatórios de auditoria.

### 12.8. Integração com a CLI

A CLI (`cli.py`) pode ser estendida para expor os workflows do orquestrador:

Exemplo conceitual:

```python
# cli.py (trecho conceitual)

import typer
from enem_project.orchestrator.workflows.etl_workflow import run_etl_full
from enem_project.orchestrator.workflows.analytics_workflow import run_analytics
from enem_project.orchestrator.workflows.ml_workflow import run_ml

app = typer.Typer()


@app.command()
def etl_full(ano: int | None = None):
    """Roda o workflow ETL completo para um ano ou para todos os anos."""
    run_etl_full(ano)


@app.command()
def analytics():
    """Roda workflows de analytics padrão (métricas, agregações)."""
    run_analytics()


@app.command()
def ml_experiments():
    """Roda experimentos de modelagem de acordo com configuração padrão."""
    run_ml()
```

### 12.9. Segurança Específica para Geração de Algoritmos

Ao pensar em "geração profissional de algoritmos" (especialmente envolvendo modelos ou geração automática de código/rotinas), o orquestrador deve impor:

1. **Ambiente controlado**:
   - Execução apenas em ambiente isolado (sem exposição direta de microdados para fora).
   - Controle de dependências (environment.yml / pyproject.toml).

2. **Reprodutibilidade**:
   - Todos os parâmetros de execuções (seeds, hiperparâmetros, filtros de dados) ficam registrados no `OrchestratorContext.params` e/ou em logs estruturados.

3. **Fairness e ética**:
   - Antes de aceitar um modelo como "oficial", o workflow de ML roda verificações em `analytics/fairness.py`.
   - Modelos que apresentarem disparidades fortes entre grupos (sexo, cor/raça, tipo de escola) podem ser bloqueados ou marcados como experimentais.

4. **Controle de exportação**:
   - O `SecurityAgent` é o único autorizado a exportar artefatos para fora do ambiente (ex.: arquivos de resultados, relatórios), e apenas a partir de dados `AGGREGATED`.

5. **Auditoria**:
   - Cada workflow gera um relatório de auditoria com:
     - `run_id`.
     - data/hora.
     - agentes executados.
     - parâmetros usados.
     - caminhos de saída.

### 12.10. Roadmap para Implementação do Orquestrador

1. Criar o pacote `orchestrator/` com arquivos `base.py`, `context.py`, `security.py`.
2. Implementar o `OrchestratorContext` com classificação de sensibilidade.
3. Implementar a classe base `Agent` e o `Orchestrator` simples (sequencial).
4. Implementar `DataIngestionAgent` + `ValidationAgent` + `SecurityAgent` mínimos.
5. Criar o primeiro workflow `etl_workflow.py` usando esses agentes para um subconjunto de anos (ex.: 2019–2021).
6. Integrar os workflows com a CLI (`cli.py`).
7. Estender para `AnalyticsAgent`, `ModelTrainingAgent` e `ReportingAgent`.
8. Criar políticas de segurança em arquivo (ex.: `config/policies.yaml`) e fazer o `SecurityManager` ler e aplicar.
9. Evoluir para execução paralela ou baseada em grafo de dependências, se necessário (por exemplo, usando DAGs simples ou integrando com Prefect/Airflow sem quebrar a arquitetura agêntica).

Esse orquestrador agêntico passa a ser o "cérebro" operacional do projeto ENEM Data Robotics, garantindo que qualquer geração de algoritmos (ETL, métricas, modelos) respeite a arquitetura, a segurança e a governança de dados definidas no restante do projeto.

