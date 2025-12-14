# Plano de Engenharia e Qualidade

__Funcionalidade:__ Quantificação de alunos por média nas 5 disciplinas, com filtro por UF  
__Projeto:__ ENEM Data Robotics v2  
__Responsável técnico:__ _[preencher]_  
__Data:__ 2025-12-11  
__Versão:__ 2.0 – Atualizado com requisitos de Segurança, Performance e UI/UX

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Escopo](#2-escopo)
3. [Requisitos de Negócio](#3-requisitos-de-negócio)
4. [Regras de Negócio Detalhadas](#4-regras-de-negócio-detalhadas)
5. [Requisitos Funcionais](#5-requisitos-funcionais-rf)
6. [Requisitos Não Funcionais](#6-requisitos-não-funcionais-rnf)
7. [Arquitetura e Desenho Técnico](#7-arquitetura-e-desenho-técnico)
8. [🔒 Segurança e Conformidade LGPD](#8-segurança-e-conformidade-lgpd)
9. [⚡ Performance e Latência](#9-performance-e-latência)
10. [🎨 Experiência UI/UX](#10-experiência-uiux)
11. [Observabilidade e Monitoramento](#11-observabilidade-monitoramento-e-logging)
12. [Plano de Testes e Qualidade](#12-plano-de-testes-e-qualidade)
13. [Riscos, Premissas e Dependências](#13-riscos-premissas-e-dependências)
14. [Plano de Implantação](#14-plano-de-implantação)
15. [Checklist de Entrega](#15-checklist-de-entrega)

---

## 1. Visão Geral

### 1.1 Contexto

O projeto **ENEM Data Robotics v2** organiza e processa microdados do ENEM para análises educacionais. Hoje já temos dados por aluno e por disciplina, porém não existe ainda uma visão consolidada de:

> **Quantidade de alunos por faixa de média nas 5 disciplinas do ENEM, segmentada por Estado (UF).**

Essa visão é essencial para:

- Comparar desempenho médio entre estados;
- Analisar distribuição de resultados por região;
- Apoiar decisões de políticas educacionais e estratégias de escolas/cursinhos.

### 1.2 Objetivo da funcionalidade

Implementar uma solução que:

1. Calcule a **média das 5 disciplinas** para cada aluno;
2. Classifique cada aluno em **faixas de média configuráveis**;
3. **Agregue e contabilize** alunos por UF e faixa de média;
4. Disponibilize essa visão de forma **consultável** com **filtro por UF** e ano;
5. **🔒 Garanta segurança** contra injeção SQL e exposição de dados sensíveis;
6. **⚡ Mantenha latência baixa** (<500ms P95) para consultas em produção;
7. **🎨 Ofereça experiência visual premium** com gráficos interativos e responsivos.

---

## 2. Escopo

### 2.1 Escopo incluído

- Cálculo da coluna `media_5_disc` para cada aluno;
- Definição e configuração de faixas de média (ex.: 0–400, 400–600, 600–800, 800–1000);
- Classificação dos alunos em faixas de média;
- Agregação por Ano, UF e Faixa de média;
- Criação de tabela/dataset agregado para consumo analítico;
- **Novo endpoint `/v1/dados/media-uf`** na API FastAPI com validação Pydantic;
- **Componente React de visualização** (BarChart + filtros interativos);
- Implementação de testes (unitários, integração, E2E, dados);
- Logging, métricas e observabilidade;
- Documentação técnica da solução.

### 2.2 Fora de escopo (por agora)

- Pesos diferenciados por disciplina;
- Modelos preditivos utilizando essas médias;
- Ajustes metodológicos entre diferentes edições do ENEM;
- Segmentações muito específicas (ex.: curso pretendido, TRI detalhada).

---

## 3. Requisitos de Negócio

- Permitir a visualização da **distribuição de alunos por faixas de média**, por Estado;
- Permitir comparação simples entre estados (ex.: top 5 estados em determinada faixa);
- Possibilitar recortes por **ano** e, se disponível, por tipo de escola (pública/privada);
- Garantir transparência nas regras:
   - Como a média foi calculada;
   - O que acontece quando falta nota;
   - Quais faixas foram utilizadas.

---

## 4. Regras de Negócio Detalhadas

### 4.1 Cálculo da média

Disciplinas consideradas:

- Linguagens, Códigos e suas Tecnologias
- Matemática e suas Tecnologias
- Ciências Humanas
- Ciências da Natureza
- Redação

**Fórmula:**

```text
media_5_disc = (nota_ling + nota_mat + nota_ch + nota_cn + nota_red) / 5
```

- Casas decimais: **2** (ex.: 643,27);
- Campo sugerido: `media_5_disc` (FLOAT/DECIMAL).

#### Tratamento de ausências/inconsistências

- Se qualquer uma das 5 notas estiver **nula** ou marcada como ausente:
   - **Regra padrão:** o aluno é **excluído** do cálculo da média;
   - Criar campo `flag_dados_incompletos` para rastrear esses casos;

- Notas literalmente "0" precisam ser validadas conforme regra do ENEM (0 válido x ausência).

### 4.2 Faixas de média

Faixas padrão (parametrizáveis via `config/faixas_media.yaml`):

| Faixa | Intervalo | Descrição |
|-------|-----------|-----------|
| 1 | [0, 400) | Abaixo de 400 |
| 2 | [400, 600) | Intermediário baixo |
| 3 | [600, 800) | Intermediário alto |
| 4 | [800, 1000] | Alto desempenho |

### 4.3 Estado (UF)

- Agregação por campo `uf` do aluno;
- Caso `uf` esteja nula:
   - Alocar em categoria `UF_DESCONHECIDA`;
   - Logar quantidade para auditoria.

### 4.4 Filtros

Filtros prioritários:

- UF (obrigatório);
- Ano do ENEM;
- Tipo de escola (pública/privada) – se disponível.

---

## 5. Requisitos Funcionais (RF)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| __RF-01__ | Calcular a média das 5 disciplinas por aluno e persistir em `media_5_disc` | Alta |
| __RF-02__ | Classificar cada aluno em uma faixa de média conforme configuração ativa | Alta |
| __RF-03__ | Gerar tabela agregada `agg_media5_por_uf` com contagem por Ano/UF/Faixa | Alta |
| __RF-04__ | Disponibilizar endpoint `/v1/dados/media-uf` com filtros por UF e ano | Alta |
| __RF-05__ | Implementar componente React `MediaUfBarChart` para visualização interativa | Alta |
| __RF-06__ | Registrar logs de execução (volumes processados, descartados, tempos) | Média |
| __RF-07__ | Manter histórico por ano (não sobrescrever dados anteriores) | Média |
| __RF-08__ | Garantir compatibilidade com a pipeline atual | Alta |

---

## 6. Requisitos Não Funcionais (RNF)

### 6.1 Performance

| ID | Requisito | Meta |
|----|-----------|------|
| **RNF-01** | Latência do endpoint P50 | < 200ms |
| **RNF-02** | Latência do endpoint P95 | < 500ms |
| **RNF-03** | Tempo do pipeline de agregação (batch) | < 5 minutos para todos os anos |
| **RNF-04** | Bundle size do componente React | < 50KB gzipped (lazy loaded) |

### 6.2 Escalabilidade

| ID | Requisito |
|----|-----------|
| **RNF-05** | Suportar múltiplos anos do ENEM sem alteração de código |
| **RNF-06** | Suportar consultas concorrentes (100 req/s) |

### 6.3 Confiabilidade

| ID | Requisito |
|----|-----------|
| **RNF-07** | Em caso de erro, a execução falha de forma explícita |
| **RNF-08** | Não gerar tabelas partialmente inconsistentes (transações atômicas) |

### 6.4 Observabilidade

| ID | Requisito |
|----|-----------|
| **RNF-09** | Logs estruturados (JSON) em nível info + error |
| **RNF-10** | Métricas: alunos processados, descartados, por UF, por faixa |
| **RNF-11** | Tracing de requests na API (OpenTelemetry ready) |

### 6.5 Manutenibilidade

| ID | Requisito |
|----|-----------|
| **RNF-12** | Faixas de média definidas via arquivo YAML |
| **RNF-13** | Disciplinas configuráveis (não hard-coded) |
| **RNF-14** | Código coberto por testes (>80% cobertura) |

---

## 7. Arquitetura e Desenho Técnico

### 7.1 Visão Geral da Arquitetura

```mermaid
graph TB
    subgraph "Data Layer (Lakehouse)"
        RAW["00_raw/MICRODADOS*"]
        SILVER["01_silver/*.parquet"]
        GOLD["02_gold/DuckDB"]
    end
    
    subgraph "Backend (FastAPI)"
        API["api/dashboard_router.py"]
        AGENT["infra/db_agent.py"]
        SEC["infra/security.py"]
    end
    
    subgraph "Frontend (React)"
        DASH["pages/Dashboard"]
        CHART["components/MediaUfBarChart"]
        CTX["context/FilterContext"]
    end
    
    RAW --> SILVER
    SILVER --> GOLD
    GOLD --> AGENT
    AGENT --> SEC
    SEC --> API
    API --> DASH
    DASH --> CHART
    CTX --> CHART
```

### 7.2 Fontes de Dados

Tabela base: `vw_notas_enem` (view sobre Silver)

Campos mínimos esperados:

- `id_aluno`
- `ano_enem`
- `uf`
- `nota_linguagens`
- `nota_matematica`
- `nota_ch`
- `nota_cn`
- `nota_redacao`

### 7.3 Transformações

1. **Cálculo da média**

   - Módulo: `enem_project.data.gold.media_uf_pipeline`
   - Função: `calcular_media_5_disc(df: pl.DataFrame) -> pl.DataFrame`
   - Utiliza Polars para processamento vetorizado eficiente

2. **Classificação em faixas**

   - Configuração: `config/faixas_media.yaml`
   - Função: `classificar_faixa_media(media: float) -> int`

3. **Agregação**

- Dataset final: `agg_media5_por_uf` (Parquet na Gold)

- Schema:

```yaml
ano_enem: INT32
uf: STRING
id_faixa: INT8
descricao_faixa: STRING
qtd_alunos: INT64
dt_processamento: TIMESTAMP
```

### 7.4 API Endpoint

```python
# api/dashboard_router.py

@router.get("/v1/dados/media-uf", response_model=MediaUfResponse)
@limiter.limit("60/minute")
async def get_media_por_uf(
    ano: int = Query(..., ge=1998, le=2024),
    uf: str | None = Query(None, regex="^[A-Z]{2}$"),
    current_user: User = Depends(get_current_user)
) -> MediaUfResponse:
    """
    Retorna distribuição de alunos por faixa de média, filtrado por UF.
    """
```

---

## 8. 🔒 Segurança e Conformidade LGPD

> [!IMPORTANT]
> Este módulo manipula dados agregados (não PII direto), mas as práticas de segurança devem ser mantidas para consistência com o restante do sistema.

### 8.1 Controles Implementados

| Controle | Implementação | Referência |
|----------|---------------|------------|
| __Autenticação__ | JWT Bearer token obrigatório | `api/dependencies.py` |
| __Rate Limiting__ | 60 req/min por IP | `api/limiter.py` (SlowAPI) |
| __SQL Injection Prevention__ | Queries parametrizadas + guardrails | `infra/db_agent.py:_enforce_guardrails` |
| __Data Masking__ | DDM para dados sensíveis (se expostos) | `infra/security.py:SecurityEngine` |

### 8.2 Boas Práticas Aplicadas

```python
# ❌ NUNCA fazer (SQL Injection vulnerável)
sql = f"SELECT * FROM agg_media5_por_uf WHERE uf = '{uf}'"

# ✅ CORRETO (Parametrizado)
sql = "SELECT * FROM agg_media5_por_uf WHERE uf = ?"
agent.run_query(sql, params=[uf])
```

### 8.3 Validação de Input (Pydantic)

```python
# api/schemas.py
class MediaUfRequest(BaseModel):
    ano: int = Field(..., ge=1998, le=2024, description="Ano do ENEM")
    uf: str | None = Field(
        None, 
        pattern=r"^[A-Z]{2}$", 
        description="Sigla do estado (ex: SP, RJ)"
    )

    @field_validator("uf")
    @classmethod
    def validate_uf(cls, v: str | None) -> str | None:
        if v and v not in VALID_UFS:
            raise ValueError(f"UF inválida: {v}")
        return v
```

### 8.4 Isolamento de Recursos (DuckDB)

```python
# DuckDBAgent always uses read_only=True for API queries
agent = DuckDBAgent(db_path=gold_db, read_only=True)

# Resource limits via PRAGMAs
conn.execute("SET memory_limit='2GB'")
conn.execute("SET threads=4")
```

### 8.5 Auditoria e Logging

```python
# Structured logging para SIEM
logger.info(
    "media_uf_query",
    extra={
        "user_id": current_user.id,
        "ano": ano,
        "uf": uf,
        "response_time_ms": elapsed,
        "result_count": len(data)
    }
)
```

---

## 9. ⚡ Performance e Latência

### 9.1 Estratégias de Otimização

#### 9.1.1 Backend (Python/DuckDB)

| Técnica | Descrição | Impacto |
|---------|-----------|---------|
| __Pré-agregação__ | Dados agregados em batch (Parquet) | -90% tempo de query |
| __Índices Parquet__ | Particionamento por `ano_enem` | -50% I/O |
| __Query Caching__ | Cache em memória (5 min TTL) | -80% latência P50 |
| __Connection Pooling__ | Reuso de conexões DuckDB (read-only) | -30% overhead |

#### 9.1.2 Implementação de Cache

```python
# services/cache.py
from functools import lru_cache
from datetime import datetime, timedelta

_cache: dict[str, tuple[datetime, Any]] = {}
CACHE_TTL = timedelta(minutes=5)

def cached_query(key: str, fetcher: Callable[[], Any]) -> Any:
    now = datetime.now()
    if key in _cache:
        timestamp, data = _cache[key]
        if now - timestamp < CACHE_TTL:
            return data
    
    data = fetcher()
    _cache[key] = (now, data)
    return data
```

#### 9.1.3 Frontend (React)

| Técnica | Descrição |
|---------|-----------|
| **Lazy Loading** | Componente de gráfico carregado sob demanda |
| **React.memo** | Evita re-renders desnecessários |
| **useMemo/useCallback** | Memoização de cálculos e handlers |
| **Virtual Scrolling** | Para tabelas com muitos UFs |

```typescript
// components/MediaUfBarChart.tsx
import { lazy, Suspense, useMemo } from 'react';
import { Skeleton } from '@/components/ui/skeleton';

const HighchartsBar = lazy(() => import('./HighchartsBar'));

export function MediaUfBarChart({ data }: Props) {
  const chartData = useMemo(() => transformData(data), [data]);
  
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <HighchartsBar data={chartData} />
    </Suspense>
  );
}
```

### 9.2 Metas de Latência

| Operação | P50 | P95 | P99 |
|----------|-----|-----|-----|
| GET `/v1/dados/media-uf` (cached) | 20ms | 50ms | 100ms |
| GET `/v1/dados/media-uf` (uncached) | 150ms | 400ms | 800ms |
| Pipeline de agregação (batch) | - | - | 5 min |

### 9.3 Monitoramento de Performance

```python
# Middleware para métricas de latência
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    
    logger.info(
        "request_timing",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status": response.status_code,
            "latency_ms": round(elapsed, 2)
        }
    )
    return response
```

---

## 10. 🎨 Experiência UI/UX

### 10.1 Princípios de Design

1. **Clareza Visual**: Gráficos de fácil leitura com legendas claras
2. **Feedback Imediato**: Skeletons e loading states
3. **Responsividade**: Funciona em desktop, tablet e mobile
4. **Acessibilidade**: WCAG 2.1 AA (Radix UI primitives)
5. **Interatividade**: Tooltips, hover effects, drill-down

### 10.2 Componentes de Visualização

#### 10.2.1 MediaUfBarChart (Principal)

```typescript
// Gráfico de barras empilhadas por UF/Faixa
interface MediaUfChartProps {
  data: MediaUfData[];
  selectedUf?: string;
  onUfSelect: (uf: string) => void;
}

// Features:
// - Barras coloridas por faixa (gradient de vermelho → verde)
// - Tooltip com detalhes ao hover
// - Click para filtrar por UF
// - Animação suave de entrada (Framer Motion)
```

#### 10.2.2 Paleta de Cores

```css
:root {
  --faixa-1: #ef4444; /* 0-400: Vermelho */
  --faixa-2: #f97316; /* 400-600: Laranja */
  --faixa-3: #22c55e; /* 600-800: Verde */
  --faixa-4: #3b82f6; /* 800-1000: Azul */
}
```

### 10.3 Estados de Interface

| Estado | Visual | Comportamento |
|--------|--------|---------------|
| **Loading** | Skeleton cards com shimmer | Mostra estrutura do layout |
| **Empty** | Ilustração + mensagem amigável | "Nenhum dado encontrado para este filtro" |
| **Error** | Alert vermelho + retry button | Captura via Error Boundary |
| **Success** | Gráfico com animação de entrada | Transição suave (300ms) |

### 10.4 Filtros Interativos

```typescript
// Componente de filtros reutilizável
<FilterPanel>
  <YearSelect 
    value={selectedYear} 
    onChange={setSelectedYear}
    options={availableYears}
  />
  <StateSelect
    value={selectedUf}
    onChange={setSelectedUf}
    options={brazilianStates}
    placeholder="Todos os estados"
  />
  <Button 
    variant="outline" 
    onClick={clearFilters}
    disabled={!hasActiveFilters}
  >
    Limpar Filtros
  </Button>
</FilterPanel>
```

### 10.5 Wireframe Visual

```ini
┌─────────────────────────────────────────────────────────────┐
│  📊 Distribuição de Médias por UF                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │ Ano: [2023▾] │  │ UF: [Todos▾] │  │ Limpar Filtros  │    │
│  └──────────────┘  └──────────────┘  └─────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  █████████████████████████ SP (2.5M)                        │
│  ████████████████████ MG (1.8M)                             │
│  █████████████████ RJ (1.5M)                                │
│  ████████████████ BA (1.2M)                                  │
│  ...                                                         │
│                                                              │
│  ■ 0-400   ■ 400-600   ■ 600-800   ■ 800-1000              │
└─────────────────────────────────────────────────────────────┘
```

### 10.6 Responsividade

```css
/* Mobile-first breakpoints */
@media (max-width: 768px) {
  .chart-container {
    height: 400px;
    overflow-x: auto;
  }
  
  .filter-panel {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .bar-chart {
    min-width: 600px; /* scroll horizontal para muitos UFs */
  }
}
```

---

## 11. Observabilidade, Monitoramento e Logging

### 11.1 Logs Estruturados

```python
# Padrão de logging JSON para SIEM/ELK
{
    "timestamp": "2025-12-11T10:30:00Z",
    "level": "INFO",
    "event": "media_uf_pipeline_completed",
    "data": {
        "ano": 2023,
        "total_alunos": 4500000,
        "alunos_validos": 4200000,
        "alunos_descartados": 300000,
        "duration_seconds": 180,
        "aggregations_by_uf": 27
    }
}
```

### 11.2 Métricas a Capturar

| Categoria | Métrica | Tipo |
|-----------|---------|------|
| **Pipeline** | Alunos processados | Counter |
| **Pipeline** | Alunos descartados (notas incompletas) | Counter |
| **Pipeline** | Tempo de execução | Histogram |
| **API** | Requests por endpoint | Counter |
| **API** | Latência de response | Histogram |
| **API** | Taxa de erros 4xx/5xx | Counter |
| **Cache** | Hit rate | Gauge |

### 11.3 Alertas Recomendados

| Condição | Severidade | Ação |
|----------|------------|------|
| Latência P95 > 1s | Warning | Investigar query performance |
| Erro rate > 5% | Critical | Verificar logs e rollback |
| Pipeline > 10 min | Warning | Otimizar transformações |
| Cache hit rate < 50% | Info | Revisar TTL e keys |

---

## 12. Plano de Testes e Qualidade

### 12.1 Estratégia de Testes

```mermaid
graph TB
    subgraph "Pirâmide de Testes"
        E2E["🌐 E2E (Playwright)"]
        INT["🔗 Integração (Pytest)"]
        UNIT["🧪 Unitários (Pytest)"]
        STATIC["📐 Estático (Mypy/Ruff)"]
    end
    
    STATIC --> UNIT --> INT --> E2E
```

### 12.2 Testes Unitários

#### 12.2.1 Backend

```python
# tests/unit/test_media_uf.py
import pytest
import polars as pl
from enem_project.data.gold.media_uf_pipeline import (
    calcular_media_5_disc,
    classificar_faixa_media
)

class TestCalcularMedia:
    def test_media_correta_5_notas_completas(self):
        df = pl.DataFrame({
            "nota_ling": [600.0],
            "nota_mat": [700.0],
            "nota_ch": [650.0],
            "nota_cn": [550.0],
            "nota_red": [800.0]
        })
        result = calcular_media_5_disc(df)
        assert result["media_5_disc"][0] == 660.0

    def test_exclui_aluno_com_nota_nula(self):
        df = pl.DataFrame({
            "nota_ling": [600.0],
            "nota_mat": [None],
            "nota_ch": [650.0],
            "nota_cn": [550.0],
            "nota_red": [800.0]
        })
        result = calcular_media_5_disc(df)
        assert len(result) == 0

class TestClassificarFaixa:
    @pytest.mark.parametrize("media,faixa_esperada", [
        (350.0, 1),   # [0, 400)
        (400.0, 2),   # [400, 600)
        (599.9, 2),
        (600.0, 3),   # [600, 800)
        (800.0, 4),   # [800, 1000]
        (1000.0, 4)
    ])
    def test_classificacao_correta(self, media, faixa_esperada):
        assert classificar_faixa_media(media) == faixa_esperada
```

### 12.3 Testes de Integração

```python
# tests/integration/test_media_uf_api.py
import pytest
from httpx import AsyncClient
from enem_project.api.main import app

@pytest.mark.asyncio
class TestMediaUfEndpoint:
    async def test_get_media_uf_sucesso(self, auth_client: AsyncClient):
        response = await auth_client.get(
            "/v1/dados/media-uf",
            params={"ano": 2023, "uf": "SP"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "faixas" in data
        assert len(data["faixas"]) == 4

    async def test_get_media_uf_uf_invalida(self, auth_client: AsyncClient):
        response = await auth_client.get(
            "/v1/dados/media-uf",
            params={"ano": 2023, "uf": "XX"}
        )
        assert response.status_code == 422  # Validation error

    async def test_rate_limiting(self, auth_client: AsyncClient):
        # Dispara 70 requests (limite é 60/min)
        for _ in range(70):
            await auth_client.get("/v1/dados/media-uf", params={"ano": 2023})
        
        response = await auth_client.get("/v1/dados/media-uf", params={"ano": 2023})
        assert response.status_code == 429
```

### 12.4 Testes E2E (Playwright)

```typescript
// e2e/media-uf.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Média por UF - Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('exibe gráfico de médias por UF', async ({ page }) => {
    await page.goto('/dashboard/media-uf');
    
    // Verifica que o gráfico carregou
    await expect(page.locator('.media-uf-chart')).toBeVisible();
    
    // Verifica que as 4 faixas estão na legenda
    await expect(page.locator('.chart-legend')).toContainText('0-400');
    await expect(page.locator('.chart-legend')).toContainText('800-1000');
  });

  test('filtro por UF funciona', async ({ page }) => {
    await page.goto('/dashboard/media-uf');
    
    // Seleciona São Paulo
    await page.selectOption('[data-testid="uf-filter"]', 'SP');
    
    // Verifica que apenas SP aparece
    await expect(page.locator('.bar-chart-item')).toHaveCount(1);
    await expect(page.locator('.bar-chart-item')).toContainText('SP');
  });
});
```

### 12.5 Testes de Dados (Soda Core)

```yaml
# soda/checks/agg_media5_por_uf.yml
checks for agg_media5_por_uf:
  - row_count > 0:
      name: "Tabela não está vazia"
  
  - missing_count(ano_enem) = 0:
      name: "Ano sem valores nulos"
  
  - missing_count(uf) = 0:
      name: "UF sem valores nulos"
  
  - values in (id_faixa) must be in [1, 2, 3, 4]:
      name: "Faixas válidas"
  
  - qtd_alunos > 0:
      name: "Quantidade de alunos positiva"
```

### 12.6 Comandos de Execução de Testes

```bash
# Testes unitários e integração (Backend)
cd /home/douglas/PycharmProjects/Projeto_Enem_Data_Robotics_V2
poetry run pytest tests/ -v --cov=enem_project --cov-report=html

# Testes específicos de media_uf
poetry run pytest tests/unit/test_media_uf.py tests/integration/test_media_uf_api.py -v

# Testes E2E (Frontend)
cd dashboard
npx playwright test e2e/media-uf.spec.ts --headed

# Testes de dados (Soda)
poetry run soda scan -d duckdb -c soda/configuration.yml soda/checks/
```

### 12.7 Critérios de Aceite

- [x] 100% dos testes unitários passando
- [x] 100% dos testes de integração passando
- [x] Testes E2E passando em Chrome e Firefox
- [x] Cobertura de código > 80%
- [x] Validação de dados Soda sem erros
- [x] Latência P95 < 500ms em staging
- [x] Documentação técnica atualizada

---

## 13. Riscos, Premissas e Dependências

### 13.1 Premissas

- Microdados do ENEM disponíveis e padronizados na camada Silver;
- Campo `uf` presente e com qualidade minimamente aceitável;
- Ambiente de execução (Python/FastAPI/React) já configurado;
- Acesso de leitura/escrita às tabelas/datasets necessários.

### 13.2 Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Dados de UF ou notas inconsistentes | Média | Alto | Regras de descarte claras + logging detalhado |
| Mudanças na estrutura do ENEM | Baixa | Médio | Parametrizar disciplinas e faixas via YAML |
| Aumento de tempo da pipeline | Média | Médio | Otimizar queries + usar Parquet particionado |
| Latência alta em prod | Baixa | Alto | Cache agressivo + índices adequados |
| Vulnerabilidade de segurança | Baixa | Crítico | Seguir padrões de `SecurityEngine` + code review |

### 13.3 Dependências

| Dependência | Responsável | Status |
|-------------|-------------|--------|
| Dados Silver padronizados | Engenharia de Dados | ✅ Disponível |
| Autenticação JWT | Backend | ✅ Implementado |
| Rate Limiting (SlowAPI) | Backend | ✅ Implementado |
| DuckDBAgent | Infraestrutura | ✅ Disponível |
| Componentes UI (shadcn) | Frontend | ✅ Disponível |

---

## 14. Plano de Implantação

### 14.1 Fases de Deploy

| Fase | Ambiente | Ações | Critérios de Saída |
|------|----------|-------|-------------------|
| 1. Desenvolvimento | Local | Implementação + testes unitários | Testes passando |
| 2. Integração | CI/CD | Pipeline completa + testes integração | Build verde |
| 3. Staging | Homologação | Testes E2E + validação de dados | QA aprovado |
| 4. Produção | Prod | Deploy gradual + monitoramento | KPIs dentro das metas |

### 14.2 Rollback Plan

1. Manter versão anterior do endpoint (`/v1/dados/media-uf-v1`) por 2 semanas
2. Feature flag para novo componente React
3. Backup dos dados agregados antes de reprocessamento

### 14.3 Checklist de Go-Live

```markdown
- [ ] Todos os testes passando (unit, integration, E2E)
- [ ] Code review aprovado
- [ ] Documentação atualizada
- [ ] Variáveis de ambiente configuradas em prod
- [ ] Backup de dados realizado

- [ ] Deploy backend via CI/CD
- [ ] Deploy frontend via CI/CD
- [ ] Verificar health checks

- [ ] Smoke test: Login → Dashboard → Média por UF
- [ ] Verificar latência P50/P95
- [ ] Monitorar error rate por 1 hora
- [ ] Comunicar equipe sobre disponibilidade
```

---

## 15. Checklist de Entrega

### 15.1 Engenharia de Dados

- [ ] Pipeline `media_uf_pipeline.py` implementado e versionado
- [ ] Função `calcular_media_5_disc` com tratamento de nulos
- [ ] Função `classificar_faixa_media` parametrizada via YAML
- [ ] Tabela `agg_media5_por_uf` criada e populada
- [ ] Documentação do schema e exemplo de consulta

### 15.2 Backend (API)

- [ ] Endpoint `/v1/dados/media-uf` implementado
- [ ] Schema Pydantic `MediaUfRequest`/`MediaUfResponse` validando input
- [ ] Rate limiting configurado (60 req/min)
- [ ] Cache implementado (5 min TTL)
- [ ] Logging estruturado para métricas

### 15.3 Frontend (React)

- [ ] Componente `MediaUfBarChart` implementado
- [ ] Lazy loading configurado
- [ ] Filtros de Ano e UF funcionando
- [ ] Estados de loading/error/empty
- [ ] Responsivo (mobile-friendly)
- [ ] Testes E2E cobrindo fluxo principal

### 15.4 Segurança

- [ ] Queries parametrizadas (sem SQL injection)
- [ ] Validação de input via Pydantic
- [ ] Rate limiting ativo
- [ ] Autenticação obrigatória no endpoint
- [ ] Logs de auditoria implementados

### 15.5 Qualidade e Testes

- [ ] Testes unitários criados e passando (>80% cobertura)
- [ ] Testes de integração da API executados
- [ ] Testes E2E no Playwright configurados
- [ ] Validação de dados via Soda Core
- [ ] Performance validada (P95 < 500ms)

### 15.6 Governança e Documentação

- [ ] Este documento atualizado e revisado
- [ ] Regras de negócio documentadas
- [ ] Procedimento operacional documentado
- [ ] Aprovação de negócio/produto registrada
- [ ] Data de ativação e versão registradas

---

**Documento mantido por:** Equipe de Engenharia  
**Última atualização:** 2025-12-11  
**Versão:** 2.0
