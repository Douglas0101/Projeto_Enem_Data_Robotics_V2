# Guia orquestrado para agente / MCP em Ciência de Dados

> Objetivo: fornecer um roteiro profissional para um agente orquestrador (MCP / multi‑agente) conduzir projetos de ciência de dados, desde o problema de negócio até o deploy e monitoramento de modelos.

---

## Visão geral da orquestração

**Papel do agente / MCP**
- Centralizar o fluxo de trabalho, garantindo que nenhuma etapa crítica seja pulada.
- Converter objetivos de negócio em tarefas técnicas bem definidas.
- Coordenar outros agentes especializados (dados, modelagem, MLOps, documentação).
- Padronizar entregas: artefatos, relatórios, código e documentação.

**Macro‑fases do pipeline**
1. Contexto e definição de problema
2. Planejamento da solução e arquitetura de dados
3. Aquisição, qualidade e engenharia de dados
4. Exploração, hipóteses e baseline de modelos
5. Design de algoritmos e experimentação
6. Avaliação, validação e alinhamento com o negócio
7. Industrialização: APIs, pipelines e MLOps
8. Monitoramento, melhoria contínua e governança

Cada fase abaixo traz:
- Objetivo
- Entradas / Saídas
- Checklist profissional
- Tarefas para o agente / MCP (prompts de exemplo)

---

## 1. Contexto e definição de problema

**Objetivo**: transformar uma demanda vaga em um problema de negócio e de modelagem bem formulado.

**Entradas**
- Briefing de negócio
- Dados disponíveis (ainda de forma superficial)

**Saídas**
- Declaração do problema
- Objetivo de negócio + métrica de sucesso
- Escopo inicial (o que está dentro / fora)

**Checklist profissional**
- [ ] Stakeholders identificados
- [ ] Problema descrito em linguagem de negócio
- [ ] Hipótese de valor (por que esse projeto vale a pena?)
- [ ] Métricas de negócio (ex: receita, churn, NPS)
- [ ] Restrições (prazo, compliance, budget, dados sensíveis)

**Tarefas do agente / MCP**

```text
Tarefa: Estruturar o problema de negócio
Entradas: briefing bruto do usuário (texto livre, reunião, e‑mail)
Passos do agente:
1. Resumir o contexto em até 10 linhas.
2. Sugerir uma formulação de problema em linguagem de negócio.
3. Propor 1–3 objetivos mensuráveis e respectivas métricas.
4. Levantar perguntas que ainda precisam de resposta.
Output esperado: documento de definição de problema (1–2 páginas).
```

---

## 2. Planejamento da solução e arquitetura de dados

**Objetivo**: desenhar como o problema será resolvido: fontes de dados, fluxo de informação e visão de alto nível dos modelos.

**Entradas**
- Documento de definição de problema (fase 1)
- Lista preliminar de fontes de dados

**Saídas**
- Arquitetura lógica de dados (diagrama / descrição)
- Plano de coleta e acesso a dados
- Roadmap macro do projeto

**Checklist profissional**
- [ ] Fontes de dados mapeadas (internas / externas)
- [ ] Nível de granularidade e histórico disponível
- [ ] Riscos de qualidade de dados identificados
- [ ] Decisão inicial: batch vs near‑real‑time
- [ ] Definição de papéis (quem faz o quê)

**Tarefas do agente / MCP**

```text
Tarefa: Desenhar arquitetura lógica de dados
Entradas: problema definido + fontes de dados potenciais
Passos do agente:
1. Listar todas as fontes de dados relevantes.
2. Descrever como os dados fluem das fontes até os modelos.
3. Sugerir tecnologias genéricas (data lake, warehouse, orquestrador, etc.).
4. Produzir um texto que possa ser facilmente transformado em diagrama.
Output esperado: especificação textual de arquitetura (para virar diagrama em outra ferramenta).
```

```text
Tarefa: Criar roadmap macro do projeto de ciência de dados
Entradas: contexto, prazo, recursos disponíveis
Passos do agente:
1. Dividir o projeto nas 8 fases deste guia.
2. Sugerir duração aproximada de cada fase.
3. Destacar dependências críticas e riscos.
Output esperado: tabela de fases x entregas x duração.
```

