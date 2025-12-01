import { useLayoutEffect, useRef } from "react";
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle,
} from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";

interface HistoryDataRow {
  ANO: number;
  NOTA_MATEMATICA_mean: number | null;
  NOTA_CIENCIAS_NATUREZA_mean: number | null;
  NOTA_CIENCIAS_HUMANAS_mean: number | null;
  NOTA_LINGUAGENS_CODIGOS_mean: number | null;
  NOTA_REDACAO_mean: number | null;
}

interface Props {
  data: HistoryDataRow[];
  isLoading: boolean;
  entityName: string; // "Brasil" or "São Paulo", etc.
}

export function StateHistoryChart({ data, isLoading, entityName }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<am5.Root | null>(null);
  const xAxisRef = useRef<am5xy.CategoryAxis<am5xy.AxisRenderer> | null>(null);
  const seriesRef = useRef<{ [key: string]: am5xy.LineSeries }>({});

  // 1. Initialization Effect (Runs ONCE)
  useLayoutEffect(() => {
    if (isLoading || !chartRef.current) return;

    // Create root
    const root = am5.Root.new(chartRef.current);
    rootRef.current = root;
    
    root.setThemes([am5themes_Animated.new(root)]);
    (root as any)._logo?.dispose();

    // Localize number formatting for tooltips/values
    root.numberFormatter.setAll({ numberFormat: "#,###.0", intlLocales: "pt-BR" });

    // Create chart
    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: true,
        panY: true,
        wheelX: "panX",
        wheelY: "zoomX",
        pinchZoomX: true,
        paddingLeft: 0,
        arrangeTooltips: true // Prevent tooltip overlap
      })
    );

    chart.get("colors")?.set("step", 2);

    // Add Legend
    const legend = root.container.children.push(
      am5.Legend.new(root, {
        centerX: am5.p50,
        x: am5.p50,
        marginBottom: 15,
        layout: root.gridLayout
      })
    );
    legend.valueLabels.template.set("width", 120);

    // X Axis - Years (Category)
    const xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(root, {
        categoryField: "ANO",
        renderer: am5xy.AxisRendererX.new(root, {
          minorGridEnabled: true,
          minGridDistance: 70
        }),
        tooltip: am5.Tooltip.new(root, {})
      })
    );
    xAxisRef.current = xAxis;

    // Add cursor (Must be after xAxis)
    const cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
      behavior: "none",
      xAxis: xAxis
    }));
    cursor.lineY.set("visible", false);

    // Y Axis - Score (0-1000)
    const yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        min: 0,
        max: 1000,
        strictMinMax: true,
        renderer: am5xy.AxisRendererY.new(root, {
          pan: "zoom"
        })
      })
    );

    // Helper to create series
    const createSeries = (name: string, field: keyof HistoryDataRow, colorHex: number, key: string) => {
      const color = am5.color(colorHex);
      // Styled Tooltip
      const tooltip = am5.Tooltip.new(root, {
        pointerOrientation: "horizontal",
        labelText: "[bold]{name}[/]: {valueY.formatNumber('#,###.0')}"
      });

      tooltip.get("background")?.setAll({
        fill: am5.color(0xffffff),
        fillOpacity: 0.9,
        stroke: color, // Border matches series color
        strokeWidth: 2,
        strokeOpacity: 1
      });

      const tooltipTextColor = am5.color(0x000000);
      tooltip.label.setAll({ fill: tooltipTextColor, stroke: tooltipTextColor });
      tooltip.label.adapters.add("fill", () => tooltipTextColor);
      tooltip.label.adapters.add("stroke", () => tooltipTextColor);

      const series = chart.series.push(
        am5xy.LineSeries.new(root, {
          name: name,
          xAxis: xAxis,
          yAxis: yAxis,
          valueYField: field,
          categoryXField: "ANO",
          stroke: color,
          tooltip: tooltip,
          connect: false,
          legendValueText: "{valueY}"
        })
      );

      series.strokes.template.setAll({ strokeWidth: 2 });

      // Add bullets
      series.bullets.push(() => {
        return am5.Bullet.new(root, {
          sprite: am5.Circle.new(root, {
            radius: 4,
            fill: series.get("stroke"),
            stroke: root.interfaceColors.get("background"),
            strokeWidth: 2
          })
        });
      });

      series.appear(1000);
      legend.data.push(series);
      seriesRef.current[key] = series;
    };

    createSeries("Matemática", "NOTA_MATEMATICA_mean", 0x3b82f6, "mat");
    createSeries("Ciências da Natureza", "NOTA_CIENCIAS_NATUREZA_mean", 0x22c55e, "nat");
    createSeries("Ciências Humanas", "NOTA_CIENCIAS_HUMANAS_mean", 0xf97316, "hum");
    createSeries("Linguagens", "NOTA_LINGUAGENS_CODIGOS_mean", 0xa855f7, "lin");
    createSeries("Redação", "NOTA_REDACAO_mean", 0xef4444, "red");

    // Scrollbar
    chart.set("scrollbarX", am5.Scrollbar.new(root, {
      orientation: "horizontal"
    }));

    chart.appear(1000, 100);

    return () => {
      root.dispose();
      rootRef.current = null;
    };
  }, [isLoading]);

  // 2. Data Update Effect (Runs when data changes)
  useLayoutEffect(() => {
    if (isLoading || !rootRef.current || !xAxisRef.current) return;

    // Data Sanitization & Deduplication
    const uniqueDataMap = new Map();
    data.forEach((d) => {
      const year = String(d.ANO);
      // Keep the last entry for a year if duplicates exist (or merge if needed)
      uniqueDataMap.set(year, {
        ...d,
        ANO: year,
        NOTA_MATEMATICA_mean: d.NOTA_MATEMATICA_mean ?? null,
        NOTA_CIENCIAS_NATUREZA_mean: d.NOTA_CIENCIAS_NATUREZA_mean ?? null,
        NOTA_CIENCIAS_HUMANAS_mean: d.NOTA_CIENCIAS_HUMANAS_mean ?? null,
        NOTA_LINGUAGENS_CODIGOS_mean: d.NOTA_LINGUAGENS_CODIGOS_mean ?? null,
        NOTA_REDACAO_mean: d.NOTA_REDACAO_mean ?? null,
      });
    });

    const processedData = Array.from(uniqueDataMap.values())
      .sort((a, b) => parseInt(a.ANO) - parseInt(b.ANO));

    // Update Axis Data
    xAxisRef.current.data.setAll(processedData);

    // Update Series Data
    Object.values(seriesRef.current).forEach((series) => {
      series.data.setAll(processedData);
    });

  }, [data, isLoading]); // Run when data updates

  if (isLoading) {
    return (
      <DashboardCard>
        <DashboardCardContent>
          <div className="w-full h-[500px]">
            <Skeleton className="h-full w-full rounded-md" />
          </div>
        </DashboardCardContent>
      </DashboardCard>
    );
  }

  return (
    <DashboardCard>
      <DashboardCardHeader>
        <DashboardCardTitle>Evolução Histórica: {entityName}</DashboardCardTitle>
        <p className="text-sm text-muted-foreground">
          Performance média nas 5 áreas de conhecimento ao longo dos anos.
        </p>
      </DashboardCardHeader>
      <DashboardCardContent>
        <div ref={chartRef} className="w-full h-[500px]" />
      </DashboardCardContent>
    </DashboardCard>
  );
}
