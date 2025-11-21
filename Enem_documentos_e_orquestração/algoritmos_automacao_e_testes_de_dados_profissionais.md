# Guia profissional de algoritmos de automação e testes de dados (versão estendida)

> Foco: algoritmos e padrões para automação de pipelines de dados e testes robustos, usando frameworks modernos, fundamentados em estruturas de dados sólidas.
>
> Público-alvo: engenheiros de dados, analytics engineers, cientistas de dados com responsabilidades de produção, MLOps e times de plataforma.

---

## 1. Objetivos, princípios e anti‑padrões

### 1.1. Objetivos

- Padronizar **algoritmos de automação** para pipelines de dados (batch, streaming e quase real-time).
- Definir **tipos de testes de dados** e como implementá-los de forma sistemática em vários níveis (unitário, integração, contrato, e2e).
- Orientar o uso de **frameworks de ponta** (dbt tests, Great Expectations, Soda Core, Pytest, Hypothesis, ferramentas de observabilidade).
- Conectar tudo isso com **estruturas de dados** clássicas, garantindo soluções eficientes, escaláveis e previsíveis.

### 1.2. Princípios de engenharia

1. **Confiabilidade acima de tudo**  
   Falhas de dados são tão graves quanto falhas de código. A pergunta "os dados estão certos?" deve ter uma resposta rastreável.

2. **Idempotência e reprodutibilidade**  
   - Reprocessar a mesma janela/partição não pode corromper resultados.  
   - Dado código + configuração + insumo, o resultado deve ser reprodutível.

3. **Observabilidade e rastreabilidade**  
   - Todo teste/automação deixa rastros claros: logs, métricas, *traces* e, quando possível, tabelas de auditoria.  
   - "O que mudou?" e "quando quebrou?" devem ser perguntas fáceis de responder.

4. **Data-as-code & Policy-as-code**  
   - Regras de dados (constraints, contratos, expectativas) versionadas junto com o código.  
   - Políticas (ex.: limites de latência, SLOs de frescor, limites de volume) expressas em arquivos de configuração/testes.

5. **Eficiência por design**  
   - Escolher estruturas de dados e algoritmos com complexidade adequada ao volume.  
   - Evitar *full scans* desnecessários e reprocessamentos completos sem necessidade.

### 1.3. Anti‑padrões a evitar

- Testes apenas "olho clínico" em notebooks (sem automação).  
- Pipelines dependentes de execução manual de scripts.  
- Falta de contratos claros entre camadas (raw/silver/gold) ou entre serviços.  
- Tolerar *data leaks* silenciosos (ex.: valores impossíveis, outliers grotescos).  
- Dados críticos sem owner declarado nem SLO de qualidade/atualização.

---

## 2. Fundamentos de estruturas de dados aplicadas a dados

Abaixo, um mapeamento entre estruturas de dados clássicas e problemas típicos em engenharia e testes de dados.

### 2.1. Visão geral e complexidade

| Estrutura            | Uso principal em dados                                      | Operações típicas (tempo médio) |
|----------------------|-------------------------------------------------------------|----------------------------------|
| Array / lista        | Séries temporais, janelas, batches ordenados                | acesso O(1), inserção fim O(1)  |
| Hash map / dict      | Contagens, índices em memória, caches                       | lookup O(1), inserção O(1)      |
| Set                  | Deduplicação, integridade referencial, domínios            | pertence? O(1)                  |
| Heap / fila prioridade | Ordenar jobs por prioridade, top‑K, filas críticas        | inserção O(log n), pop O(log n) |
| Árvore / B‑Tree      | Índices em banco, buscas por intervalo                     | busca O(log n)                  |
| Grafo (DAG)          | Lineage, dependências entre pipelines/tabelas              | topo sort O(V+E)                |
| Estruturas aproximadas | Bloom Filter, HyperLogLog, Count‑Min Sketch              | operação O(1), memória reduzida |

### 2.2. Vetores / Arrays / Tabelas (listas ordenadas)

- Representam linhas de uma tabela, séries temporais, janelas deslizantes.
- Usos:
  - **Validações de sequência** (ex.: monotonicidade de datas, ordenação por timestamp).  
  - **Janela deslizante (sliding window)** para detecção de outliers locais ou quebras de padrão.
- Boas práticas:
  - Sempre que possível, delegar operações de janela ao warehouse (SQL window functions) para evitar trazer tudo à memória.

