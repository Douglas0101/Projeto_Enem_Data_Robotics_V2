# Guia Avançado de Engenharia de Dados para Ciência de Dados

> **Público-alvo:** cientistas de dados, analistas, engenheiros de dados e engenheiros de machine learning que já conhecem SQL, Python e conceitos básicos de bancos de dados e querem estruturar dados em escala para análises e modelos.

---

## 1. Por que Engenharia de Dados é crítica para Ciência de Dados

Muitos projetos de ciência de dados não falham por causa do modelo, e sim por causa dos **dados**:

- Dados difíceis de acessar
- Métricas inconsistentes entre áreas
- Pipelines frágeis, que quebram com qualquer mudança
- *Data leakage* em modelos

Engenharia de dados é o conjunto de práticas, padrões e ferramentas que garantem que cientistas de dados tenham **dados confiáveis, bem modelados e organizados**, com **reprodutibilidade** e **escala**.

### 1.1 Responsabilidades típicas de Engenharia de Dados

- Projetar e manter **arquiteturas de dados** (data lakes, warehouses, lakehouses)
- Construir **pipelines de ingestão** (batch e streaming)
- Modelar dados em **camadas analíticas** (dimensões, fatos, wide tables para ML)
- Garantir **qualidade, governança e segurança** de dados
- Otimizar **custo e performance** de consultas
- Expor dados em formatos úteis para analistas e cientistas de dados

### 1.2 Interface com Ciência de Dados

A interface ideal é um “contrato” mais ou menos assim:

- A engenharia de dados entrega **tabelas consistentes, versionadas e documentadas**
- A ciência de dados usa essas tabelas para:
  - Explorar dados
  - Criar **datasets de treinamento**
  - Construir e monitorar modelos

Cada lado pode até saber um pouco do papel do outro, mas o ganho vem quando os dois trabalham sobre uma **fundação de dados bem feita**.

---

## 2. Arquiteturas Modernas de Dados

### 2.1 Data Warehouse, Data Lake e Lakehouse

**Data Warehouse**

- Focado em **analytics** (BI, relatórios, OLAP)
- Dados limpos, estruturados, geralmente em esquema dimensional (fatos e dimensões)
- Otimizado para consultas agregadas

**Data Lake**

- Repositório bruto de dados, geralmente em armazenamento de objetos (S3, GCS, ADLS)
- Suporta dados estruturados, semiestruturados (JSON, CSV, Parquet) e não estruturados
- Bom para exploração, mas sem disciplina vira um *data swamp*

**Lakehouse**

- Combina o melhor dos dois mundos
- Dados no **data lake** com camadas de qualidade (bronze, silver, gold) + engine de consulta analítica (Spark, Databricks, Trino, etc.)
- Usa formatos de tabela com gerenciamento de metadados (Delta, Iceberg, Hudi)

### 2.2 Padrão Medallion (Bronze, Silver, Gold)

Um padrão muito usado em projetos de ciência de dados é o **medallion architecture**:

- **Bronze**: dados brutos, próximos da origem (mínimo de transformação)
- **Silver**: dados limpos, normalizados, com regras de negócio básicas aplicadas
- **Gold**: dados prontos para consumo – painéis, modelos, métricas consolidadas

Para ciência de dados:

- **Bronze** é útil para investigações forenses ou reprocessamento
- **Silver** é base para criação de features
- **Gold** concentra tabelas de alto nível (ex: *tabela de clientes com todas as métricas agregadas*)

### 2.3 Batch vs Streaming

**Batch**

- Processa grandes volumes em janelas (de hora, dia, semana)
- Mais simples de gerenciar
- Serve para a maioria dos casos de ciência de dados

**Streaming / Near Real-Time**

- Processa dados continuamente (Kafka, Kinesis, Pub/Sub, Flink, Spark Structured Streaming)
- Necessário quando:
  - Modelos precisam de **features em tempo real**
  - Monitoramento depende de latência baixa
  - Casos de uso online (recomendação em tempo real, detecção de fraude)

