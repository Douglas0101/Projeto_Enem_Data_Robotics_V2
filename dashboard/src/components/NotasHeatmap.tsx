import { useState, useEffect, useMemo, useRef, useLayoutEffect } from "react";
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";

import { TbNotasGeoUfRow } from "../types/dashboard";
import { getNotasGeoUf } from "../api/dashboard";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle
} from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";

const METRICS = [
  { key: "NOTA_MATEMATICA_mean", label: "Matemática" },
  { key: "NOTA_CIENCIAS_NATUREZA_mean", label: "Ciências da Natureza" },
  { key: "NOTA_CIENCIAS_HUMANAS_mean", label: "Ciências Humanas" },
  { key: "NOTA_LINGUAGENS_CODIGOS_mean", label: "Linguagens e Códigos" },
  { key: "NOTA_REDACAO_mean", label: "Redação" },
] as const;

type MetricKey = (typeof METRICS)[number]["key"];

const BAR_COLORS: Record<string, string> = {
  "Matemática": "#0f3d91",
  "Ciências da Natureza": "#1e739e",
  "Ciências Humanas": "#159a9c",
  "Linguagens e Códigos": "#2bba9e",
  "Redação": "#0b7a70",
};

const YEAR_RANGE = Array.from({ length: 2024 - 2009 + 1 }, (_, i) => 2009 + i);

type BarTrace = {
  name: string;
  values: (number | null)[];
};

// --- Editorial Bar Chart Component ---
interface EditorialBarChartProps {
  data: BarTrace[];
  years: number[];
  isLoading?: boolean;
}

function EditorialBarChart({ data, years, isLoading }: EditorialBarChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  // Transform Data for amCharts
  const chartData = useMemo(() => {
    return years.map((year, index) => {
      const item: any = { year: year.toString() };
      data.forEach(trace => {
        item[trace.name] = trace.values[index];
      });
      return item;
    });
  }, [data, years]);

  useLayoutEffect(() => {
    if (!chartRef.current || isLoading || data.length === 0) return;

    const root = am5.Root.new(chartRef.current);
    root.setThemes([am5themes_Animated.new(root)]);
    root.numberFormatter.set("numberFormat", "#,###.0");
    (root as any)._logo?.dispose();

    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: false,
        panY: false,
        wheelX: "none",
        wheelY: "none",
        layout: root.verticalLayout
      })
    );

    // Cursor
    chart.set("cursor", am5xy.XYCursor.new(root, { behavior: "none" }));

    // X Axis
    const xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(root, {
        categoryField: "year",
        renderer: am5xy.AxisRendererX.new(root, {
          minGridDistance: 30,
          cellStartLocation: 0.1,
          cellEndLocation: 0.9
        }),
        tooltip: am5.Tooltip.new(root, {})
      })
    );
    
    xAxis.data.setAll(chartData);
    xAxis.get("renderer").grid.template.set("location", 1);

    // Y Axis
    const yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        min: 0,
        max: 1000,
        renderer: am5xy.AxisRendererY.new(root, {
          strokeOpacity: 0.1
        })
      })
    );

    // Create Series
    data.forEach((trace) => {
      const series = chart.series.push(
        am5xy.ColumnSeries.new(root, {
          name: trace.name,
          xAxis: xAxis,
          yAxis: yAxis,
          valueYField: trace.name,
          categoryXField: "year",
          clustered: true
        })
      );

      series.columns.template.setAll({
        width: am5.percent(80),
        tooltipText: "{name}: {valueY.formatNumber('#,###.0')}",
        tooltipY: 0,
        strokeOpacity: 0,
        cornerRadiusTL: 8,
        cornerRadiusTR: 8,
        fill: am5.color(BAR_COLORS[trace.name] ?? "#999"),
        
        // Interaction
        draggable: true,
        dragType: "y", // Restrict dragging to Y axis
        cursorOverStyle: "ns-resize"
      });

      // Drag Event Logic
      series.columns.template.events.on("drag", function(ev) {
        const column = ev.target;
        const dataItem = column.dataItem;
        
        if (dataItem) {
          const y = column.y();
          const value = yAxis.positionToValue(yAxis.coordinateToPosition(y));
          
          // Update tooltip to show "Nova Média"
          column.set("tooltipText", `Nova Média: [bold]${value.toFixed(1)}[/]`);
          column.showTooltip();
          
          dataItem.set("valueY", value);
          dataItem.set("valueYWorking", value);
        }
      });

      // Reset tooltip on drag stop
      series.columns.template.events.on("dragstop", function(ev) {
        const column = ev.target;
        column.set("tooltipText", "{name}: {valueY}");
      });

      series.data.setAll(chartData);
    });

    // Add Legend
    const legend = chart.children.push(
        am5.Legend.new(root, {
            centerX: am5.p50,
            x: am5.p50
        })
    );
    legend.data.setAll(chart.series.values);

    chart.appear(1000, 100);

    return () => {
      root.dispose();
    };
  }, [chartData, isLoading, data]);

  if (isLoading) {
    return (
      <div className="w-full h-[500px]">
        <Skeleton className="h-full w-full rounded-md" />
      </div>
    );
  }

  return (
    <div ref={chartRef} className="w-full h-[500px]" />
  );
}

