# Orquestração e agentes para banco de dados e SQL em projetos profissionais de ciência de dados

Este documento descreve uma arquitetura de referência e padrões de implementação para **orquestração de pipelines SQL** e uso de **agentes de dados** em projetos profissionais de ciência de dados.

Foco:
- Pipelines de dados baseados em SQL (ETL/ELT)
- Múltiplos bancos (PostgreSQL, Snowflake, BigQuery, etc.)
- Camada de agentes para acesso controlado, auditável e reutilizável
- Boas práticas de produção (observabilidade, segurança, versionamento)

---

## 1. Visão geral da arquitetura

Componentes principais:

1. **Orquestrador de pipelines**  
   - Define DAGs (grafo de dependências) de jobs SQL.  
   - Agenda execuções (diárias, horárias, em resposta a eventos).  
   - Controla *retries*, SLAs, alertas e logs.

2. **Camada de agentes de dados (Data Agents)**  
   - Responsável por se conectar aos bancos, gerar e executar SQL com segurança.  
   - Implementa políticas (limites de linhas, whitelists de schemas/tabelas, mascaramento de dados sensíveis).  
   - Oferece uma API de alto nível para analistas, cientistas de dados e serviços.

3. **Camada de dados**  
   - **Zona bruta (raw)**: dados pouco ou nada transformados.  
   - **Zona de staging**: dados limpos, normalizados.  
   - **Zona de modelo/analytics (mart)**: tabelas de fatos e dimensões para consumo (dashboards, modelos de ML).

4. **Camada de consumo**  
   - Dashboards (BI, aplicações internas).  
   - Modelos de ML, notebooks, serviços de API.

5. **Metadados e governança**  
   - Catálogo de dados (schemas, tabelas, lineage, owners).  
   - Regras de qualidade de dados (data quality checks).  
   - Auditoria de acessos e execuções de queries.

---

## 2. Padrões de orquestração de pipelines SQL

### 2.1. Estrutura conceitual de DAG

Um DAG típico de ciência de dados orientado a SQL pode envolver:

- `ingest_raw_*`: ingestão de dados para zona bruta.  
- `transform_*`: limpeza, normalização, joins.  
- `build_marts_*`: construção de tabelas de métricas e dimensões.  
- `quality_checks_*`: validação de contagens, ranges, chaves.  
- `refresh_views_*`: *views* materializadas para dashboards.

Cada nó do DAG é um job que executa um ou mais scripts SQL (ou macros dbt, stored procedures, etc.).

### 2.2. Requisitos de produção

- **Idempotência**: rodar o mesmo job para a mesma partição não pode duplicar dados.  
- **Particionamento temporal**: usar colunas de data (ex.: `dt`, `ingestion_date`) para reprocessar janelas específicas.  
- **Controle de dependências**: jobs só rodam quando os pais estão completos.  
- **Retry com backoff**: quedas de conexão ou timeouts são comuns em grandes cargas.  
- **Paralelismo controlado**: evitar sobrecarregar o banco com jobs pesados simultâneos.

### 2.3. Exemplo de definição de pipeline (pseudo-code TypeScript)

Abaixo um exemplo genérico de definição de DAG em TypeScript, independente de orquestrador específico (poderia ser adaptado para Airflow, Prefect, Temporal, etc.).