Uma arquitetura madura costuma ter **os dois**, com consistência garantida entre o batch e o streaming.

---

## 3. Modelagem de Dados para Analytics e Ciência de Dados

### 3.1 OLTP vs OLAP

- **OLTP (Online Transaction Processing)**: sistemas operacionais (ERP, CRM, apps) focados em gravações rápidas e consistência transacional.
- **OLAP (Online Analytical Processing)**: sistemas analíticos, focados em consultas complexas, agregações e leituras intensas.

Engenharia de dados normalmente extrai de OLTP e transforma em OLAP.

### 3.2 Modelagem Dimensional (Kimball)

Um padrão clássico para analytics:

- **Tabelas fato**: eventos ou medições (ex: vendas, transações, cliques)
- **Tabelas dimensão**: contexto (ex: cliente, produto, tempo, canal)

Vantagens:

- Facilita criação de métricas consistentes
- Bem suportada por ferramentas de BI

Exemplo de fato:

```sql
CREATE TABLE fato_vendas AS
SELECT
  pedido_id,
  cliente_id,
  produto_id,
  data_id,
  canal_id,
  quantidade,
  valor_total,
  desconto
FROM silver.vendas_normalizadas;
```

### 3.3 Tabelas Wide para Modelos (Feature Tables)

Para modelos de ML, muitas vezes é mais produtivo trabalhar com **tabelas wide**, onde cada linha representa uma entidade (cliente, pedido, sessão) e cada coluna é uma feature.

Exemplo (tabela de features de cliente):

- `cliente_id`
- `dias_desde_ultima_compra`
- `ticket_medio_30d`
- `n_itens_30d`
- `n_visitas_site_7d`
- `usou_cupom_ultimos_90d`

Essas tabelas podem ser construídas a partir de fatos e dimensões, geralmente em uma camada **gold_ml**.

### 3.4 Data Vault e Modelagem Corporativa

Em contextos de grande escala e múltiplas fontes, pode-se usar **Data Vault** como camada de integração, e a partir dela derivar modelos dimensionais e tabelas para ML.

Ponto importante: independente da técnica, o foco é ter **linhagem clara**, **histórico versionado** e **semântica consistente**.

---

## 4. Pipelines de Dados e Orquestração

### 4.1 ETL vs ELT

- **ETL (Extract, Transform, Load)**: transforma antes de carregar no destino
  - Mais comum em arquiteturas antigas ou quando o destino é limitado
- **ELT (Extract, Load, Transform)**: carrega tudo no destino (data lake/warehouse) e transforma lá
  - Padrão dominante em arquiteturas modernas na nuvem

### 4.2 Orquestração

Ferramentas comuns (conceitos gerais):

- Sistemas baseados em **DAGs** (grafos acíclicos): cada nó é uma tarefa, as arestas são dependências
- Suporte a:
  - Reprocessamento
  - *Backfills*
  - Schedules e *triggers*
  - Monitoramento e alertas

Características desejáveis em pipelines:

- **Idempotência**: rodar o mesmo job duas vezes não estraga os dados
- **Atomicidade**: uma carga inteira ou falha completamente, ou é totalmente aplicada
- **Observabilidade**: logs, métricas, alertas
- **Testes automatizados**: unitários, de integração e de dados

### 4.3 Boas práticas em DAGs

- Modelar pipelines por **domínio de negócio**, não por tecnologia
- Manter tarefas pequenas e coesas
- Reaproveitar componentes (templates) para padrões repetitivos
- Evitar lógica de negócio complexa dentro do orquestrador – preferir camadas de transformação (SQL, dbt, Spark)

---

## 5. Ingestão de Dados

### 5.1 Principais padrões de ingestão

- **Batch por arquivo**: CSV/Parquet entregues em pastas, FTP, SFTP, buckets
- **APIs**: REST/GraphQL para buscar ou receber dados
- **Eventos em streaming**: filas e *message brokers* (Kafka, Kinesis, Pub/Sub, RabbitMQ)
- **CDC (Change Data Capture)**: captura mudanças em bancos transacionais (Debezium, etc.)