// --- Editorial Heatmap Component ---
interface EditorialHeatmapProps {
  data: { uf: string; year: string; value: number }[];
}

function EditorialHeatmap({ data }: EditorialHeatmapProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!chartRef.current || data.length === 0) return;

    const root = am5.Root.new(chartRef.current);
    root.setThemes([am5themes_Animated.new(root)]);
    root.numberFormatter.set("numberFormat", "#,###.0");
    (root as any)._logo?.dispose();

    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: false,
        panY: false,
        wheelX: "none",
        wheelY: "none",
        layout: root.verticalLayout
      })
    );

    // Axes
    // X Axis (Years) - Top for matrix feel
    const xRenderer = am5xy.AxisRendererX.new(root, {
      minGridDistance: 30,
      opposite: true
    });
    xRenderer.grid.template.set("visible", false);

    const xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(root, {
        renderer: xRenderer,
        categoryField: "year",
        tooltip: am5.Tooltip.new(root, {})
      })
    );

    // Y Axis (States)
    const yRenderer = am5xy.AxisRendererY.new(root, {
      minGridDistance: 20,
      inversed: true
    });
    yRenderer.grid.template.set("visible", false);

    const yAxis = chart.yAxes.push(
      am5xy.CategoryAxis.new(root, {
        renderer: yRenderer,
        categoryField: "uf"
      })
    );

    // Series
    const series = chart.series.push(
      am5xy.ColumnSeries.new(root, {
        calculateAggregates: true,
        stroke: am5.color(0xffffff),
        clustered: false,
        xAxis: xAxis,
        yAxis: yAxis,
        categoryXField: "year",
        categoryYField: "uf",
        valueField: "value"
      })
    );

    series.columns.template.setAll({
      tooltipText: "[bold]{categoryY}[/] em [bold]{categoryX}[/]:\nMédia: [bold]{value.formatNumber('#.0')}[/]",
      tooltip: am5.Tooltip.new(root, {}),
      strokeOpacity: 1,
      strokeWidth: 2,
      width: am5.percent(100),
      height: am5.percent(100),
      cornerRadiusTL: 4,
      cornerRadiusTR: 4,
      cornerRadiusBL: 4,
      cornerRadiusBR: 4
    });

    // Add Cursor for better hover interaction
    chart.set("cursor", am5xy.XYCursor.new(root, {
      behavior: "none"
    }));

    // Heat Rules
    series.set("heatRules", [{
      target: series.columns.template,
      min: am5.color(0xe6e6e6),
      max: am5.color(0x0f3d91), // Blue matching dashboard theme
      dataField: "value",
      key: "fill"
    }]);

    // Heat Legend
    const heatLegend = chart.children.push(
      am5.HeatLegend.new(root, {
        orientation: "horizontal",
        startColor: am5.color(0xe6e6e6),
        endColor: am5.color(0x0f3d91),
        startText: "Menor Nota",
        endText: "Maior Nota",
        stepCount: 5,
        width: am5.percent(100),
        paddingTop: 20
      })
    );

    // Legend interactivity
    series.columns.template.events.on("pointerover", function(ev) {
      const di = ev.target.dataItem;
      if (di) {
        const value = di.get("value");
        if (typeof value === "number") {
          heatLegend.showValue(value);
        }
      }
    });

    series.columns.template.events.on("pointerout", function(ev) {
      heatLegend.hideTooltip();
    });

    series.events.on("datavalidated", function () {
      heatLegend.set("startValue", series.getPrivate("valueLow"));
      heatLegend.set("endValue", series.getPrivate("valueHigh"));
    });

    // Set Data
    const years = Array.from(new Set(data.map(d => d.year))).sort();
    const ufs = Array.from(new Set(data.map(d => d.uf))).sort();
    
    xAxis.data.setAll(years.map(y => ({ year: y })));
    yAxis.data.setAll(ufs.map(u => ({ uf: u })));
    series.data.setAll(data);

    chart.appear(1000, 100);

    return () => {
      root.dispose();
    };
  }, [data]);

  const uniqueUfsCount = new Set(data.map(d => d.uf)).size;
  const dynamicHeight = Math.max(300, uniqueUfsCount * 40);

  return <div ref={chartRef} className="w-full" style={{ height: `${dynamicHeight}px` }} />;
}

// --- Main Component ---
interface Props {
  data: TbNotasGeoUfRow[];
  isLoading: boolean;
  year: number;
}