### 2.3. Hash maps / Dicionários

- Mapeamentos chave → valor (ex.: `particao → contagem`, `categoria → frequência`).
- Usos típicos:
  - **Contagem de frequências**: histogramas, distribuição de categorias.  
  - **Reconciliação de volumes** entre camadas (raw, silver, gold).  
  - **Caches** de resultados de validação entre etapas para evitar recomputar queries pesadas.

### 2.4. Conjuntos (sets)

- Ideais para testar **pertinência** e **domínios**.
- Exemplos:
  - `set(chaves_fato) ⊆ set(chaves_dimensão)`.  
  - Domínios esperados de colunas categóricas (ex.: `{'M', 'F', 'N'}`).  
  - Comparação de domínios entre versões: `set(col_v1) == set(col_v2)`.

### 2.5. Árvores / Índices (B‑Trees, segment trees)

- Mais conceituais na camada de teste (os índices físicos estão no banco), mas fundamentais para raciocinar sobre:
  - **Custo de queries de teste** (com ou sem índice adequado).  
  - **Checks por intervalo** (datas e ranges numéricos).
- Em cenários específicos, árvores de segmentos podem ser usadas em sistemas próprios de monitoramento para:
  - Agregar métricas por intervalos de tempo ou intervalos numéricos em O(log n).

### 2.6. Grafos

- Representam **lineage de dados** e dependências entre tabelas/pipelines.
- Usos:
  - Cálculo de ordem topológica de execução de pipelines (DAG).  
  - Propagação de falhas: dado um nó quebrado, identificar nós descendentes potencialmente inválidos.  
  - Otimização de testes: rodar testes apenas nas partes do grafo afetadas por uma mudança.

### 2.7. Filas e filas de prioridade

- Em orquestradores e workers de validação:
  - **Fila simples**: jobs aguardando execução.  
  - **Fila de prioridade**: jobs críticos primeiro (ex.: tabelas usadas por dashboards executivos).  
- Algoritmo básico de scheduling pode usar um heap (priority queue) ordenado por SLA ou impacto de negócio.

### 2.8. Estruturas aproximadas

- **Bloom Filter:** detectar rapidamente se um elemento "provavelmente já foi visto" (deduplicação aproximada).  
- **HyperLogLog:** estimar cardinalidade (número de elementos distintos) em grandes streams, útil para testes de diversidade de valores.  
- **Count‑Min Sketch:** estimar frequências de elementos (heavy hitters) com memória limitada.

---

## 3. Algoritmos de automação de dados

### 3.1. Janela deslizante para validação de séries temporais

**Problema:** garantir que uma métrica ou volume se mantenha dentro de desvios aceitáveis ao longo do tempo.

**Estrutura de dados:** array + janela deslizante.

**Idéia geral:**

1. Ordenar por `dt` ou timestamp.  
2. Manter uma janela de tamanho `k` (últimos dias/partições).  
3. Calcular média e desvio padrão dentro da janela.  
4. Se o valor atual estiver fora de `mean ± N * std`, disparar alerta.

**Complexidade:** O(n) usando técnica de janela com atualização incremental de soma e soma dos quadrados.

**Pseudocódigo simplificado:**

```python
def sliding_anomaly(values, k=7, n_std=3):
    alerts = []
    window = []
    sum_x = 0.0
    sum_x2 = 0.0

    for i, v in enumerate(values):
        window.append(v)
        sum_x += v
        sum_x2 += v * v

        if len(window) > k:
            old = window.pop(0)
            sum_x -= old
            sum_x2 -= old * old

        if len(window) == k:
            mean = sum_x / k
            var = sum_x2 / k - mean * mean
            std = max(var, 0) ** 0.5
            if std > 0 and abs(v - mean) > n_std * std:
                alerts.append((i, v, mean, std))

    return alerts
```

### 3.2. Deduplicação incremental com conjuntos

**Problema:** remover duplicados em fluxos de dados sem custo explosivo.

**Estruturas:** set / hash map.

**Algoritmo simplificado:**

1. Definir chave de unicidade (ex.: `ID`, `hash(campo1, campo2, dt)`).  
2. Manter um conjunto de chaves já vistas para uma partição ou janela de tempo.  
3. Ao ler novo registro:
   - Se chave estiver no set → marcar como duplicado e descartar ou registrar.  
   - Caso contrário → inserir no set e processar.