### 5.2 Defesa contra problemas comuns

- Duplicatas de registros
- Esquemas que mudam silenciosamente
- Falhas intermitentes de rede/APIs
- Dados fora de ordem ou atrasados

Estratégias:

- Chaves naturais ou técnicas para de-duplicação
- *Schema registry* e validação de compatibilidade
- *Dead-letter queues* para eventos problemáticos
- *Retry* com *backoff* exponencial

---

## 6. Qualidade de Dados e Observabilidade

### 6.1 Dimensões clássicas de qualidade

- **Completude**: porcentagem de valores não nulos onde deveriam existir
- **Consistência**: mesma lógica de negócio gera os mesmos resultados em diferentes lugares
- **Acurácia**: os dados refletem a realidade
- **Atualidade (freshness)**: dados chegam dentro da janela esperada
- **Unicidade**: ausência de duplicatas indevidas

### 6.2 Testes de Dados

Tipos de testes:

- **Esquemáticos**: tipos de coluna, limites, chaves primárias/estrangeiras
- **Regras de negócio**: ex: `preco >= 0`, `data_compra >= data_cadastro`
- **Estatísticos**: distribuição, média, desvio padrão – útil para detectar *drift* de dados

Integração com pipelines:

- Falhar o job quando regras críticas forem violadas
- Marcar a tabela como "não confiável" quando algum teste de qualidade falhar

### 6.3 Observabilidade de Dados

Observar não só a **infraestrutura**, mas também o **comportamento dos dados**:

- Linhagem (de onde vem cada coluna)
- Volumetria (quantidade de linhas por partição)
- Tempos de atualização
- Mudanças de esquema

Isso é crucial para ciência de dados:

- Evita treinar modelos em dados quebrados
- Ajuda a explicar mudanças de performance dos modelos (drift)

---

## 7. Governança, Metadados e Catálogo de Dados

### 7.1 Metadados Técnicos e de Negócio

- **Técnicos**: tipos, partições, tamanho, frequência de atualização
- **De negócio**: definição da métrica, dono, exemplos de uso

### 7.2 Catálogo de Dados

Um catálogo de dados deve permitir:

- Buscar tabelas por nome, coluna ou conceito de negócio
- Ver linhagem: de quais tabelas esta depende, e quem depende dela
- Ver documentação e dono (responsável)

### 7.3 Segurança e Privacidade

- Classificar dados (público, interno, confidencial, sensível)
- Mascarar ou anonimizar PII (dados pessoais)
- Implementar controle de acesso por função/grupo (RBAC/ABAC)

Para ciência de dados, é fundamental que haja **processo claro para uso de dados sensíveis**, incluindo:

- Como solicitar acesso
- Como armazenar *features* sensíveis
- Como fazer auditoria de quem usou o quê

---

## 8. Armazenamento e Performance

### 8.1 Formatos de Arquivo

- **Row-based (linha)**: ex: CSV, JSON
  - Bons para ingestão simples e leitura linha a linha
  - Ruins para consultas analíticas pesadas
- **Columnar (colunar)**: ex: Parquet, ORC
  - Otimizados para analytics (leitura seletiva de colunas, compressão)

Para ciência de dados, formatos colunares são quase sempre preferíveis para dados históricos.

### 8.2 Particionamento e Organização

Técnicas comuns:

- **Particionamento por tempo**: `dt=AAAA-MM-DD`, `ano=AAAA/mes=MM/dia=DD`
- **Particionamento por chave de negócio**: `regiao`, `loja`, `cliente_segmento`

Boas práticas:

- Evitar partições com pouquíssimas linhas (particionamento exagerado)
- Equilibrar granularidade de partição com volume de dados e padrões de consulta

### 8.3 Otimização de Consultas