---

## 3. Aquisição, qualidade e engenharia de dados

**Objetivo**: garantir dados utilizáveis, limpos e documentados.

**Entradas**
- Acesso às fontes de dados

**Saídas**
- Tabelas tratadas (bronze → silver → gold, dependendo da arquitetura)
- Regras de limpeza e transformação documentadas

**Checklist profissional**
- [ ] Especificar dicionário de dados (nome, tipo, descrição, domínio)
- [ ] Definir regras de tratamento de nulos e outliers
- [ ] Padronizar datas, categorias, identidades (IDs)
- [ ] Auditoria de dados sensíveis (PII, dados regulados)

**Tarefas do agente / MCP**

```text
Tarefa: Especificar regras de tratamento de dados
Entradas: amostra de dados (schema + linhas de exemplo)
Passos do agente:
1. Identificar tipos de variáveis (numéricas, categóricas, texto, datas).
2. Sugerir regras de limpeza por tipo (nulos, outliers, formatação).
3. Propor colunas derivadas úteis (features iniciais).
4. Gerar um "Data Quality Plan" estruturado.
Output esperado: plano de qualidade de dados (tabela ou markdown).
```

---

## 4. Exploração, hipóteses e baseline

**Objetivo**: entender o comportamento dos dados, levantar hipóteses e criar modelos simples de referência.

**Entradas**
- Dataset tratado (tabelas já limpas)

**Saídas**
- Relatório de exploração (EDA)
- Hipóteses de negócio e insights iniciais
- Baseline de modelo (simples, porém mensurável)

**Checklist profissional**
- [ ] Análise de distribuição das principais variáveis
- [ ] Correlações e relações chave
- [ ] Avaliação de viéses potenciais (amostra, tempo, região)
- [ ] Definição de baseline (modelo trivial ou simples)

**Tarefas do agente / MCP**

```text
Tarefa: Orquestrar relatório de EDA
Entradas: descrição do dataset (schema, amostra) + objetivo do modelo
Passos do agente:
1. Gerar um plano de EDA (itens a analisar, gráficos, tabelas).
2. Pedir a execução dos códigos necessários a um agente de código ou humano.
3. Consumir os resultados (estatísticas, gráficos descritos) e produzir texto interpretativo.
4. Destacar riscos e oportunidades descobertas.
Output esperado: relatório de EDA estruturado (seções: contexto, dados, achados, hipóteses).
```

```text
Tarefa: Definir baseline de modelo
Entradas: tipo de problema (classificação, regressão, ranking etc.) + métricas de negócio
Passos do agente:
1. Sugerir 1–2 modelos extremamente simples (ex: média, regressão linear, árvore rasa).
2. Definir claramente o protocolo de avaliação (split, validação cruzada, métricas).
3. Gerar um checklist de experimentos mínimos.
Output esperado: especificação do baseline pronta para implementação.
```

---

## 5. Design de algoritmos e experimentação

**Objetivo**: desenhar a estratégia de modelagem, escolher algoritmos, features e plano de experimentos.

**Entradas**
- Relatório de EDA
- Baseline estabelecido

**Saídas**
- Especificação clara dos modelos a testar
- Plano de experimentos (matriz de experimentos)

**Checklist profissional**
- [ ] Tipo de problema e formato de saída bem definido
- [ ] Conjunto de algoritmos candidatos (clássicos, gradient boosting, deep learning, etc.)
- [ ] Estratégia de features (handcrafted, embeddings, agregações temporais)
- [ ] Estratégia de validação (time‑series split, k‑fold, nested CV)
- [ ] Critério de seleção do modelo final

**Tarefas do agente / MCP**

```text
Tarefa: Especificar estratégia de modelagem
Entradas: EDA + objetivo de negócio + restrições (latência, interpretabilidade)
Passos do agente:
1. Selecionar 3–5 algoritmos adequados às restrições.
2. Justificar por que cada algoritmo faz sentido.
3. Definir um conjunto inicial de features obrigatórias e opcionais.
4. Propor abordagem de regularização e controle de overfitting.
Output esperado: documento "Estratégia de Modelagem".
```