**Escalabilidade:**

- Para fluxos gigantes, usar **Bloom Filter** para detecção rápida de já-vistos (aceitando falsos positivos).  
- Em ambientes distribuídos, distribuir deduplicação por partição de chave (hash partitioning).

### 3.3. Reconciliação de contagens entre camadas (raw vs silver vs gold)

**Problema:** garantir que volumes entre camadas sejam consistentes.

**Estruturas:** maps/dicionários por partição.

**Algoritmo:**

1. Calcular para cada camada (raw, silver, gold) um dicionário `partição → contagem`.  
2. Unir as chaves e comparar contagens com tolerância relativa/absoluta.  
3. Gerar relatório estruturado de discrepâncias.

**Exemplo de lógica:**

```python
def reconcile_counts(raw, silver, gold, tol_pct=0.01):
    all_keys = set(raw) | set(silver) | set(gold)
    report = []
    for k in sorted(all_keys):
        r = raw.get(k, 0)
        s = silver.get(k, 0)
        g = gold.get(k, 0)
        def diff(a, b):
            if a == 0 and b == 0:
                return 0.0
            return abs(a - b) / max(a, b)
        if diff(r, s) > tol_pct or diff(s, g) > tol_pct:
            report.append({"partition": k, "raw": r, "silver": s, "gold": g})
    return report
```

### 3.4. Detecção de chaves órfãs (integridade referencial)

**Problema:** garantir que fatos sempre encontrem sua dimensão.

**Estruturas:** conjuntos.

**SQL direto (warehouse):**

```sql
SELECT COUNT(*) AS orphans
FROM fato f
LEFT JOIN dim d ON f.chave = d.chave
WHERE d.chave IS NULL;
```

**Uso em frameworks:**

- dbt: teste `relationships`.  
- Great Expectations: `expect_column_values_to_be_in_set` ou `expect_compound_columns_to_be_unique` conforme o caso.

### 3.5. Amostragem inteligente (reservoir sampling)

**Problema:** inspecionar dados grandes sem ler tudo em memória.

**Estrutura:** algoritmo de reservoir sampling.

**Propriedade:** retorna uma amostra uniforme de tamanho `k` sem conhecer `N` de antemão.

### 3.6. Detecção de drift de schema e de dados

**Problema:** detectar mudanças silenciosas em schemas ou distribuições.

**Estruturas:** sets (para colunas) + histogramas (para distribuições).

- Schema drift: comparar `set(colunas_atual)` com `set(colunas_esperadas)`.  
- Data drift: comparar histogramas/resumos numéricos anteriores com atuais (KS-test, PSI, etc.).

Automatizar como parte de pipelines de validação, com thresholds e severidade (warning vs fail).

---

## 4. Frameworks de ponta para testes de dados (com exemplos)

### 4.1. dbt tests

- Ideal para projetos orientados a SQL e warehouses.  
- Tipos de testes:
  - **Genéricos**: `not_null`, `unique`, `accepted_values`, `relationships`, etc.  
  - **Custom**: regras de negócio específicas, expressas como queries.

**Exemplo de `schema.yml` para uma tabela Gold:**

```yaml
version: 2

models:
  - name: tb_notas
    description: "Notas consolidadas por inscrito/ano."
    columns:
      - name: ANO
        tests:
          - not_null
      - name: ID_INSCRICAO
        tests:
          - not_null
          - unique
      - name: NOTA_MATEMATICA
        tests:
          - not_null
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              max_value: 1000
```

### 4.2. Great Expectations

- Framework declarativo de expectativas para dados (Python).  
- Integra com arquivos locais, warehouses, data lakes, etc.

**Exemplo de suite simples (YAML):**

```yaml
expectation_suite_name: tb_notas_suite
expectations:
  - expectation_type: expect_column_values_to_not_be_null
    kwargs:
      column: NOTA_REDACAO
  - expectation_type: expect_column_values_to_be_between
    kwargs:
      column: NOTA_MATEMATICA
      min_value: 0
      max_value: 1000
  - expectation_type: expect_table_row_count_to_be_between
    kwargs:
      min_value: 1
```

### 4.3. Soda Core / SodaCL

- Linguagem declarativa (`SodaCL`) para checks de dados em YAML.
- Bom para times que já usam YAML como padrão de configuração.