- Selecionar apenas as colunas necessárias
- Filtrar o máximo possível cedo (pushdown de filtros)
- Usar tabelas materializadas para consultas pesadas recorrentes
- Analisar planos de execução para encontrar *bottlenecks*

---

## 9. Engenharia de Features e Feature Stores

### 9.1 Desafios Clássicos

- **Reprodutibilidade**: conseguir recriar o dataset que gerou um determinado modelo
- **Data leakage**: usar, sem perceber, informação do futuro no treinamento
- **Consistência online/offline**: features calculadas de forma diferente em treinamento e em produção

### 9.2 Princípios de Boa Engenharia de Features

- Toda feature deve ter **definição clara** e estar documentada
- As transformações devem ser **centralizadas** (não copiadas em mil notebooks)
- Versão de features e datasets deve ser rastreável

### 9.3 Feature Stores

Um *feature store* é uma camada que:

- Armazena features **offline** (para treinamento em batch)
- Serve features **online** (para inferência em tempo real)
- Garante **consistência** entre os dois mundos
- Ajuda a evitar leakage com **point-in-time joins**

Exemplo conceitual de consulta de features point-in-time:

```sql
SELECT
  f.cliente_id,
  f.dias_desde_ultima_compra,
  f.ticket_medio_30d,
  l.label_churn
FROM
  features_cliente_point_in_time f
JOIN
  labels_churn l
ON
  f.cliente_id = l.cliente_id
  AND f.event_timestamp <= l.data_referencia
```

A regra `f.event_timestamp <= l.data_referencia` é crucial para não vazarmos informação do futuro.

---

## 10. MLOps e DataOps: onde Engenharia de Dados entra

### 10.1 Ciclo de Vida de Modelos

Um fluxo típico:

1. Ingestão e modelagem de dados
2. Criação de features
3. Treinamento de modelos
4. Validação, *deploy* e monitoramento
5. *Retraining* com dados mais recentes

A engenharia de dados é responsável, principalmente, pelos passos **1, 2 e parte do 5**.

### 10.2 Processos Importantes

- Pipelines de **treinamento automatizado** (jobs de re-treino com novas janelas de dados)
- Capacidade de fazer **backfill** de histórico para corrigir dados e re-treinar modelos
- Monitoramento de **drift de dados** em produção

### 10.3 Colaboração com MLOps

- Garantir que o ambiente de produção de modelos tenha acesso às mesmas **transformações de dados** usadas em treinamento
- Padronizar como datasets de treino são versionados (por exemplo, com carimbo de tempo e hash de conteúdo)

---

## 11. Arquiteturas em Nuvem e Data Mesh

### 11.1 Padrões em Nuvem

Independente do provedor, a arquitetura costuma ter blocos parecidos:

- Armazenamento de objetos (data lake)
- Warehouse/Lakehouse para analytics
- Ferramentas de orquestração
- Catálogo de dados
- Ferramentas de qualidade e monitoramento

### 11.2 Data Mesh (Visão Resumida)

Data Mesh é mais organização do que tecnologia. Ideias centrais:

- Dados como **produto**
- Times de **domínio** responsáveis pelos seus *data products*
- Plataforma de dados **self-serve** que oferece ferramentas comuns (ingestão, catálogo, governança)

Para o cientista de dados, isso significa:

- Acesso a dados mais próximos do domínio de negócio
- Necessidade de padrões de interoperabilidade entre domínios (IDs, métricas comuns, etc.)

---

## 12. Boas Práticas de Colaboração entre Engenharia de Dados e Ciência de Dados

### 12.1 Contratos de Dados

Estabelecer contratos claros:

- Quais tabelas são **oficiais** para cada métrica
- Frequência e horário de atualização
- Qual o SLA de correção em caso de falhas

### 12.2 Processos de Mudança de Esquema

- Evitar *breaking changes* (renomear/remover colunas sem aviso)
- Introduzir primeiro as novas colunas, comunicar, migrar o uso, depois descontinuar as antigas
- Versionar tabelas importantes (por ex.: `tabela_v1`, `tabela_v2` durante o período de migração)