```text
Tarefa: Criar plano de experimentos
Entradas: lista de modelos, espaço de hiperparâmetros, recursos computacionais
Passos do agente:
1. Definir quais combinações serão testadas (grade, random, Bayesian etc.).
2. Estimar custo computacional por experimento.
3. Priorizar experimentos de maior impacto esperado.
4. Gerar uma tabela Experimento x Modelo x Hiperparâmetros x Métricas.
Output esperado: plano de experimentos versionável (CSV/markdown).
```

---

## 6. Avaliação, validação e alinhamento com o negócio

**Objetivo**: avaliar os modelos de forma técnica e de negócio, e garantir que o resultado é confiável e útil.

**Entradas**
- Resultados dos experimentos (métricas, gráficos, logs)

**Saídas**
- Comparação estruturada entre modelos
- Escolha do modelo candidato a produção
- Avaliação de impacto de negócio esperado

**Checklist profissional**
- [ ] Métricas técnicas consolidadas (média, desvio, intervalos de confiança)
- [ ] Avaliação por segmento (ex: tipo de cliente, região, faixa de valor)
- [ ] Análise de fairness / viés onde aplicável
- [ ] Trade‑offs claros (performance vs interpretabilidade vs custo)

**Tarefas do agente / MCP**

```text
Tarefa: Consolidar resultados de experimentos
Entradas: tabela de resultados (experimento x métricas)
Passos do agente:
1. Ordenar experimentos por métrica principal.
2. Destacar os 3 melhores modelos.
3. Gerar uma análise textual curta para cada um (prós e contras).
4. Sugerir um modelo candidato a produção com justificativa.
Output esperado: relatório de avaliação de modelos.
```

```text
Tarefa: Traduzir performance técnica em impacto de negócio
Entradas: métrica técnica (ex: AUC, MAE) + informações de contexto de negócio
Passos do agente:
1. Mapear como a métrica técnica afeta indicadores de negócio.
2. Estimar ganhos aproximados (ex: redução de churn, aumento de receita).
3. Produzir um sumário executivo para stakeholders não técnicos.
Output esperado: seção de "Impacto de Negócio" no relatório.
```

---

## 7. Industrialização: APIs, pipelines e MLOps

**Objetivo**: transformar o modelo escolhido em um serviço robusto, rastreável e de fácil manutenção.

**Entradas**
- Modelo final + código de treinamento
- Requisitos de integração (sistemas consumidores)

**Saídas**
- Especificação de API / batch
- Pipeline de treinamento & scoring (conceitual)
- Plano de MLOps (monitoramento, re‑treino, versionamento)

**Checklist profissional**
- [ ] Definição de contrato de entrada/saída da API
- [ ] Estratégia de versionamento de modelo e dados
- [ ] Logs estruturados de previsões
- [ ] Plano de rollback em caso de problema

**Tarefas do agente / MCP**

```text
Tarefa: Especificar contrato de serviço do modelo
Entradas: modelo escolhido + caso de uso (online / batch)
Passos do agente:
1. Listar campos obrigatórios e opcionais da requisição.
2. Descrever o formato de resposta.
3. Definir códigos de erro e mensagens padrão.
4. Sugerir boas práticas de segurança (rate limit, autenticação genérica).
Output esperado: especificação de API em markdown ou pseudo‑OpenAPI.
```

```text
Tarefa: Desenhar pipeline de MLOps conceitual
Entradas: frequência de re‑treino, janelas de dados, requisitos de monitoramento
Passos do agente:
1. Descrever passos: ingestão → feature store → treino → validação → deploy → monitoramento.
2. Explicitar gatilhos de re‑treino.
3. Definir quais métricas serão monitoradas em produção (técnicas e de negócio).
4. Gerar um diagrama textual que possa ser transformado em diagrama visual.
Output esperado: documento de arquitetura MLOps.
```

---

## 8. Monitoramento, melhoria contínua e governança

**Objetivo**: garantir que o modelo se mantenha saudável, ético e gerando valor no tempo.