```ts
// src/pipelines/user_behavior_mart.pipeline.ts

export interface TaskContext {
  executionDate: string; // ex: '2025-11-18'
  partition: string; // ex: '2025-11-17'
}

export interface PipelineTask {
  id: string;
  dependencies?: string[];
  run: (ctx: TaskContext) => Promise<void>;
}

export interface PipelineDefinition {
  id: string;
  schedule: string; // cron expression
  tasks: PipelineTask[];
}

export const userBehaviorMartPipeline: PipelineDefinition = {
  id: 'user_behavior_mart',
  schedule: '0 3 * * *', // roda diariamente às 03:00
  tasks: [
    {
      id: 'ingest_raw_events',
      async run(ctx) {
        // chama agente SQL para rodar script de ingestão
        await sqlAgent.runScript('ingest_raw_events.sql', { partition: ctx.partition });
      },
    },
    {
      id: 'transform_sessions',
      dependencies: ['ingest_raw_events'],
      async run(ctx) {
        await sqlAgent.runScript('transform_sessions.sql', { partition: ctx.partition });
      },
    },
    {
      id: 'build_user_behavior_mart',
      dependencies: ['transform_sessions'],
      async run(ctx) {
        await sqlAgent.runScript('build_user_behavior_mart.sql', { partition: ctx.partition });
      },
    },
    {
      id: 'quality_checks',
      dependencies: ['build_user_behavior_mart'],
      async run(ctx) {
        await sqlAgent.runScript('quality_checks_user_behavior.sql', { partition: ctx.partition });
      },
    },
  ],
};
```

---

## 3. Camada de agentes de dados (Data Agents)

### 3.1. Papel dos agentes

Um **agente de dados** é um componente de software que:

- Centraliza a lógica de conexão e autenticação com os bancos.  
- Aplica *guardrails* de segurança e performance antes de executar SQL.  
- Oferece uma API de alto nível para operações comuns:
  - Executar scripts SQL versionados (no repositório).  
  - Rodar queries parametrizadas (com *binding* seguro).  
  - Paginando e limitando resultados.  
  - Obter metadados (schemas, colunas, estatísticas).  
- Em cenários com LLMs/IA generativa, pode:
  - Traduzir perguntas em linguagem natural para SQL.  
  - Validar SQL sugerido por LLM antes da execução.  
  - Explicar o resultado ou o plano de execução.

### 3.2. Interface base de um agente em TypeScript

```ts
// src/agents/sqlAgent.ts

export type Dialect = 'postgres' | 'snowflake' | 'bigquery';

export interface QueryOptions {
  rowLimit?: number;
  timeoutMs?: number;
  dryRun?: boolean;
}

export interface SqlAgent {
  dialect: Dialect;

  runQuery<T = any>(sql: string, params?: any[], options?: QueryOptions): Promise<T[]>;

  runScript<T = any>(scriptName: string, params?: Record<string, any>, options?: QueryOptions): Promise<T[]>;

  getTables(schema?: string): Promise<string[]>;

  getTableColumns(table: string, schema?: string): Promise<{ name: string; type: string }[]>;

  explainQuery(sql: string, params?: any[]): Promise<any>;
}
```

### 3.3. Implementação de um agente para PostgreSQL