### 12.3 Documentação e Exemplos

- Notebooks de exemplo de uso de tabelas principais
- Queries SQL que produzem as métricas-chave
- Seções "Como montar um dataset de treinamento para X" na documentação

---

## 13. Casos Práticos (Visão de Alto Nível)

### 13.1 Churn de Clientes

1. **Bronze**: eventos de compra, login, suporte do CRM
2. **Silver**: tabelas limpas de `clientes`, `transacoes`, `interacoes_suporte`
3. **Gold**:
   - Tabela de **features** de cliente com janelas temporais (30d, 90d)
   - Tabela de **labels** de churn (se o cliente ficou X dias sem comprar)
4. **Feature store**: registra features com `cliente_id` e `event_timestamp`
5. **Treinamento**: dataset montado com *point-in-time joins*
6. **Produção**: serviço de inferência que consome features online e gera scores de churn

### 13.2 Recomendação de Produtos

1. Eventos de navegação e compra em streaming
2. Enriquecimento com catálogo de produtos e perfil de cliente
3. Construção de features como:
   - Produtos mais vistos recentemente
   - Coocorrência de compras
   - Similaridade de itens
4. Armazenamento de embeddings ou vetores de similaridade
5. Sistemas online consultam o feature store e o índice de similaridade para recomendar em tempo real

---

## 14. Próximos Passos para se Aprofundar

Sugestão de trilhas de estudo:

1. **Modelagem de dados para analytics**
   - Modelagem dimensional
   - Data Vault (visão geral)
2. **Pipelines e orquestração**
   - Conceitos de DAGs, idempotência, backfill
3. **Lakehouse e formatos de tabela**
   - Arquitetura medallion, formatos colunares, particionamento
4. **Engenharia de features e feature stores**
   - Point-in-time joins
   - Consistência online/offline
5. **Qualidade e observabilidade de dados**
   - Testes de dados
   - Monitoramento de freshness e volumetria

Use este guia como um **mapa**: identifique quais áreas são mais críticas para o contexto da sua empresa e aprofunde nelas primeiro. Engenharia de dados madura é a base para modelos de machine learning robustos e decisões de negócio confiáveis.

---

## 15. Técnicas Avançadas e Tendências Recentes

Nesta seção, aprofundamos temas mais modernos e sofisticados que estão guiando times de engenharia de dados de ponta.

### 15.1 Lakehouse de próxima geração e formatos de tabela abertos

Os *open table formats* trouxeram uma nova geração de lakehouses:

- **Delta Lake**
- **Apache Iceberg**
- **Apache Hudi**

Principais capacidades avançadas:

- **Transações ACID** sobre arquivos em data lake (garantem consistência mesmo com muitos jobs concorrentes)
- **Time travel**: ler tabelas "como eram" em um ponto no tempo (útil para auditoria, reproduzir datasets e depurar modelos)
- **Evolução de esquema controlada**: adicionar/renomear colunas com governança
- **Partition evolution / hidden partitioning**: mudar a estratégia de particionamento para novos dados sem reescrever todo o histórico
- **Row/column-level delete & update**: suporte nativo a GDPR/privacidade e correções pontuais
- **Change data feed (CDF)** ou *incremental queries*: consumir apenas mudanças desde um *checkpoint*, essencial para pipelines incrementais e feature stores

Boas práticas:

- Definir claramente **catálogo de tabelas** (Glue, Hive Metastore, catálogo proprietário, etc.) e padrões de nomenclatura
- Reservar os formatos abertos para dados de **médio/alto valor analítico**; dados efêmeros podem continuar em formatos simples
- Padronizar **estratégia de partição + ordenação** (por exemplo, partição por data, *clustering* por IDs de negócio ou colunas muito filtradas)

### 15.2 Data Contracts e pipelines *schema-first*

**Data Contracts** formalizam o acordo entre produtores e consumidores de dados (estrutura, semântica, qualidade mínima e SLAs).

