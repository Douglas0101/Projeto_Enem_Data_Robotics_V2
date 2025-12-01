import { useLayoutEffect, useRef } from "react";
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import { TbNotasGeoUfRow } from "../types/dashboard";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle,
} from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";

interface Props {
  data: TbNotasGeoUfRow[];
  isLoading: boolean;
  onStateClick?: (uf: string) => void;
  selectedUf?: string;
}

export function StatePerformanceChart({ data, isLoading, onStateClick, selectedUf }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!chartRef.current || isLoading || data.length === 0) return;

    // Create root element
    const root = am5.Root.new(chartRef.current);

    // Set themes
    root.setThemes([am5themes_Animated.new(root)]);
    
    // Hide watermark as requested
    (root as any)._logo?.dispose();

    // --- Data Processing ---
    // ... (keep aggregation logic same as before)
    const aggregatedData = data.reduce((acc, row) => {
      const uf = row.SG_UF_PROVA;
      if (!uf) return acc;

      if (!acc[uf]) {
        acc[uf] = {
          uf,
          totalInscritos: 0,
          wMat: 0, weightMat: 0,
          wNat: 0, weightNat: 0,
          wHum: 0, weightHum: 0,
          wLin: 0, weightLin: 0,
          wRed: 0, weightRed: 0,
        };
      }

      const inscritos = row.INSCRITOS ?? 0;
      acc[uf].totalInscritos += inscritos;

      const add = (keySum: keyof typeof acc[typeof uf], keyWeight: keyof typeof acc[typeof uf], val: number | null | undefined) => {
        if (val != null) {
          (acc[uf][keySum] as number) += val * inscritos;
          (acc[uf][keyWeight] as number) += inscritos;
        }
      };

      add("wMat", "weightMat", row.NOTA_MATEMATICA_mean);
      add("wNat", "weightNat", row.NOTA_CIENCIAS_NATUREZA_mean);
      add("wHum", "weightHum", row.NOTA_CIENCIAS_HUMANAS_mean);
      add("wLin", "weightLin", row.NOTA_LINGUAGENS_CODIGOS_mean);
      add("wRed", "weightRed", row.NOTA_REDACAO_mean);

      return acc;
    }, {} as Record<string, any>);

    const chartData = Object.values(aggregatedData).map((item: any) => {
      const calc = (sum: number, w: number) => w > 0 ? parseFloat((sum / w).toFixed(1)) : 0;
      return {
        uf: item.uf,
        inscritos: item.totalInscritos,
        mat: calc(item.wMat, item.weightMat),
        nat: calc(item.wNat, item.weightNat),
        hum: calc(item.wHum, item.weightHum),
        lin: calc(item.wLin, item.weightLin),
        red: calc(item.wRed, item.weightRed),
      };
    }).sort((a: any, b: any) => b.inscritos - a.inscritos);

    // Create chart
    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: false,
        panY: false,
        wheelX: "panX",
        wheelY: "zoomX",
        layout: root.verticalLayout
      })
    );

    const cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
      behavior: "zoomX"
    }));
    cursor.lineY.set("visible", false);

    const xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(root, {
        categoryField: "uf",
        renderer: am5xy.AxisRendererX.new(root, {
          minGridDistance: 15,
          cellStartLocation: 0.1,
          cellEndLocation: 0.9
        }),
        tooltip: am5.Tooltip.new(root, {})
      })
    );

    xAxis.get("renderer").labels.template.setAll({
      fontWeight: "bold",
      rotation: 0,
      centerY: am5.p50,
      centerX: am5.p50,
      location: 0.5,
      oversizedBehavior: "none"
    });

    xAxis.data.setAll(chartData);

    const yAxisVolume = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        renderer: am5xy.AxisRendererY.new(root, {
          pan: "zoom"
        })
      })
    );

    yAxisVolume.get("renderer").labels.template.setAll({
      fill: am5.color(0x10b981)
    });

    const yAxisQuality = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        min: 0, // Fixed: 2009 has averages below 300 (e.g. Redacao ~257), so 300 breaks the chart. 0 is safe.
        max: 1000,
        strictMinMax: true,
        renderer: am5xy.AxisRendererY.new(root, {
          opposite: true,
          pan: "zoom"
        })
      })
    );

    yAxisQuality.get("renderer").labels.template.setAll({
      fill: am5.color(0x64748b)
    });

    // 0. Volume (Columns)
    const seriesVolume = chart.series.push(
      am5xy.ColumnSeries.new(root, {
        name: "Inscritos",
        xAxis: xAxis,
        yAxis: yAxisVolume,
        valueYField: "inscritos",
        categoryXField: "uf",
        tooltip: am5.Tooltip.new(root, {
          labelText: "{categoryX}: {valueY} inscritos"
        })
      })
    );

    seriesVolume.columns.template.setAll({
      cornerRadiusTL: 5,
      cornerRadiusTR: 5,
      strokeOpacity: 0,
      fillOpacity: 0.8,
      fill: am5.color(0x10b981),
      cursorOverStyle: "pointer"
    });

    // --- Visual Highlight Logic ---
    seriesVolume.columns.template.adapters.add("fill", (fill, target) => {
      if (!selectedUf || selectedUf === "all") {
        return fill;
      }
      const dataItem = target.dataItem;
      if (dataItem && dataItem.get("categoryX") === selectedUf) {
        return am5.color(0x10b981); // Active: Emerald
      }
      return am5.color(0xcbd5e1); // Inactive: Slate-300 (Gray)
    });

    seriesVolume.columns.template.adapters.add("fillOpacity", (opacity, target) => {
      if (!selectedUf || selectedUf === "all") {
        return 0.8;
      }
      const dataItem = target.dataItem;
      if (dataItem && dataItem.get("categoryX") === selectedUf) {
        return 1; // Active: Full opacity
      }
      return 0.3; // Inactive: Low opacity
    });
    // -----------------------------

    seriesVolume.columns.template.events.on("click", (ev) => {
      const uf = ev.target.dataItem?.get("categoryX");
      if (uf && onStateClick) {
        onStateClick(uf as string);
      }
    });

    const createLineSeries = (name: string, field: string, colorHex: number) => {
      const series = chart.series.push(
        am5xy.LineSeries.new(root, {
          name: name,
          xAxis: xAxis,
          yAxis: yAxisQuality,
          valueYField: field,
          categoryXField: "uf",
          stroke: am5.color(colorHex),
          tooltip: am5.Tooltip.new(root, {
            labelText: `${name}: {valueY}`
          })
        })
      );

      // Dim lines if a specific state is selected (optional, but helps focus)
      // Actually, let's keep lines fully visible to compare the selected state vs others contextually
      
      series.strokes.template.setAll({
        strokeWidth: 2,
        stroke: am5.color(colorHex)
      });

      series.bullets.push(function () {
        return am5.Bullet.new(root, {
          sprite: am5.Circle.new(root, {
            radius: 3.5,
            fill: am5.color(colorHex),
            stroke: root.interfaceColors.get("background"),
            strokeWidth: 1
          })
        });
      });
      
      series.data.setAll(chartData);
      series.appear(1000);
    };

    createLineSeries("Matemática", "mat", 0x3b82f6);
    createLineSeries("Ciências Natureza", "nat", 0x22c55e);
    createLineSeries("Ciências Humanas", "hum", 0xf97316);
    createLineSeries("Linguagens", "lin", 0xa855f7);
    createLineSeries("Redação", "red", 0xef4444);

    chart.set("scrollbarX", am5.Scrollbar.new(root, {
      orientation: "horizontal",
      marginBottom: 20
    }));

    const legend = chart.children.push(
      am5.Legend.new(root, {
        centerX: am5.p50,
        x: am5.p50,
        y: 0,
        centerY: am5.p100,
        paddingTop: 10,
        layout: root.gridLayout
      })
    );
    
    legend.data.setAll(chart.series.values);

    seriesVolume.data.setAll(chartData);
    seriesVolume.appear(1000);
    chart.appear(1000, 100);

    return () => {
      root.dispose();
    };
  }, [data, isLoading, onStateClick, selectedUf]); // Added selectedUf dependency

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
        <DashboardCardTitle>Volume de Inscritos vs Qualidade (Por Disciplina)</DashboardCardTitle>
        <p className="text-sm text-muted-foreground">
          Relação entre volume de participantes e desempenho médio nas 5 áreas de conhecimento.
        </p>
      </DashboardCardHeader>
      <DashboardCardContent>
        <div ref={chartRef} className="w-full h-[500px]" />
      </DashboardCardContent>
    </DashboardCard>
  );
}
