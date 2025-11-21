# Orquestração de fluxo de engenharia de dados e backend para dashboards (TypeScript/JavaScript)

Abaixo está um desenho de referência em alto nível + exemplos de código em TypeScript/JavaScript para orquestrar um fluxo de engenharia de dados no backend até o consumo em dashboards.

---

## 1. Visão geral da arquitetura

**Componentes principais:**

1. **Ingestão de dados**  
   - Recebe eventos (API REST, filas, batch, etc.)
   - Valida dados
   - Publica em uma fila ou armazena em um *data lake* / banco bruto

2. **Orquestrador de jobs de ciência de dados**  
   - Agenda e executa *pipelines* de transformação, feature engineering e scoring de modelos
   - Pode rodar como *worker* Node.js com filas (BullMQ, RabbitMQ, etc.)

3. **Camada de dados analíticos**  
   - Banco otimizado para leitura (PostgreSQL, BigQuery, ClickHouse, etc.)
   - Tabelas/materializações de métricas

4. **API de métricas para dashboards**  
   - Endpoints REST/GraphQL para o front de dashboards
   - Agregações, filtros, paginação, caching

5. **Dashboards (frontend)**  
   - Consomem a API de métricas
   - JS/TS (React, Vue, etc.)

---

## 2. Estrutura de pastas sugerida (monorepo JS/TS)

```text
backend/
  src/
    config/
    common/
    ingestion/
      controllers/
      services/
    orchestration/
      jobs/
      workers/
      schedulers/
    analytics/
      repositories/
      services/
    api/
      controllers/
      routes/
    infra/
      db/
      queue/
  tests/
  package.json
  tsconfig.json

dashboard/
  src/
    api/
    components/
    pages/
  package.json
```

---

## 3. Backend base em TypeScript (Node + Express)

### 3.1. `src/server.ts`

```ts
import express from 'express';
import bodyParser from 'body-parser';
import { ingestionRouter } from './ingestion/ingestion.router';
import { analyticsRouter } from './analytics/analytics.router';

const app = express();

app.use(bodyParser.json());

app.use('/ingestion', ingestionRouter);
app.use('/analytics', analyticsRouter);

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`API running on port ${PORT}`);
});
```

---

## 4. Camada de ingestão (dados brutos)

### 4.1. Rota de ingestão: `src/ingestion/ingestion.router.ts`

```ts
import { Router } from 'express';
import { ingestionController } from './ingestion.controller';

export const ingestionRouter = Router();

// Recebe eventos de negócio ou registros brutos
ingestionRouter.post('/event', ingestionController.ingestEvent);
```

### 4.2. Controller de ingestão: `src/ingestion/ingestion.controller.ts`

```ts
import { Request, Response } from 'express';
import { ingestionService } from './ingestion.service';

class IngestionController {
  async ingestEvent(req: Request, res: Response) {
    try {
      const payload = req.body;

      // Validação simples (poderia usar Zod/Yup/Joi)
      if (!payload || !payload.userId || !payload.timestamp) {
        return res.status(400).json({ error: 'Payload inválido' });
      }

      await ingestionService.enqueueRawEvent(payload);

      return res.status(202).json({ status: 'accepted' });
    } catch (error) {
      console.error(error);
      return res.status(500).json({ error: 'Erro ao ingerir evento' });
    }
  }
}

export const ingestionController = new IngestionController();
```

### 4.3. Service de ingestão com fila: `src/ingestion/ingestion.service.ts`

Exemplo usando **BullMQ** (Redis) como fila.

```ts
import { Queue } from 'bullmq';

interface RawEvent {
  userId: string;
  timestamp: string;
  type: string;
  metadata: Record<string, any>;
}

const connection = { host: process.env.REDIS_HOST || 'localhost', port: 6379 };

const rawEventsQueue = new Queue<RawEvent>('raw-events', { connection });

class IngestionService {
  async enqueueRawEvent(event: RawEvent) {
    await rawEventsQueue.add('raw-event', event, {
      removeOnComplete: true,
      attempts: 3,
    });
  }
}

export const ingestionService = new IngestionService();
export { rawEventsQueue };
```