Elementos típicos de um contrato:

- Esquema (campos, tipos, obrigatoriedade)
- Regras de qualidade (campos que não podem ser nulos, faixas de valores, cardinalidade)
- Regras de versionamento (como evoluir o contrato sem quebrar consumidores)
- SLAs/SLOs de **freshness** e disponibilidade

Exemplo conceitual em YAML (simplificado):

```yaml
name: eventos_pedido
version: 1
owner: squad_comercial
schema:
  - name: pedido_id
    type: string
    required: true
  - name: valor_total
    type: decimal(18,2)
    required: true
    constraints:
      min: 0
  - name: status
    type: string
    required: true
    enum: [CRIADO, PAGO, CANCELADO]
quality:
  max_null_percent:
    valor_total: 0
sla:
  freshness_minutes: 5
```

Pontos avançados:

- Validar contratos **na borda** (produtor) – por exemplo, no microserviço que publica em Kafka
- Integrar contratos com o catálogo de dados e o orquestrador (jobs só rodam se as entradas estiverem compatíveis)
- Tratar mudanças de contrato como mudanças de API: *review*, depreciação, comunicação e migração gradual

### 15.3 Data Observability de próxima geração

Além de testes pontuais, times maduros tratam observabilidade de dados como SRE trata disponibilidade de sistemas.

Capacidades avançadas:

- **Monitoria contínua** de:
  - Volumetria (linhas por partição, por evento)
  - Freshness (atrasos vs. SLOs)
  - Distribuição estatística (média, variância, percentis, categorias mais frequentes)
- **Alertas inteligentes**: uso de modelos de anomalia em vez de apenas limiares estáticos
- **Linhagem ativa**: ao detectar problema em uma tabela upstream, já marcar tabelas downstream como potencialmente afetadas
- **Playbooks de incidentes de dados**: procedimento claro de triagem, mitigação, comunicação e *postmortem*

Boas práticas:

- Definir **SLOs de dados** (por exemplo: "95% dos *loads* diários da tabela `fato_vendas` concluídos até 07:00")
- Diferenciar problemas que exigem **bloquear consumo** (ex.: duplicidade grave em fatos) de problemas que apenas geram *warnings*
- Incorporar métricas de qualidade no processo de aprovação de novos *data products* e modelos

### 15.4 Camada de Métricas e Camada Semântica

Em ambientes com muitos consumidores (BI, produtos, modelos), uma **camada semântica/metrics layer** ajuda a garantir que todos falem a mesma língua.

Funções principais:

- Definir métricas em um único lugar (por exemplo, YAML ou código) com:
  - Fórmula (numerador, denominador)
  - Filtros padrão
  - Janela temporal
  - Dimensões por onde pode ser segmentada
- Expor essas métricas para diferentes ferramentas (dashboards, notebooks, experimentação, relatórios financeiros)
- Implementar governança: quem pode criar/alterar métricas, processo de aprovação e versionamento

Impacto para ciência de dados:

- Facilita a criação de **labels e features derivadas de métricas oficiais** (ex.: churn baseado na mesma definição de "cliente ativo" usada em finanças)
- Elimina discussão interminável de "qual número está certo" entre times

### 15.5 Arquiteturas modernas de Feature Store

Para casos avançados de ML (particularmente **real-time ML**), arquiteturas de feature store evoluíram em alguns padrões comuns:

1. **Dual-store (offline + online)**
   - *Offline store*: data lake/warehouse (BigQuery, Snowflake, lakehouse)
   - *Online store*: banco de baixa latência (Redis, DynamoDB, Cassandra/Scylla, etc.)
   - Camada de sincronização garante consistência entre os dois mundos

2. **Virtual / compute-on-read**
   - Features não são materializadas previamente em um "banco de features" central
   - São calculadas sob demanda a partir de tabelas fonte, com forte cache em camadas mais próximas do modelo
   - Boa opção quando o número de features é alto, mas o tráfego online é concentrado em poucas combinações