**Entradas**
- Logs de previsões e métricas de produção
- Feedback de usuários / negócio

**Saídas**
- Painel conceitual de monitoramento
- Processo de revisão periódica do modelo

**Checklist profissional**
- [ ] Métricas de drift de dados e de performance definidas
- [ ] Rotina de auditoria de vieses
- [ ] Procedimento de abertura de incidentes (SEVs)
- [ ] Processo de comunicação de mudanças (versões de modelo)

**Tarefas do agente / MCP**

```text
Tarefa: Definir plano de monitoramento de modelo
Entradas: características do modelo, volume de requisições, criticidade do uso
Passos do agente:
1. Sugerir métricas de dados (distribuição, missing, drift).
2. Sugerir métricas de performance (por segmento, no tempo).
3. Propor thresholds e alertas.
4. Especificar uma rotina de revisão (semanal/mensal) com perguntas‑guia.
Output esperado: "Runbook de Monitoramento".
```

---

## 9. Governança, documentação e reprodutibilidade

**Objetivo**: assegurar que o projeto possa ser entendido, auditado e replicado.

**Entradas**
- Artefatos produzidos em todas as fases anteriores

**Saídas**
- Documentação de projeto de ciência de dados
- Registro de decisões chave

**Checklist profissional**
- [ ] Documentação de dados (dicionário, fontes, transformações)
- [ ] Documentação de modelos (algoritmos, hiperparâmetros, datasets)
- [ ] Histórico de experimentos
- [ ] Registro de decisões de negócio e trade‑offs

**Tarefas do agente / MCP**

```text
Tarefa: Consolidar documentação final do projeto
Entradas: notas de cada fase, specs de dados, modelos e APIs
Passos do agente:
1. Organizar a documentação em seções padrão (Contexto, Dados, Modelos, Deploy, Monitoramento).
2. Gerar índices e resumos por público (técnico x executivo).
3. Apontar lacunas documentais e sugerir ações para preenchê‑las.
Output esperado: esqueleto completo de documentação do projeto.
```

---

## 10. Template de orquestração reutilizável

O agente / MCP pode encapsular todo este guia em um **template de projeto**, com:

- Perguntas iniciais obrigatórias (checklist de discovery).
- Estrutura padrão de pastas e artefatos:
  - `/00_contexto` – definição de problema, stakeholders, métricas.
  - `/10_dados` – dicionário, plano de qualidade, scripts de ingestão.
  - `/20_modelagem` – EDA, estratégia de modelagem, experimentos.
  - `/30_producao` – specs de API, pipelines, MLOps.
  - `/40_monitoramento` – runbooks, alertas, relatórios periódicos.
  - `/99_docs` – documentação consolidada, apresentações, decisões.

O fluxo orquestrado é então:
1. Criar instância de projeto usando o template.
2. Guiar o usuário/ time por cada fase usando as tarefas sugeridas.
3. Coletar respostas, decisões e resultados e armazenar nos artefatos corretos.
4. No final, gerar automaticamente um **relatório executivo** e uma **documentação técnica completa**.

Esse passo a passo fornece a estrutura profissional; a implementação (código, pipelines, dashboards) pode ser delegada a agentes especializados ou a desenvolvedores humanos, sempre coordenados pelo agente / MCP orquestrador.


---

## 11. Conjunto de prompts prontos para MCP / agente orquestrador

Abaixo está um conjunto de prompts reutilizáveis que você pode usar em um agente orquestrador/MCP. Substitua os campos entre chaves `{{...}}` pelo conteúdo específico do seu projeto.

---

### 11.1 Prompt mestre de orquestração (para o agente principal)