---

## 5. Orquestração de jobs de ciência de dados

Aqui o foco é transformar os eventos brutos em **features** e métricas para dashboards.

### 5.1. Worker de processamento: `src/orchestration/workers/raw-events.worker.ts`

```ts
import { Worker, Job } from 'bullmq';
import { rawEventsQueue } from '../../ingestion/ingestion.service';
import { analyticsService } from '../../analytics/analytics.service';

const connection = { host: process.env.REDIS_HOST || 'localhost', port: 6379 };

interface RawEvent {
  userId: string;
  timestamp: string;
  type: string;
  metadata: Record<string, any>;
}

const worker = new Worker<RawEvent>(
  rawEventsQueue.name,
  async (job: Job<RawEvent>) => {
    const event = job.data;

    // 1. Enriquecimento/feature engineering (exemplo simples)
    const features = {
      userId: event.userId,
      eventType: event.type,
      ts: new Date(event.timestamp),
      // Exemplo: extrair campos específicos do metadata
      value: event.metadata?.value ?? 0,
    };

    // 2. (Opcional) Chamada a modelo de ML externo (Python, serviço gRPC/http)
    // const score = await modelClient.score(features);

    // 3. Persistir em tabela analítica
    await analyticsService.saveEventFeature(features);
  },
  { connection }
);

worker.on('completed', (job) => {
  console.log(`Job ${job.id} processado com sucesso`);
});

worker.on('failed', (job, err) => {
  console.error(`Job ${job?.id} falhou`, err);
});
```

### 5.2. Scheduler para jobs batch (diários/horários): `src/orchestration/schedulers/daily-metrics.scheduler.ts`

Exemplo usando **node-cron**.

```ts
import cron from 'node-cron';
import { analyticsService } from '../../analytics/analytics.service';

// Roda todo dia às 02:00 para agregar métricas diárias
cron.schedule('0 2 * * *', async () => {
  console.log('[Scheduler] Calculando métricas diárias...');
  await analyticsService.computeDailyMetrics();
});
```

---

## 6. Camada analítica e API para dashboards

### 6.1. Repositório analítico: `src/analytics/analytics.repository.ts`

Exemplo com PostgreSQL (usando `pg`).

```ts
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

interface EventFeature {
  userId: string;
  eventType: string;
  ts: Date;
  value: number;
}

export const analyticsRepository = {
  async insertEventFeature(feature: EventFeature) {
    await pool.query(
      `INSERT INTO event_features (user_id, event_type, ts, value)
       VALUES ($1, $2, $3, $4)`,
      [feature.userId, feature.eventType, feature.ts, feature.value]
    );
  },

  async getTimeSeriesMetric(metric: string, from: string, to: string) {
    // Exemplo simples: soma de "value" por dia
    const result = await pool.query(
      `SELECT date_trunc('day', ts) as day, SUM(value) as total
       FROM event_features
       WHERE ts BETWEEN $1 AND $2
       GROUP BY 1
       ORDER BY 1`,
      [from, to]
    );
    return result.rows;
  },
};
```

### 6.2. Service analítico: `src/analytics/analytics.service.ts`

```ts
import { analyticsRepository } from './analytics.repository';

interface EventFeature {
  userId: string;
  eventType: string;
  ts: Date;
  value: number;
}

class AnalyticsService {
  async saveEventFeature(feature: EventFeature) {
    await analyticsRepository.insertEventFeature(feature);
  }

  async computeDailyMetrics() {
    // Aqui você poderia materializar métricas em tabelas auxiliares
    // Ex.: criar uma tabela daily_metrics com agregados por dia/tipo
    // Exemplo simplificado omitindo SQL específico
    console.log('Recomputando métricas diárias (placeholder)...');
  }

  async getMetricTimeSeries(metric: string, from: string, to: string) {
    // Poderia haver lógica específica por métrica
    return analyticsRepository.getTimeSeriesMetric(metric, from, to);
  }
}

export const analyticsService = new AnalyticsService();
```