**Exemplo:**

```yaml
checks for tb_notas:
  - row_count > 0
  - missing_count(NOTA_REDACAO) = 0
  - avg(NOTA_MATEMATICA) between 300 and 800
  - schema:
      warn:
        when required column missing: ["ANO", "ID_INSCRICAO"]
```

### 4.4. Pytest + Hypothesis (property-based tests)

- **Pytest** para organizar testes automatizados em Python.  
- **Hypothesis** para gerar dados de teste automaticamente e testar propriedades gerais.

**Exemplo conceitual com Hypothesis:**

```python
from hypothesis import given
from hypothesis import strategies as st

@given(st.lists(st.integers()))
def test_clean_is_idempotent(xs):
    cleaned_once = clean(xs)
    cleaned_twice = clean(cleaned_once)
    assert cleaned_once == cleaned_twice
```

---

## 5. Tipos de testes de dados (camadas)

### 5.1. Testes de schema e contrato

- Checam se o schema está conforme o esperado:
  - Presença de colunas obrigatórias.  
  - Tipos de dados corretos.  
  - Constraints básicas (not_null, unique).  
- Devem existir, no mínimo, para todas as tabelas Gold e para as tabelas Silver mais críticas.

### 5.2. Testes de qualidade e consistência

- Checam se os dados "fazem sentido":
  - Ranges numéricos (ex.: notas entre 0 e 1000).  
  - Distribuições (ex.: porcentagem de nulos, cardinalidade de categorias).  
  - Regras de negócio (ex.: data de conclusão ≥ data de início).

### 5.3. Testes de regressão de métricas

- Comparam métricas chaves entre versões ou execuções:
  - Row count (diferença percentual).  
  - Médias, desvios, quantis.  
  - Mudanças em proporções (ex.: % aprovados).

- Úteis para detectar quebras silenciosas após mudanças em código/pipeline.

### 5.4. Testes de lineage / dependências

- Garantem que a ordem de execução respeita o DAG e que não há referências circulares.
- Em dbt, grande parte vem "de graça" via grafo de modelos. Em ambientes custom, o grafo pode ser modelado explicitamente.

### 5.5. Testes de performance

- Verificam se tempos de execução e consumo de recursos permanecem abaixo de limites.
- Podem ser automatizados via medições em CI/CD e thresholds definidos em código ou config.

### 5.6. Níveis de severidade

- **ERROR / fail:** quebra pipeline, impede publicação (ex.: PK com duplicata, row_count = 0).  
- **WARNING:** não quebra pipeline, mas dispara alerta (ex.: aumento de 5% em nulos dentro de faixa aceitável).  
- **INFO:** métricas observáveis sem ação imediata.

---

## 6. Padrões de implementação (design patterns de dados)

### 6.1. Pirâmide de testes de dados

1. **Testes unitários de transformação** (base da pirâmide)  
   - Funções e UDFs isoladas.  
   - Testes em Pytest com pequenos datasets em memória.

2. **Testes de contrato e schema**  
   - dbt/GE/Soda sobre tabelas Silver/Gold.

3. **Testes de regressão de métricas & e2e**  
   - Validam fluxos completos para janelas menores em ambientes de QA.

### 6.2. Testar "na borda da camada"

- **Raw:** integridade básica (arquivo existe, linhas > 0, encoding, parse).  
- **Silver:** schema, tipos, chaves principais, integridade referencial.  
- **Gold:** regras de negócio, métricas de produto, consistência temporal, limites esperados.

### 6.3. Padrão "partição + full refresh"

- Estrategicamente:
  - **Full refresh** em ambientes de QA para garantir consistência global.  
  - **Incremental por partição** em produção (para performance), com testes que comparem incremental vs full em amostras/ambientes dedicados.

### 6.4. Blue‑green ou shadow tables

- Em migrações grandes:
  - Criar tabela nova (ex.: `tb_notas_v2`).  
  - Popular em paralelo com a antiga.  
  - Rodar testes de regressão entre `tb_notas` e `tb_notas_v2`.  
  - Somente após aprovação, promover `v2` a tabela principal (rename/swap).

---

## 7. Integração com orquestradores, CI/CD e agentes

### 7.1. Orquestradores (Airflow, Prefect, Dagster, etc.)

- Cada pipeline deve ter tarefas explícitas de validação:

