import React, { useEffect, useState, useMemo, useCallback } from "react";
import { useFilters } from "../context/FilterContext";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Skeleton } from "./ui/skeleton";
import {
  getMediaMunicipal,
  type MediaMunicipalRow,
} from "../api/dashboard";
import Highcharts from "highcharts";
import HighchartsReact from "highcharts-react-official";

// Color palette for disciplines - Optimized for White Theme (Darker/Saturated)
const DISCIPLINE_COLORS = {
  MEDIA_CN: "#059669", // Emerald-600
  MEDIA_CH: "#4f46e5", // Indigo-600
  MEDIA_LC: "#7c3aed", // Violet-600
  MEDIA_MT: "#d97706", // Amber-600
  MEDIA_RED: "#e11d48", // Rose-600
  MEDIA_FINAL: "#0891b2", // Cyan-600
};

const DISCIPLINE_LABELS: Record<string, string> = {
  MEDIA_CN: "Ciências da Natureza",
  MEDIA_CH: "Ciências Humanas",
  MEDIA_LC: "Linguagens e Códigos",
  MEDIA_MT: "Matemática",
  MEDIA_RED: "Redação",
  MEDIA_FINAL: "Média Final",
};

interface SeriesData {
  name: string;
  data: (number | null)[];
  color: string;
}