```text
Você é um agente orquestrador de projetos de Ciência de Dados em ambiente corporativo.

Sua missão é:
- Garantir que todas as fases do projeto sejam seguidas:
  1) Contexto e definição de problema
  2) Planejamento da solução e arquitetura de dados
  3) Aquisição, qualidade e engenharia de dados
  4) Exploração, hipóteses e baseline
  5) Design de algoritmos e experimentação
  6) Avaliação, validação e alinhamento com o negócio
  7) Industrialização: APIs, pipelines e MLOps
  8) Monitoramento, melhoria contínua e governança
  9) Governança, documentação e reprodutibilidade
- Converter entrada de negócio em tarefas técnicas claras.
- Coordenar agentes especializados (dados, código, MLOps, documentação).
- Gerar artefatos padronizados em texto (documentos, especificações, checklists).

Quando receber uma nova demanda, você deve:
1. Identificar em qual fase do pipeline o trabalho está.
2. Rodar o(s) prompt(s) específicos dessa fase, coletando as respostas necessárias.
3. Atualizar uma visão consolidada do projeto (resumo executivo + visão técnica).
4. Sinalizar riscos, dúvidas abertas e próximos passos.

Saída padrão:
- Fase atual
- Objetivo da fase
- Perguntas para o usuário/time
- Propostas de artefatos a gerar
- Lista de próximos passos numerados
```

---

### 11.2 Kickoff / Definição do problema

```text
[Prompt – Kickoff / Definição do problema]

Quero iniciar um projeto de ciência de dados.
Use as informações abaixo para estruturar o problema de negócio e de modelagem.

Contexto do negócio:
{{contexto_do_negocio}}

Stakeholders principais (se conhecidos):
{{stakeholders}}

Restrições (prazo, budget, compliance, etc.):
{{restricoes}}

Sua tarefa:
1. Resumir o contexto em até 10 linhas.
2. Formular o problema em linguagem de negócio.
3. Propor 1–3 objetivos mensuráveis e respectivas métricas.
4. Listar o que está dentro e fora do escopo.
5. Sugerir perguntas que ainda precisam ser respondidas.

Formate a saída em seções:
- Contexto resumido
- Declaração do problema
- Objetivos e métricas de sucesso
- Escopo (dentro / fora)
- Perguntas em aberto
```

---

### 11.3 Planejamento da solução e arquitetura de dados

```text
[Prompt – Planejamento / Arquitetura de Dados]

Temos o seguinte problema e contexto:
{{resumo_problema}}

Fontes de dados conhecidas (nome + descrição breve):
{{fontes_de_dados}}

Restrições técnicas (se houver):
{{restricoes_tecnicas}}

Sua tarefa:
1. Listar todas as fontes de dados relevantes para o problema.
2. Descrever como os dados devem fluir das fontes até os modelos.
3. Sugerir, em nível conceitual, os componentes de dados (ex: data lake, warehouse, orquestrador, feature store).
4. Produzir uma descrição textual que possa ser facilmente transformada em diagrama.
5. Criar um roadmap macro de fases com entregas.

Formate a saída em seções:
- Fontes de dados mapeadas
- Arquitetura lógica de dados (texto)
- Decisões principais (batch vs near-real-time, granularidade, etc.)
- Roadmap macro (tabela: Fase | Entrega principal | Duração estimada)
```

---

### 11.4 Aquisição, qualidade e engenharia de dados

```text
[Prompt – Plano de Qualidade e Engenharia de Dados]

Temos o seguinte schema e exemplos de dados:
{{schema_e_amostras}}

Objetivo de modelagem:
{{objetivo_modelagem}}

Sua tarefa:
1. Identificar tipos de variáveis (numéricas, categóricas, texto, datas, IDs).
2. Sugerir regras de limpeza por tipo (tratamento de nulos, outliers, padronizações).
3. Propor colunas derivadas (features iniciais) relevantes para o objetivo.
4. Organizar tudo em um "Data Quality Plan" estruturado.

Formate a saída como uma tabela em texto com colunas:
- Variável
- Tipo
- Problemas potenciais
- Regra de tratamento
- Features derivadas (se aplicável)
```

---

### 11.5 Exploração de dados (EDA) e hipóteses