3. **Streaming-first**
   - Features são derivadas diretamente de fluxos de eventos (Flink, Spark Structured Streaming, Kafka Streams)
   - *Stateful operators* mantêm janelas deslizantes, contadores e agregados
   - Ideal para fraude, recomendação em tempo real e detecção de anomalias

Tópicos avançados:

- **TTL por feature** e metadados de freshness – impedir modelos de lerem valores "velhos demais"
- **Point-in-time correctness** como requisito formal (testes garantem que pipelines de features não usam dados do futuro)
- Features vetoriais (embeddings) servidas por **vector databases** integradas à plataforma (busca semântica, RAG, recomendação)

### 15.6 Streaming avançado: *stateful* e *exactly-once*

Quando saímos do batch e vamos para *event-driven*, alguns conceitos se tornam críticos:

- **Tempo de evento vs. tempo de processamento**: usar timestamps do evento para janelas corretas, independentemente de atrasos na entrega
- **Watermarks**: heurística para decidir quando uma janela está "completa o suficiente" para ser fechada
- **Processamento com estado (stateful)**: manter contadores, janelas, agregados em memória/armazenamento interno do engine de streaming
- **Semântica de entrega**:
  - *At-most-once*: pode perder eventos, mas nunca duplica
  - *At-least-once*: pode duplicar, mas não perde
  - *Exactly-once*: combina *checkpointing* + idempotência para evitar perdas e duplicatas

Padrões práticos:

- **Streaming ETL contínuo**: alimentar tabelas analíticas quase em tempo real com jobs de streaming que escrevem em formatos de lakehouse transacionais
- **Materialized views** em streaming: manter tabelas derivadas atualizadas a partir de tópicos de eventos (por exemplo, saldo de carteira, status atual de pedido)
- Integrar **CDC + streaming** para replicar bancos OLTP para o lakehouse com baixa latência, sem consultas pesadas

### 15.7 Privacidade, segurança e dados *AI-ready*

Com o uso crescente de IA (tradicional e generativa), a engenharia de dados precisa ir além de RBAC básico.

Tópicos avançados:

- **Classificação automática de dados sensíveis** (PII, PHI, segredos) usando regras + modelos de ML
- Técnicas de **pseudonimização e tokenização** para permitir análises sem expor identificadores reais
- Controles de acesso a nível de linha/coluna (row/column-level security) integrados ao catálogo e ao warehouse
- Trilhas de auditoria detalhadas (quem acessou quais dados, quando e por quê)
- Para pipelines de *Retrieval-Augmented Generation (RAG)*:
  - Limpar e anonimizar documentos antes de indexar em bases vetoriais
  - Propagar metadados de autorização até a camada de busca (o usuário só vê documentos para os quais tem permissão)

### 15.8 FinOps de Dados e eficiência de custo

Dados escalam rápido – e a conta também. FinOps de dados traz disciplina financeira para o stack analítico.

Práticas comuns:

- Atribuir custos de warehouse/lakehouse por **domínio, time ou produto** (tags, *billing projects*, *resource groups*)
- Definir *quotas* ou orçamentos para workloads mais pesadas (experimentos, *ad-hoc analytics*)
- Automatizar *auto-suspend*/*auto-resume* de clusters e warehouses
- Otimizar consultas repetitivas com:
  - Tabelas materializadas
  - *Result caching*
  - Segmentação de dados quentes vs. frios (camadas de armazenamento com custos diferentes)
- Revisar políticas de **retenção**: por quanto tempo dados detalhados realmente precisam ficar em armazenamento quente?

A ideia central é tratar o **custo de dados** como um primeiro cidadão do design de arquitetura, não como algo a ser olhado só quando a fatura explode.

---

Este capítulo não substitui os anteriores, mas os aprofunda para contextos em que a plataforma de dados precisa suportar múltiplos domínios, modelos em tempo real, IA generativa e demandas fortes de governança. Use-o como referência quando for dar o próximo salto de maturidade na sua engenharia de dados.