export function MediaMunicipalChart() {
  const { uf, year } = useFilters();

  // State
  const [municipios, setMunicipios] = useState<string[]>([]);
  const [selectedMunicipio, setSelectedMunicipio] = useState<string>("");
  const [data, setData] = useState<MediaMunicipalRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load municipalities when UF changes - use media-municipal data for accurate filtering
  useEffect(() => {
    if (!uf || uf === "all") {
      setMunicipios([]);
      setSelectedMunicipio("");
      return;
    }

    let cancelled = false;

    async function loadMunicipios() {
      try {
        // Fetch municipalities that have data in the media-municipal table
        // Use the endpoint with no municipio filter to get all municipalities for the UF
        const result = await getMediaMunicipal({
          uf,
          anoInicio: 2009,
          anoFim: 2024,
          minAlunos: 50,
        });
        if (!cancelled) {
          // Extract unique municipality names from the results
          const uniqueCities = [...new Set(result.map(r => r.NO_MUNICIPIO_PROVA))].sort();
          setMunicipios(uniqueCities);
          setSelectedMunicipio(""); // Reset selection
        }
      } catch (err) {
        console.error("Failed to load municipios:", err);
        setMunicipios([]);
      }
    }

    loadMunicipios();

    return () => {
      cancelled = true;
    };
  }, [uf]);

  // Load data when municipality is selected
  useEffect(() => {
    if (!uf || uf === "all" || !selectedMunicipio) {
      setData([]);
      return;
    }

    let cancelled = false;

    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const result = await getMediaMunicipal({
          uf,
          municipio: selectedMunicipio,
          anoInicio: 2009,
          anoFim: 2024,
          minAlunos: 50,
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
  }, [uf, selectedMunicipio]);

  // Transform data for chart
  const chartData = useMemo(() => {
    if (!data.length) return null;

    // Get all years from data
    const years = [...new Set(data.map((d) => d.ANO))].sort();

    // Build series for each discipline
    const disciplines = [
      "MEDIA_CN",
      "MEDIA_CH",
      "MEDIA_LC",
      "MEDIA_MT",
      "MEDIA_RED",
      "MEDIA_FINAL",
    ] as const;

    const series: SeriesData[] = disciplines.map((disc) => ({
      name: DISCIPLINE_LABELS[disc],
      color: DISCIPLINE_COLORS[disc],
      data: years.map((y) => {
        const row = data.find((d) => d.ANO === y);
        return row ? row[disc] : null;
      }),
    }));

    // Also get QTD_ALUNOS for tooltip
    const alunosPerYear = years.map((y) => {
      const row = data.find((d) => d.ANO === y);
      return row?.QTD_ALUNOS ?? 0;
    });

    return { years, series, alunosPerYear };
  }, [data]);

  // Highcharts options
  const chartOptions: Highcharts.Options = useMemo(() => {
    if (!chartData) return {};

    return {
      chart: {
        type: "areaspline",
        backgroundColor: "transparent",
        height: 450,
      },
      title: {
        text: `Evolução das Médias - ${selectedMunicipio}`,
        style: { color: "#0f172a", fontWeight: "bold", fontSize: "18px" },
      },
      subtitle: {
        text: `UF: ${uf} | Anos: 2009-2024`,
        style: { color: "#475569" },
      },
      xAxis: {
        categories: chartData.years.map(String),
        labels: { style: { color: "#94a3b8" } },
        title: { text: "Ano", style: { color: "#94a3b8" } },
        plotBands: [{
          from: chartData.years.indexOf(2020),
          to: chartData.years.indexOf(2022),
          color: "rgba(99, 102, 241, 0.05)",
          label: {
            text: "Pandemia",
            style: { color: "#6366f1", fontSize: "11px", fontWeight: "600" },
            verticalAlign: "top",
            y: 15,
          },
        }],
      },
      yAxis: {
        title: { text: "Média", style: { color: "#64748b", fontWeight: "500" } },
        labels: { style: { color: "#64748b" } },
        min: 0,
        max: 1000,
        gridLineColor: "rgba(0, 0, 0, 0.06)",
        gridLineDashStyle: "Dot" as Highcharts.DashStyleValue,
      },
      tooltip: {
        shared: true,
        backgroundColor: "#ffffff",
        borderColor: "#e2e8f0",
        style: { color: "#1e293b" },
        formatter: function () {
          // Robustly get index and data
          const points = this.points || [];
          if (points.length === 0) return "";
          
          // Cast allows accessing internal point index safely
          const pointIndex = (points[0] as any).point.index;
          const year = chartData.years[pointIndex];
          const alunos = chartData.alunosPerYear[pointIndex] ?? 0;
          
          let s = `<div class="font-bold text-slate-700 mb-2 border-b border-slate-200 pb-1">Ano: ${year}</div>`;
          s += `<div class="text-xs text-slate-500 mb-2">Alunos: <span class="font-semibold text-slate-700">${alunos.toLocaleString()}</span></div>`;
          
          points.forEach((p) => {
            s += `<div class="flex items-center gap-1.5 text-xs py-0.5">
              <span style="color:${p.color}; font-size: 14px;">●</span> 
              <span class="text-slate-600">${p.series.name}:</span> 
              <span class="font-bold text-slate-800 ml-auto">${p.y?.toFixed(1) ?? "N/A"}</span>
            </div>`;
          });
          return s;
        },
        useHTML: true,
      },
      legend: {
        layout: "horizontal",
        align: "center",
        verticalAlign: "top",
        y: 0,
        floating: false,
        borderWidth: 0,
        backgroundColor: "transparent",
        itemStyle: { 
          color: "#475569",
          fontWeight: "600",
          fontSize: "12px",
        },
        itemHoverStyle: { color: "#0f172a" },
        itemDistance: 16,
      },
      plotOptions: {
        areaspline: {
          fillOpacity: 0.15,
          lineWidth: 2.5,
          states: {
            hover: {
              lineWidth: 3,
            },
          },
        },
      },
      series: chartData.series.map((s) => ({
        type: "areaspline" as const,
        name: s.name,
        data: s.data,
        color: s.color,
        marker: { enabled: true, radius: 4 },
        lineWidth: 2,
      })),
      credits: { enabled: false },
    };
  }, [chartData, selectedMunicipio, uf]);

  const handleMunicipioChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setSelectedMunicipio(e.target.value);
    },
    []
  );

  // Render
  if (!uf || uf === "all") {
    return (
      <Card className="bg-slate-800/50 border-slate-700">
        <CardContent className="p-8 text-center">
          <p className="text-muted-foreground text-lg">
            🎯 Selecione um <strong>estado (UF)</strong> no filtro acima para
            visualizar a evolução municipal.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white border-slate-200 shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xl flex items-center gap-2">
          📊 Média Municipal - Evolução Temporal
        </CardTitle>
        <div className="flex items-center gap-2">
          <label htmlFor="municipio-select" className="text-sm text-slate-500 font-medium">
            Município:
          </label>
          <select
            id="municipio-select"
            value={selectedMunicipio}
            onChange={handleMunicipioChange}
            className="bg-white border-slate-300 text-slate-700 px-3 py-1.5 rounded-md text-sm focus:ring-2 focus:ring-primary shadow-sm"
            disabled={loading || municipios.length === 0}
          >
            <option value="">Selecione...</option>
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
          <div className="bg-red-900/30 border border-red-500/50 text-red-200 px-4 py-3 rounded mb-4">
            ❌ Erro: {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-[450px] w-full bg-slate-100" />
          </div>
        ) : !selectedMunicipio ? (
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-lg">
              👆 Selecione um <strong>município</strong> acima para visualizar os
              dados.
            </p>
            <p className="text-sm mt-2">
              {municipios.length > 0
                ? `${municipios.length} municípios disponíveis para ${uf}`
                : "Carregando municípios..."}
            </p>
          </div>
        ) : data.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-lg">📭 Nenhum dado encontrado para este município.</p>
            <p className="text-sm mt-2">
              Tente outro município ou verifique se os dados foram processados.
            </p>
          </div>
        ) : (
          <>
            <HighchartsReact highcharts={Highcharts} options={chartOptions} />
            <div className="mt-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {Object.entries(DISCIPLINE_LABELS).map(([key, label]) => {
                const latestData = data.find((d) => d.ANO === Math.max(...data.map((r) => r.ANO)));
                const value = latestData?.[key as keyof MediaMunicipalRow] as number | null;
                return (
                  <div
                    key={key}
                    className="rounded-lg p-3 border transition-all hover:bg-slate-50 flex flex-row items-center justify-between gap-3 shadow-sm"
                    style={{ 
                      backgroundColor: "#ffffff",
                      borderColor: `${DISCIPLINE_COLORS[key as keyof typeof DISCIPLINE_COLORS]}40`,
                    }}
                  >
                    <div className="flex flex-col items-start min-w-0">
                      <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold truncate w-full" title={label}>
                        {label.replace("Ciências da ", "C. ").replace("Linguagens e ", "Ling. ")}
                      </p>
                    </div>
                    <p 
                      className="text-lg font-bold whitespace-nowrap"
                      style={{ color: DISCIPLINE_COLORS[key as keyof typeof DISCIPLINE_COLORS] }}
                    >
                      {value != null ? value.toFixed(1) : "N/A"}
                    </p>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