```text
[Prompt – Plano de EDA]

Dataset disponível (descrição):
{{descricao_dataset}}

Objetivo do modelo:
{{objetivo_modelo}}

Sua tarefa:
1. Montar um plano de EDA com itens a analisar (estatísticas, correlações, séries temporais, segmentações, etc.).
2. Sugerir tipos de gráficos e tabelas a gerar.
3. Indicar quais análises são obrigatórias e quais são opcionais.
4. Definir perguntas de negócio que a EDA deve tentar responder.

Formate a saída em seções:
- Plano de EDA (lista numerada de análises)
- Sugestões de gráficos/tabelas
- Perguntas de negócio a investigar

Depois que os resultados da EDA estiverem disponíveis (estatísticas, descrições de gráficos), gere um segundo output:
- Achados principais
- Hipóteses levantadas
- Riscos e limitações observadas
```

---

### 11.6 Baseline de modelo

```text
[Prompt – Definição de Baseline]

Tipo de problema (classificação, regressão, etc.):
{{tipo_problema}}

Métricas de negócio prioritárias:
{{metricas_negocio}}

Restrições (latência, interpretabilidade, infra, etc.):
{{restricoes_modelo}}

Sua tarefa:
1. Sugerir 1–2 modelos baseline extremamente simples (ex: média, maioria, regressão linear, árvore rasa).
2. Definir o protocolo de avaliação (train/test split, validação cruzada, métricas técnicas).
3. Propor um checklist mínimo de experimentos com o baseline.

Formate a saída em seções:
- Modelos baseline sugeridos
- Protocolo de avaliação
- Checklist de experimentos mínimos
```

---

### 11.7 Estratégia de modelagem

```text
[Prompt – Estratégia de Modelagem]

Resumo da EDA e do baseline:
{{resumo_eda_baseline}}

Objetivo de negócio e restrições:
{{objetivo_e_restricoes}}

Sua tarefa:
1. Sugerir 3–5 algoritmos candidatos adequados (ex: regressão regularizada, gradient boosting, redes neurais, etc.).
2. Justificar a escolha de cada algoritmo em função do contexto.
3. Definir um conjunto inicial de features obrigatórias e opcionais.
4. Propor estratégias de regularização e controle de overfitting.
5. Definir a estratégia de validação (k-fold, time-series split, etc.).

Formate a saída em seções:
- Algoritmos candidatos e justificativas
- Estratégia de features
- Estratégia de validação
- Riscos e trade-offs
```

---

### 11.8 Plano de experimentos

```text
[Prompt – Plano de Experimentos]

Modelos candidatos:
{{modelos_candidatos}}

Espaço de hiperparâmetros (nível alto):
{{espaco_hiperparametros}}

Recursos computacionais disponíveis:
{{recursos_computacionais}}

Sua tarefa:
1. Definir quais combinações de modelo + hiperparâmetros serão testadas (grid, random, Bayesian etc.).
2. Estimar o custo computacional relativo de cada experimento.
3. Priorizar os experimentos com maior potencial de ganho.
4. Produzir uma tabela (em texto) Experimento x Modelo x Hiperparâmetros x Métrica principal x Prioridade.

Formate a saída como tabela em markdown.
```

---

### 11.9 Avaliação de modelos e alinhamento com o negócio

```text
[Prompt – Consolidação de Resultados de Modelos]

Tabela de resultados (experimento x métricas):
{{tabela_resultados}}

Segmentações relevantes (ex: tipo de cliente, região, faixa de valor):
{{segmentacoes}}

Sua tarefa:
1. Ordenar os experimentos por métrica principal.
2. Destacar os 3 melhores modelos.
3. Descrever prós e contras de cada um.
4. Sugerir um modelo candidato a produção, com justificativa técnica.
5. Apontar riscos, limitações e possíveis melhorias.

Formate a saída em seções:
- Ranking de modelos
- Análise dos top 3
- Modelo recomendado
- Riscos e próximos passos
```

```text
[Prompt – Tradução de Performance Técnica em Impacto de Negócio]

Métricas técnicas dos modelos (ex: AUC, MAE, F1):
{{metricas_tecnicas}}

Contexto de negócio (como a previsão será usada):
{{contexto_negocio}}

Sua tarefa:
1. Explicar, em linguagem de negócio, o que significam as métricas técnicas.
2. Conectar variações nessas métricas a impactos nos indicadores de negócio (ex: receita, churn, risco).
3. Estimar, mesmo que de forma aproximada, ganhos ou perdas associados ao uso do modelo recomendado.
4. Produzir um sumário executivo de 5–10 linhas para stakeholders não técnicos.
```