```ts
// src/agents/postgresSqlAgent.ts

import { Pool } from 'pg';
import fs from 'fs';
import path from 'path';
import { SqlAgent, Dialect, QueryOptions } from './sqlAgent';

export class PostgresSqlAgent implements SqlAgent {
  dialect: Dialect = 'postgres';
  private pool: Pool;

  constructor(connectionString: string) {
    this.pool = new Pool({ connectionString });
  }

  private enforceGuardrails(sql: string, options?: QueryOptions) {
    const limit = options?.rowLimit ?? 10000;

    // Exemplo simples: garantir que SELECT tenha LIMIT
    if (/^\s*select/i.test(sql) && !/limit\s+\d+/i.test(sql)) {
      sql = `${sql} LIMIT ${limit}`;
    }

    // Bloquear comandos perigosos em contexto de leitura
    if (/drop\s+table/i.test(sql) || /truncate\s+/i.test(sql)) {
      throw new Error('Comando potencialmente destrutivo bloqueado pelo agente.');
    }

    return sql;
  }

  async runQuery<T = any>(sql: string, params: any[] = [], options?: QueryOptions): Promise<T[]> {
    const guardedSql = this.enforceGuardrails(sql, options);

    if (options?.dryRun) {
      console.log('[DRY RUN] SQL:', guardedSql, 'params:', params);
      return [];
    }

    const client = await this.pool.connect();
    try {
      if (options?.timeoutMs) {
        await client.query(`SET statement_timeout = ${options.timeoutMs}`);
      }
      const result = await client.query(guardedSql, params);
      return result.rows as T[];
    } finally {
      client.release();
    }
  }

  async runScript<T = any>(scriptName: string, params: Record<string, any> = {}, options?: QueryOptions): Promise<T[]> {
    const scriptPath = path.join(__dirname, '..', 'sql', scriptName);
    let sql = fs.readFileSync(scriptPath, 'utf-8');

    // substituição simples de variáveis (idealmente usar template engine segura)
    Object.entries(params).forEach(([key, value]) => {
      const token = new RegExp(`{{${key}}}`, 'g');
      sql = sql.replace(token, typeof value === 'string' ? `'${value}'` : String(value));
    });

    return this.runQuery<T>(sql, [], options);
  }

  async getTables(schema?: string): Promise<string[]> {
    const rows = await this.runQuery<{ table_name: string }>(
      `SELECT table_name
       FROM information_schema.tables
       WHERE table_schema = $1
       ORDER BY table_name`,
      [schema ?? 'public']
    );
    return rows.map((r) => r.table_name);
  }

  async getTableColumns(table: string, schema = 'public'): Promise<{ name: string; type: string }[]> {
    const rows = await this.runQuery<{ column_name: string; data_type: string }>(
      `SELECT column_name, data_type
       FROM information_schema.columns
       WHERE table_name = $1 AND table_schema = $2
       ORDER BY ordinal_position`,
      [table, schema]
    );

    return rows.map((r) => ({ name: r.column_name, type: r.data_type }));
  }

  async explainQuery(sql: string, params: any[] = []): Promise<any> {
    const rows = await this.runQuery(`EXPLAIN ${sql}`, params);
    return rows;
  }
}
```

---

## 4. Organização dos scripts SQL

### 4.1. Estrutura de diretórios

```text
sql/
  raw/
    ingest_raw_events.sql
    ingest_raw_users.sql
  staging/
    transform_sessions.sql
  marts/
    build_user_behavior_mart.sql
    build_revenue_mart.sql
  quality_checks/
    quality_checks_user_behavior.sql
  utils/
    create_temp_indexes.sql
```

Princípios:

- Scripts pequenos e focados em responsabilidades específicas.  
- Nomear por domínio e nível (raw, staging, mart).  
- Uso intensivo de `WITH` e *CTEs* para legibilidade.  
- Parametrização por partição (`{{partition}}`), tenant, ambiente, etc.

### 4.2. Exemplo de script SQL parametrizado

```sql
-- sql/marts/build_user_behavior_mart.sql

INSERT INTO mart.user_behavior_mart (dt, user_id, session_count, events_count)
SELECT
  '{{partition}}'::date AS dt,
  s.user_id,
  COUNT(DISTINCT s.session_id) AS session_count,
  COUNT(e.event_id) AS events_count
FROM staging.sessions s
LEFT JOIN staging.events e
  ON e.session_id = s.session_id
WHERE s.dt = '{{partition}}'
GROUP BY 1, 2;
```

---

## 5. Fluxos profissionais típicos

### 5.1. Pipeline diário para métricas de produto

1. Orquestrador dispara pipeline `user_behavior_mart` às 03:00 UTC.  
2. `ingest_raw_events` carrega dados do dia anterior para `raw.events`.  
3. `transform_sessions` normaliza e estrutura sessões em `staging.sessions`.  
4. `build_user_behavior_mart` agrega métricas em `mart.user_behavior_mart`.  
5. `quality_checks` valida contagens mínimas, duplicidades, *nulls* críticos.  
6. Dashboards de produto leem diretamente de `mart.user_behavior_mart`.

### 5.2. Fluxo ad-hoc guiado por agentes

1. Cientista de dados formula uma pergunta de negócio.  
2. Front-end (ou notebook) envia pedido a um serviço de **assistant de dados**.  
3. O assistant utiliza um LLM para sugerir SQL, baseado em metadados de schema.  
4. O SQL é passado ao **agente de dados**, que:
   - Valida se as tabelas usadas são permitidas.  
   - Aplica `LIMIT` e filtros obrigatórios.  
   - Registra auditoria (quem pediu, query, timestamp).  
