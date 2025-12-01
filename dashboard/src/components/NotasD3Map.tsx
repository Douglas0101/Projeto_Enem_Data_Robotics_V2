import React, { useEffect, useState, useMemo } from "react";
import Plot from "react-plotly.js";
import { feature } from "topojson-client";
import { TbNotasGeoUfRow } from "../types/dashboard";
import { Topology } from "topojson-specification";
import { Feature, FeatureCollection } from "geojson";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle
} from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";
import { useFilters } from "../context/FilterContext"; // Import useFilters

interface Props {
  data: TbNotasGeoUfRow[];
  isLoading: boolean;
  year: number;
  // onStateClick?: (state: string) => void; // Removido, será tratado via context
}

const METRICS = [
  { key: "NOTA_MATEMATICA_mean", label: "Matemática" },
  { key: "NOTA_CIENCIAS_NATUREZA_mean", label: "Ciências da Natureza" },
  { key: "NOTA_CIENCIAS_HUMANAS_mean", label: "Ciências Humanas" },
  { key: "NOTA_LINGUAGENS_CODIGOS_mean", label: "Linguagens e Códigos" },
  { key: "NOTA_REDACAO_mean", label: "Redação" },
] as const;

type MetricKey = (typeof METRICS)[number]["key"];

const UF_NOME_MAP: { [key: string]: string } = {
  AC: "Acre", RO: "Rondônia", AM: "Amazonas", RR: "Roraima", PA: "Pará",
  AP: "Amapá", TO: "Tocantins", MA: "Maranhão", PI: "Piauí", CE: "Ceará",
  RN: "Rio Grande do Norte", PB: "Paraíba", PE: "Pernambuco", AL: "Alagoas",
  SE: "Sergipe", BA: "Bahia", MG: "Minas Gerais", ES: "Espírito Santo",
  RJ: "Rio de Janeiro", SP: "São Paulo", PR: "Paraná", SC: "Santa Catarina",
  RS: "Rio Grande do Sul", MS: "Mato Grosso do Sul", MT: "Mato Grosso",
  GO: "Goiás", DF: "Distrito Federal",
};

const MAP_HEIGHT = 650;

