import React, { useEffect, useState, useMemo, useCallback } from "react";
import { useFilters } from "../context/FilterContext";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Skeleton } from "./ui/skeleton";
import {
  getDistribuicaoNotas,
  getMunicipios,
  type DistribuicaoNotasRow,
} from "../api/dashboard";
import Highcharts from "highcharts";
import HighchartsReact from "highcharts-react-official";

// Cores para as faixas - do vermelho ao azul (performance crescente)
const FAIXA_COLORS: Record<string, string> = {
  "Abaixo de 400": "#ef4444",       // Red-500
  "400 a 600": "#f97316",           // Orange-500
  "600 a 800": "#22c55e",           // Green-500
  "Acima de 800": "#3b82f6",        // Blue-500
};

// Ícones para as faixas
const FAIXA_ICONS: Record<string, string> = {
  "Abaixo de 400": "📉",
  "400 a 600": "📊",
  "600 a 800": "📈",
  "Acima de 800": "🏆",
};

export function ScoreDistributionChart() {
  const { uf, year } = useFilters();

  // State
  const [municipios, setMunicipios] = useState<string[]>([]);
  const [selectedMunicipio, setSelectedMunicipio] = useState<string>("");
  const [data, setData] = useState<DistribuicaoNotasRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMunicipios, setLoadingMunicipios] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load municipalities when UF changes
  useEffect(() => {
    if (!uf || uf === "all") {
      setMunicipios([]);
      setSelectedMunicipio("");
      return;
    }

    let cancelled = false;

    async function loadMunicipios() {
      setLoadingMunicipios(true);
      try {
        const result = await getMunicipios(uf);
        if (!cancelled) {
          setMunicipios(result);
          setSelectedMunicipio(""); // Reset selection
        }
      } catch (err) {
        console.error("Failed to load municipios:", err);
        setMunicipios([]);
      } finally {
        if (!cancelled) {
          setLoadingMunicipios(false);
        }
      }
    }

    loadMunicipios();

    return () => {
      cancelled = true;
    };
  }, [uf]);

  // Load distribution data
  useEffect(() => {
    if (!uf || uf === "all") {
      setData([]);
      return;
    }

    let cancelled = false;

    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const result = await getDistribuicaoNotas({
          uf,
          municipio: selectedMunicipio || undefined,
          ano: year,
        });
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, [uf, selectedMunicipio, year]);

  // Calculate total for display
  const totalAlunos = useMemo(() => {
    return data.reduce((acc, curr) => acc + curr.QTD_ALUNOS, 0);
  }, [data]);

  // Handle local municipio change
  const handleMunicipioChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setSelectedMunicipio(e.target.value);
    },
    []
  );

  // Highcharts options
  const chartOptions: Highcharts.Options = useMemo(() => {
    if (!data.length) return {};

    const locationName = selectedMunicipio || uf;

    return {
      chart: {
        type: "column",
        backgroundColor: "transparent",
        height: 400,
      },
      title: {
        text: `Distribuição de Notas - ${locationName}`,
        style: { color: "#0f172a", fontWeight: "bold", fontSize: "18px" },
      },
      subtitle: {
        text: `Ano: ${year} | Total: ${totalAlunos.toLocaleString()} alunos`,
        style: { color: "#475569" },
      },
      xAxis: {
        categories: data.map((d) => d.FAIXA),
        labels: {
          style: { color: "#64748b", fontSize: "12px", fontWeight: "600" },
        },
        title: { text: "Faixa de Nota", style: { color: "#64748b" } },
      },
      yAxis: {
        title: {
          text: "Quantidade de Alunos",
          style: { color: "#64748b", fontWeight: "500" },
        },
        labels: { style: { color: "#64748b" } },
        gridLineColor: "rgba(0, 0, 0, 0.06)",
        gridLineDashStyle: "Dot" as Highcharts.DashStyleValue,
      },
      tooltip: {
        backgroundColor: "#ffffff",
        borderColor: "#e2e8f0",
        style: { color: "#1e293b" },
        formatter: function (this: any) {
          const faixa = this.x as string;
          const icon = FAIXA_ICONS[faixa] || "📊";
          const value = this.y || 0;
          return `
            <div class="font-bold text-slate-700 mb-1">
              ${icon} ${faixa}
            </div>
            <div class="text-sm">
              <b>${value.toLocaleString()}</b> alunos
            </div>
            <div class="text-xs text-slate-500">
              ${(value / totalAlunos * 100).toFixed(1)}% do total
            </div>
          `;
        },
        useHTML: true,
      },
      legend: { enabled: false },
      plotOptions: {
        column: {
          colorByPoint: true,
          colors: data.map((d) => FAIXA_COLORS[d.FAIXA] || "#94a3b8"),
          borderRadius: 6,
          dataLabels: {
            enabled: true,
            format: "{point.y:,.0f}",
            style: {
              color: "#475569",
              fontWeight: "600",
              textOutline: "none",
            },
          },
        },
      },
      series: [
        {
          type: "column" as const,
          name: "Alunos",
          data: data.map((d) => d.QTD_ALUNOS),
        },
      ],
      credits: { enabled: false },
    };
  }, [data, uf, selectedMunicipio, year, totalAlunos]);

  // Render: UF not selected
  if (!uf || uf === "all") {
    return (
      <Card className="bg-slate-800/50 border-slate-700">
        <CardContent className="p-8 text-center">
          <p className="text-muted-foreground text-lg">
            🎯 Selecione um <strong>estado (UF)</strong> no filtro acima para
            visualizar a distribuição de notas.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white border-slate-200 shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xl flex items-center gap-2">
          📊 Distribuição por Faixas de Notas
        </CardTitle>
        <div className="flex items-center gap-2">
          <label
            htmlFor="municipio-dist-select"
            className="text-sm text-slate-500 font-medium"
          >
            Município (opcional):
          </label>
          <select
            id="municipio-dist-select"
            value={selectedMunicipio}
            onChange={handleMunicipioChange}
            className="bg-white border-slate-300 text-slate-700 px-3 py-1.5 
                       rounded-md text-sm focus:ring-2 focus:ring-primary shadow-sm"
            disabled={loadingMunicipios || municipios.length === 0}
          >
            <option value="">Todos os municípios</option>
            {municipios.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 
                          px-4 py-3 rounded mb-4">
            ❌ Erro: {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-[400px] w-full bg-slate-100" />
          </div>
        ) : data.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-lg">📭 Nenhum dado encontrado.</p>
            <p className="text-sm mt-2">
              Verifique se os dados foram processados para o local selecionado.
            </p>
          </div>
        ) : (
          <>
            <HighchartsReact highcharts={Highcharts} options={chartOptions} />

            {/* Summary Cards */}
            <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              {data.map((faixa) => (
                <div
                  key={faixa.FAIXA}
                  className="rounded-lg p-4 border shadow-sm transition-all 
                             hover:shadow-md"
                  style={{
                    backgroundColor: `${FAIXA_COLORS[faixa.FAIXA]}10`,
                    borderColor: `${FAIXA_COLORS[faixa.FAIXA]}40`,
                  }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">
                      {FAIXA_ICONS[faixa.FAIXA]}
                    </span>
                    <span
                      className="text-sm font-semibold"
                      style={{ color: FAIXA_COLORS[faixa.FAIXA] }}
                    >
                      {faixa.FAIXA}
                    </span>
                  </div>
                  <p
                    className="text-2xl font-bold"
                    style={{ color: FAIXA_COLORS[faixa.FAIXA] }}
                  >
                    {faixa.QTD_ALUNOS.toLocaleString()}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {faixa.PERCENTUAL.toFixed(1)}% do total
                  </p>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