5. O resultado é retornado em formato tabular para exploração.

---

## 6. Observabilidade, auditoria e governança

### 6.1. Logs e métricas de pipelines

- Logar para cada task:
  - `pipeline_id`, `task_id`, `execution_date`, `partition`.  
  - Status (SUCCESS/FAILED/SKIPPED), duração, contagem de linhas processadas.  
  - Erros (stack trace, SQL problemático).

- Expor métricas em sistemas como Prometheus, DataDog, etc.:  
  - **latência** dos jobs.  
  - **taxa de falhas**.  
  - **tempo médio de queries** por banco.

### 6.2. Auditoria de queries

O agente de dados deve registrar:

- Usuário/serviço chamador.  
- SQL (normalizado se possível).  
- Parâmetros (possivelmente mascarados).  
- Número de linhas retornadas/modificadas.  
- Horário de execução.

Isso facilita:

- Responder a incidentes de segurança.  
- Entender custos (especialmente em warehouses como Snowflake/BigQuery).  
- Otimizar queries mais frequentes.

### 6.3. Segurança e controle de acesso

- Autenticação forte (OIDC, OAuth2, SSO) na camada de API/assistente.  
- *Role-based access control* (RBAC) para schemas e tabelas.  
- Mascaramento de dados sensíveis (PII, PHI) no nível de visão ou coluna.  
- Segregação de ambientes (dev/stage/prod) com credenciais distintas e pipelines isolados.

---

## 7. Integração com dashboards e ciência de dados

### 7.1. Consumo por dashboards

- Dashboards devem ler preferencialmente de **marts estáveis** (não de staging/raw).  
- As tabelas de mart devem ter:
  - Particionamento por data.  
  - Convenções consistentes de nomes de colunas.  
  - Documentação no catálogo (descritivo, dono, SLA de atualização).

### 7.2. Consumo por notebooks/modelos de ML

- Cientistas de dados podem usar o agente de dados em notebooks (via SDK) para:
  - Ler features diretamente de `mart`/`feature store`.  
  - Persistir predições em tabelas específicas.  
  - Rodar *experiments* controlados com partições e amostragens.

- O mesmo conjunto de queries/pipelines usados em produção deve ser reutilizável em ambiente de experimentação sempre que possível.

---

## 8. Checklist de maturidade para projetos profissionais

1. **Orquestração**
   - [ ] Todos os pipelines críticos estão sob um orquestrador central.  
   - [ ] DAGs possuem dependências explícitas e janelas de reprocessamento claras.  
   - [ ] Há *retries* configurados para erros transitórios.

2. **Agentes de dados**
   - [ ] Toda query de produção passa por uma camada de agente (não conexão direta).  
   - [ ] Guardrails de LIMIT, blacklist/whitelist de comandos e schemas estão configurados.  
   - [ ] Logs de auditoria são armazenados em local seguro.

3. **SQL & modelagem**
   - [ ] Scripts SQL versionados em repositório (Git).  
   - [ ] Estrutura de zonas (raw, staging, mart) bem definida.  
   - [ ] Documentação mínima das principais tabelas e colunas.

4. **Observabilidade e segurança**
   - [ ] Métricas de jobs e queries expostas em ferramenta de monitoramento.  
   - [ ] Alertas configurados para falhas e atrasos de pipelines.  
   - [ ] Controles de acesso revisados periodicamente.

---

## 9. Próximos passos

- Introduzir ferramentas de transformação e orquestração especializadas (dbt, Airflow, Prefect, Dagster) integradas com os agentes.  
- Adicionar camada de geração de SQL assistida por LLM com validação rígida no agente.  
- Criar *playbooks* de operação para incidentes de dados (SEVs de dados).  
- Automatizar testes de regressão de dados (data unit tests) dentro dos pipelines.

Este blueprint pode ser adaptado ao seu stack específico (PostgreSQL, Snowflake, BigQuery, Databricks etc.), mantendo os mesmos princípios de orquestração, agentes e governança profissional de dados.