export default function NotasHeatmap(props: Props) {
  const { data, isLoading } = props;
  const [fallbackData, setFallbackData] = useState<TbNotasGeoUfRow[]>([]);
  const [fallbackLoading, setFallbackLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>("NOTA_MATEMATICA_mean");

  // Fallback Data Logic
  useEffect(() => {
    let cancelled = false;
    async function loadFallback() {
      if (isLoading || data.length > 0) {
        setFallbackLoading(false);
        return;
      }
      try {
        setFallbackLoading(true);
        const rows = await getNotasGeoUf({ minInscritos: 0 });
        if (!cancelled) {
          setFallbackData(rows);
        }
      } catch (err) {
        if (!cancelled) {
          setFetchError((err as Error).message);
        }
      } finally {
        if (!cancelled) {
          setFallbackLoading(false);
        }
      }
    }
    void loadFallback();
    return () => {
      cancelled = true;
    };
  }, [isLoading, data]);

  const effectiveData = data.length ? data : fallbackData;
  
  // --- Prepare Data for Top Chart (Editorial Grouped Bars) ---
  const { barChartTraces, barChartYears } = useMemo(() => {
    const filtered = effectiveData.filter((d) => d.ANO >= 2009 && d.ANO <= 2024);
    if (!filtered.length) return { barChartTraces: [], barChartYears: [] };

    const years = YEAR_RANGE;

    const traces: BarTrace[] = METRICS.map(metric => {
      const values = years.map(year => {
        const rows = filtered.filter(d => d.ANO === year);
        const validRows = rows.filter(r => (r as any)[metric.key] !== null);
        if (validRows.length === 0) return null;
        const sum = validRows.reduce((acc, r) => acc + ((r as any)[metric.key] as number), 0);
        return sum / validRows.length;
      });

      return {
        name: metric.label,
        values,
      };
    });

    return { barChartTraces: traces, barChartYears: years };
  }, [effectiveData]);

  // --- Prepare Data for Heatmap (Matrix) ---
  const heatmapData = useMemo(() => {
    const filtered = effectiveData.filter(d => d.ANO >= 2009 && d.ANO <= 2024 && d.SG_UF_PROVA !== "UNKNOWN");
    
    return filtered.map(item => ({
        year: item.ANO.toString(),
        uf: item.SG_UF_PROVA,
        value: (item as any)[selectedMetric] as number
    })).filter(d => d.value != null);
  }, [effectiveData, selectedMetric]);


  if (isLoading || fallbackLoading) {
    return (
      <DashboardCard>
        <DashboardCardContent>
          <div className="w-full h-[500px] mb-8">
             <Skeleton className="h-full w-full rounded-md" />
          </div>
          <div className="w-full h-[1000px]">
             <Skeleton className="h-full w-full rounded-md" />
          </div>
        </DashboardCardContent>
      </DashboardCard>
    );
  }

  return (
    <DashboardCard>
      <DashboardCardHeader>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <DashboardCardTitle className="text-base font-medium">
              Médias por disciplina (2009-2024)
            </DashboardCardTitle>
            <p className="text-sm text-muted-foreground">
              Agrupado por ano, valores médios por disciplina.
            </p>
          </div>
        </div>
      </DashboardCardHeader>
      <DashboardCardContent>
        {fetchError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
            <strong className="font-bold">Erro:</strong> <span className="block sm:inline">{fetchError}</span>
          </div>
        )}

        {/* TOP CHART: EDITORIAL BAR INFOGRAPHIC */}
        <div className="w-full mb-8">
          {barChartTraces.length > 0 ? (
            <EditorialBarChart data={barChartTraces} years={barChartYears} isLoading={isLoading || fallbackLoading} />
          ) : (
            <div className="flex h-[400px] items-center justify-center text-muted-foreground">Sem dados para o gráfico de barras.</div>
          )}
        </div>

        <div className="mt-8 pt-6 border-t">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
              <div className="space-y-1">
                  <DashboardCardTitle className="text-base font-medium">
                    Desempenho Unificado (Estado x Ano)
                  </DashboardCardTitle>
                  <p className="text-sm text-muted-foreground">
                    Matriz de calor das médias por estado.
                  </p>
              </div>
              <div className="min-w-[250px]">
                  <select
                      value={selectedMetric} 
                      onChange={(e) => setSelectedMetric(e.target.value as MetricKey)}
                      className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  >
                      {METRICS.map(m => (
                          <option key={m.key} value={m.key}>{m.label}</option>
                      ))}
                  </select>
              </div>
          </div>
          
          {/* BOTTOM CHART: HEATMAP */}
          <div className="w-full">
              {heatmapData.length > 0 ? (
                  <EditorialHeatmap data={heatmapData} />
              ) : (
                  <div className="flex h-[600px] items-center justify-center text-muted-foreground">Sem dados para o heatmap.</div>
              )}
          </div>
        </div>
      </DashboardCardContent>
    </DashboardCard>
  );
}