```text
extract → load_raw → validate_raw → transform_to_silver → validate_silver → build_gold → validate_gold → publish
```

- Falha em qualquer etapa de validação **interrompe o pipeline** e registra o erro no sistema de monitoramento.

### 7.2. CI/CD

- Pull Requests que alteram pipelines, UDFs ou contratos de dados devem:
  - Rodar testes de unidade (Pytest etc.).  
  - Rodar testes de dados em ambiente de QA/preview (dbt test, GE, Soda).  
  - Exibir resultado em comentários/checagens obrigatórias do PR.

### 7.3. Agentes MCP / Data Agents

- Devem seguir as mesmas regras definidas em `AGENTS.md`, com ênfase em:
  - **Safeguards**: limites de linhas, tempo de execução, bloqueio de DDL destrutivo.  
  - **Auditoria**: registrar quem executou qual query, quando e com qual propósito.  
  - **Planejamento orientado a testes**: sempre propor quais testes serão criados/ajustados junto com a mudança sugerida.

---

## 8. Checklist de maturidade em automação e testes de dados

### 8.1. Níveis sugeridos

- **Nível 1 – Básico (ad‑hoc)**  
  - Testes manuais em notebooks.  
  - Pouca ou nenhuma automação.  
  - Falhas descobertas por usuários de negócio.

- **Nível 2 – Fundacional**  
  - Orquestrador para pipelines críticos.  
  - Alguns testes de schema em tabelas Gold.  
  - Monitoramento rudimentar de volumes.

- **Nível 3 – Profissional**  
  - Testes sistemáticos em várias camadas (raw/silver/gold).  
  - Framework especializado (dbt/GE/Soda) integrado ao fluxo.  
  - CI/CD com checagens de dados para PRs.  
  - Registros estruturados de auditoria.

- **Nível 4 – Avançado / Data Platform**  
  - Data contracts formais entre times.  
  - Lineage completo, com impacto de mudanças visível antes do deploy.  
  - Monitoramento contínuo de qualidade e drift.  
  - Alertas baseados em SLOs de dados.

### 8.2. Checklist resumido

1. **Automação**
   - [ ] Pipelines críticos são orquestrados por DAG, não por scripts manuais.  
   - [ ] Há algoritmos claros de deduplicação, reconciliação e monitoramento de volumes.  
   - [ ] Reprocessos são idempotentes e documentados.

2. **Testes**
   - [ ] Todas as tabelas Gold têm testes de schema e qualidade.  
   - [ ] Há testes de integridade referencial entre fatos e dimensões.  
   - [ ] Mudanças em pipelines são acompanhadas de testes de regressão de métricas.

3. **Frameworks**
   - [ ] Pelo menos um framework especializado (dbt/GE/Soda) está integrado ao fluxo.  
   - [ ] Pytest é usado para componentes Python críticos (ETL, transformação, validação).  
   - [ ] Há uso (ou plano) de property-based testing para funções complexas.

4. **Estruturas de dados & eficiência**
   - [ ] Algoritmos de validação levam em conta a complexidade em grandes volumes.  
   - [ ] Conjuntos, maps e amostragens são usados de forma consciente para evitar *full scans* desnecessários.  
   - [ ] Há documentação das principais técnicas e estruturas usadas nos pipelines.

5. **Governança e ownership**
   - [ ] Cada tabela Gold crítica tem um owner claro.  
   - [ ] Há processos definidos para aprovar mudanças de schema.  
   - [ ] Falhas de dados geram *post-mortems* com ações de prevenção.

---

## 9. Conexão com demais documentos e próximos passos

Este guia deve ser lido em conjunto com:

- Documentos de **orquestração de backend e dashboards** (API, ingestion, workers, dashboards).  
- Documentos de **orquestração de SQL e agentes de dados** (pipelines SQL, agentes, governança).  
- `AGENTS.md`, que define regras gerais de atuação dos agentes MCP neste repositório.

Próximos passos recomendados:

1. Mapear o nível atual de maturidade dos projetos com base neste documento.  
2. Definir uma trilha incremental (ex.: do nível 1 → 2 → 3) com ações concretas e responsáveis.  
3. Criar templates (código, YAML, exemplos de testes) para que novos projetos já nasçam alinhados a este padrão.  
4. Incorporar este guia em sessões de onboarding e *design reviews* de pipelines de dados.