const NotasD3Map: React.FC<Props> = ({ data, isLoading, year }) => {
  const { uf, setUf } = useFilters(); // Usar o contexto de filtros
  const [geoJsonData, setGeoJsonData] = useState<FeatureCollection | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>("NOTA_MATEMATICA_mean");
  const [geoLoading, setGeoLoading] = useState(true);
  const [tooltip, setTooltip] = useState({
    visible: false,
    x: 0,
    y: 0,
    uf: "",
    name: "",
    value: null as number | null,
  });

  const containerRef = React.useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const loadTopology = async () => {
      try {
        setGeoLoading(true);
        const response = await fetch("/br-states.json");
        if (!response.ok) throw new Error("Failed to load topology");
        const topology = (await response.json()) as Topology;

        const statesCollection = feature(
          topology,
          topology.objects.estados as any
        ) as unknown as FeatureCollection;
        const statesWithSigla: FeatureCollection = {
          ...statesCollection,
          features: statesCollection.features.map((f) => ({
            ...(f as Feature),
            properties: {
              ...(f.properties || {}),
              SIGLA: (f as any).id ?? (f.properties as any)?.SIGLA ?? "",
            },
          })),
        };

        setGeoJsonData(statesWithSigla);
      } catch (err) {
        console.error("Erro ao carregar mapa do Brasil:", err);
      } finally {
        setGeoLoading(false);
      }
    };
    void loadTopology();
  }, []);

  const { trace, layout } = useMemo(() => {
    if (!geoJsonData || !data?.length) return { trace: null, layout: null };

    const filteredData = data.filter((d) => d.ANO === year);

    const locations: string[] = [];
    const z: number[] = [];
    const text: string[] = [];
    let minValue = Infinity;
    let maxValue = -Infinity;

    filteredData.forEach((row) => {
      const val = (row as any)[selectedMetric] as number | null;
      if (val !== null && row.SG_UF_PROVA !== "UNKNOWN") {
        locations.push(row.SG_UF_PROVA);
        z.push(val);
        text.push(UF_NOME_MAP[row.SG_UF_PROVA] || row.SG_UF_PROVA);
        minValue = Math.min(minValue, val);
        maxValue = Math.max(maxValue, val);
      }
    });

    const zmin = minValue !== Infinity ? minValue : undefined;
    const zmax = maxValue !== -Infinity ? maxValue : undefined;

    const choroplethTrace: any = {
      type: "choropleth",
      geojson: geoJsonData,
      locations: locations,
      z: z,
      featureidkey: "properties.SIGLA",
      colorscale: "Blues",
      reversescale: false,
      zmin,
      zmax,
      marker: {
        line: {
          color: "white",
          width: 0.6,
        },
        // Adicionar um destaque visual para o UF selecionado
        line_width: locations.map(l => l === uf ? 3 : 0.6),
        line_color: locations.map(l => l === uf ? '#FFD700' : 'white'), // Destaque amarelo
      },
      text: text,
      hoverinfo: "none",
      colorbar: {
        orientation: 'h', // Horizontal
        title: { text: "Média de Notas", side: "top" },
        thickness: 10, // Muito fina
        len: 0.4, // 40% da largura
        x: 0.5, // Centralizada horizontalmente
        xanchor: 'center',
        y: -0.1, // Abaixo do mapa (ou use 1.02 para acima)
        yanchor: 'top',
        bgcolor: 'rgba(0,0,0,0)',
        outlinewidth: 0,
        ticklen: 4,
        tickfont: { family: 'Inter, sans-serif', size: 10, color: '#64748b' },
        tickformat: '.0f',
      },
      showscale: true,
    };

    const plotLayout: Partial<Plotly.Layout> = {
      autosize: true,
      height: 650, // Altura fixa otimizada
      font: { family: "Inter, sans-serif", color: "#374151" },
      margin: { l: 10, r: 10, t: 30, b: 10 }, // Margens mínimas
      dragmode: false,
      geo: {
        scope: "south america", // Add scope
        fitbounds: "locations", // Garantir fitbounds
        projection: { type: "mercator" },
        showframe: false,
        showcoastlines: false,
        showcountries: false,
        showlakes: false,
        showrivers: false,
        bgcolor: "rgba(0,0,0,0)",
      },
      // Explicitly disable standard axes to avoid "axisMatchGroups" errors
      xaxis: { visible: false, fixedrange: true },
      yaxis: { visible: false, fixedrange: true },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      hovermode: "closest",
    };

    return { trace: choroplethTrace, layout: plotLayout };
  }, [geoJsonData, data, year, selectedMetric, uf]); // Adicionar uf às dependências

  const metricLabel = useMemo(
    () => METRICS.find((m) => m.key === selectedMetric)?.label ?? "Média",
    [selectedMetric]
  );

  const handleHover = React.useCallback(
    (event: Readonly<Plotly.PlotHoverEvent>) => {
      const point = event.points?.[0];
      if (!point || !containerRef.current) return;
      const mouseEvent = event.event as MouseEvent | undefined;
      if (!mouseEvent) return;
      const rect = containerRef.current.getBoundingClientRect();
      const localX = mouseEvent.clientX - rect.left + 12;
      const localY = mouseEvent.clientY - rect.top + 12;
      const ufCode = (point.location as string) || "";
      const value = typeof point.z === "number" ? point.z : null;
      setTooltip({
        visible: true,
        x: localX,
        y: localY,
        uf: ufCode,
        name: UF_NOME_MAP[ufCode] || ufCode,
        value,
      });
    },
    []
  );

  const handleUnhover = React.useCallback(() => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  }, []);

  const handleClick = React.useCallback(
    (event: Readonly<Plotly.PlotMouseEvent>) => {
      const point = event.points?.[0];
      if (point) {
        const clickedUf = (point.location as string) || "";
        if (clickedUf) {
          setUf(clickedUf === uf ? "SP" : clickedUf); // Toggle ou define. Se clicar no mesmo, reseta para SP (default)
        }
      }
    },
    [setUf, uf]
  );

  useEffect(() => {
    setTooltip((prev) => ({ ...prev, visible: false }));
  }, [selectedMetric, year, isLoading, geoLoading, uf]); // Adicionar uf

  return (
    <DashboardCard>
      <DashboardCardHeader className="flex flex-wrap items-start md:items-center gap-4 pb-4">
        <div className="space-y-1">
          <DashboardCardTitle className="text-base font-medium">
            Mapa de Desempenho Nacional - {year}
          </DashboardCardTitle>
          <p className="text-sm text-muted-foreground">
            Distribuição geográfica das médias por estado.
          </p>
        </div>
        <div className="min-w-[220px]">
          <select
            className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value as MetricKey)}
          >
            {METRICS.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      </DashboardCardHeader>
      <DashboardCardContent className="p-0">
        <div className="relative w-full min-h-[650px]" ref={containerRef}>
          {isLoading || geoLoading ? (
            <div className="flex h-[650px] items-center justify-center">
              <Skeleton className="h-full w-full max-w-[800px] max-h-[600px] rounded-md" />
            </div>
          ) : trace && layout ? (
            <Plot
              data={[trace]}
              layout={layout}
              useResizeHandler={true}
              style={{ width: "100%", minHeight: "650px" }}
              config={{ displayModeBar: false, responsive: true }}
              onHover={handleHover}
              onUnhover={handleUnhover}
              onClick={handleClick}
            />
          ) : (
            <div className="flex h-[650px] items-center justify-center text-muted-foreground">
              Dados indisponíveis para o ano selecionado.
            </div>
          )}

          {/* Custom Tailwind Tooltip */}
          {tooltip.visible && (
            <div
              className="absolute z-50 min-w-[210px] rounded-xl border bg-popover p-3 text-popover-foreground shadow-md transition-all duration-200 ease-out"
              style={{
                top: tooltip.y,
                left: tooltip.x,
                transform: "translate(-45%, -120%)",
              }}
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">
                  {tooltip.uf}
                </span>
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                  {metricLabel}
                </span>
              </div>
              <div className="mb-1 text-sm font-semibold">{tooltip.name}</div>
              <div className="text-xl font-bold text-blue-600 dark:text-blue-400 leading-none">
                {tooltip.value !== null ? tooltip.value.toFixed(1) : "--"}{" "}
                <span className="text-xs font-normal text-muted-foreground">pontos</span>
              </div>
              <div className="mt-1 text-[11px] opacity={70}">Ano {year}</div>
            </div>
          )}
        </div>
      </DashboardCardContent>
    </DashboardCard>
  );
};

export default NotasD3Map;