### 6.3. Router de analytics: `src/analytics/analytics.router.ts`

```ts
import { Router } from 'express';
import { analyticsController } from './analytics.controller';

export const analyticsRouter = Router();

analyticsRouter.get('/metrics/:metric/time-series', analyticsController.getMetricTimeSeries);
```

### 6.4. Controller de analytics: `src/analytics/analytics.controller.ts`

```ts
import { Request, Response } from 'express';
import { analyticsService } from './analytics.service';

class AnalyticsController {
  async getMetricTimeSeries(req: Request, res: Response) {
    try {
      const { metric } = req.params;
      const { from, to } = req.query as { from?: string; to?: string };

      if (!from || !to) {
        return res.status(400).json({ error: 'Parâmetros from e to são obrigatórios' });
      }

      const data = await analyticsService.getMetricTimeSeries(metric, from, to);

      return res.json({ metric, from, to, data });
    } catch (error) {
      console.error(error);
      return res.status(500).json({ error: 'Erro ao buscar métricas' });
    }
  }
}

export const analyticsController = new AnalyticsController();
```

---

## 7. Consumo em dashboard (frontend JS/TS)

Exemplo simples em React (TypeScript) consumindo a API de métricas.

### 7.1. Hook de API: `dashboard/src/api/useMetricTimeSeries.ts`

```ts
import { useEffect, useState } from 'react';

interface TimeSeriesPoint {
  day: string;
  total: string;
}

export function useMetricTimeSeries(metric: string, from: string, to: string) {
  const [data, setData] = useState<TimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ from, to });
        const res = await fetch(`/analytics/metrics/${metric}/time-series?` + params.toString());
        if (!res.ok) {
          throw new Error('Erro ao buscar métricas');
        }
        const json = await res.json();
        setData(json.data);
      } catch (err: any) {
        setError(err.message ?? 'Erro desconhecido');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [metric, from, to]);

  return { data, loading, error };
}
```

### 7.2. Componente de dashboard: `dashboard/src/components/MetricChart.tsx`

```tsx
import React from 'react';
import { useMetricTimeSeries } from '../api/useMetricTimeSeries';

interface MetricChartProps {
  metric: string;
  from: string;
  to: string;
}

export const MetricChart: React.FC<MetricChartProps> = ({ metric, from, to }) => {
  const { data, loading, error } = useMetricTimeSeries(metric, from, to);

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div>
      <h2>{metric}</h2>
      <ul>
        {data.map((point) => (
          <li key={point.day}>
            {point.day}: {point.total}
          </li>
        ))}
      </ul>
      {/* Aqui você pode integrar qualquer lib de gráficos (Recharts, Chart.js, ECharts, etc.) */}
    </div>
  );
};
```

---

## 8. Fluxo de ponta a ponta (resumo)

1. **Dashboard / Cliente** envia dados de evento → `POST /ingestion/event`  
2. **API de ingestão** valida e envia evento para **fila** `raw-events`.  
3. **Worker de orquestração** consome `raw-events`, faz feature engineering, chama modelo (se houver) e salva em tabelas analíticas.  
4. (Opcional) **Schedulers** agregam/materalizam métricas (ex.: diárias).  
5. **API de analytics** expõe endpoints de métricas (time series, agregados, etc.).  
6. **Dashboards** (TS/JS) consomem a API e renderizam visualizações.

---

## 9. Próximos passos / extensões possíveis

- Adicionar autenticação/autorização (JWT, OAuth2) nas rotas de analytics.  
- Abstrair melhor o orquestrador (ex.: orquestração baseada em DAG usando Temporal.io ou Airflow + API intermediária).  
- Implementar cache de métricas (Redis) para evitar consultas pesadas repetidas.  
- Versionamento de modelos de ML e *feature store* dedicada.  
- Observabilidade: métricas de jobs, filas, tempo de resposta da API e *data quality checks*.