---

### 11.10 Industrialização: especificação de API e MLOps

```text
[Prompt – Especificação de API do Modelo]

Modelo escolhido e suas entradas/saídas principais:
{{modelo_escolhido}}

Tipo de uso (online/batch) e sistemas consumidores:
{{sistemas_consumidores}}

Sua tarefa:
1. Definir o contrato de requisição (campos obrigatórios e opcionais, tipos e validações).
2. Definir o formato da resposta (campos, tipos, interpretações).
3. Sugerir códigos de erro e mensagens padrão.
4. Propor boas práticas genéricas de segurança (autenticação, rate limit).

Formate a saída em um pseudo-OpenAPI em texto.
```

```text
[Prompt – Arquitetura Conceitual de MLOps]

Frequência de re-treino desejada:
{{frequencia_retreino}}

Volume de dados e criticidade do uso:
{{volume_criticidade}}

Sua tarefa:
1. Descrever o pipeline completo: ingestão → preparação → feature store (se aplicável) → treino → validação → deploy → monitoramento.
2. Explicitar gatilhos para re-treino (tempo, drift de dados, queda de performance).
3. Definir quais métricas técnicas e de negócio serão monitoradas em produção.
4. Sugerir uma estratégia de versionamento de modelo e rollback.

Formate a saída em seções:
- Fluxo de alto nível
- Gatilhos de re-treino
- Métricas monitoradas
- Estratégia de versionamento/rollback
```

---

### 11.11 Monitoramento e governança em produção

```text
[Prompt – Plano de Monitoramento de Modelo]

Descrição do modelo em produção e seu uso:
{{descricao_modelo_producao}}

Volume de requisições e criticidade:
{{volume_criticidade}}

Sua tarefa:
1. Sugerir métricas de dados a monitorar (distribuições, missing, drift, mudança de mix de segmentos).
2. Definir métricas de performance do modelo ao longo do tempo (por segmento, janelas móveis).
3. Propor thresholds e alertas iniciais.
4. Descrever uma rotina de revisão periódica (semanal/mensal) com perguntas-guia.

Formate a saída em seções:
- Métricas de dados
- Métricas de performance
- Alertas e thresholds
- Rotina de revisão (checklist)
```

---

### 11.12 Documentação final e reprodutibilidade

```text
[Prompt – Consolidação de Documentação do Projeto]

Artefatos disponíveis (resumos, EDA, specs de modelo, API, MLOps etc.):
{{lista_artefatos}}

Sua tarefa:
1. Organizar a documentação sugerindo uma estrutura de pastas e seções padrão:
   - Contexto e Problema
   - Dados
   - Modelos e Experimentos
   - Deploy e MLOps
   - Monitoramento e Governança
2. Gerar um índice comentado (o que se encontra em cada seção/pasta).
3. Sugerir textos curtos de introdução para cada seção.
4. Listar lacunas documentais e sugerir ações para preenchê-las.

Formate a saída como:
- Estrutura de pastas/seções
- Índice comentado
- Textos introdutórios
- Lacunas e ações sugeridas
```

---

### 11.13 Template rápido de criação de projeto

```text
[Prompt – Criar Template de Projeto de Ciência de Dados]

Quero criar um novo projeto de ciência de dados com estas características:

Contexto do negócio:
{{contexto_do_negocio}}

Tipo de problema (se já souber):
{{tipo_problema}}

Restrições gerais:
{{restricoes_gerais}}

Sua tarefa:
1. Instanciar uma estrutura de projeto baseada nas pastas:
   - /00_contexto
   - /10_dados
   - /20_modelagem
   - /30_producao
   - /40_monitoramento
   - /99_docs
2. Para cada pasta, listar os arquivos/documentos que devem existir e um breve propósito.
3. Listar as perguntas iniciais obrigatórias que precisam ser respondidas para começar o projeto.
4. Sugerir uma lista de próximos passos para a primeira semana de trabalho.

Formate a saída em seções claras e numeradas.
```

