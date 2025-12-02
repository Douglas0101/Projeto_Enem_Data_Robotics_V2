import React, { useLayoutEffect, useRef } from 'react';
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface ChartData {
  ano: number;
  inscritos: number;
  provas: number;
  natureza: number;
  humanas: number;
  linguagens: number;
  matematica: number;
  redacao: number;
}

interface MunicipalityMixedChartProps {
  data: ChartData[];
  title?: string;
}

export function MunicipalityMixedChart({ data, title }: MunicipalityMixedChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const root = am5.Root.new(chartRef.current!);

    root.setThemes([
      am5themes_Animated.new(root)
    ]);
    
    (root as any)._logo?.dispose();

    const chart = root.container.children.push(am5xy.XYChart.new(root, {
      panX: false,
      panY: false,
      wheelX: "panX",
      wheelY: "zoomX",
      layout: root.verticalLayout
    }));

    // Add cursor
    const cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
      behavior: "zoomX"
    }));
    cursor.lineY.set("visible", false);

    // Create axes
    // X Axis (Years)
    const xRenderer = am5xy.AxisRendererX.new(root, {
      minGridDistance: 30,
      cellStartLocation: 0.1,
      cellEndLocation: 0.9
    });

    xRenderer.labels.template.setAll({
      centerX: am5.p50,
      textAlign: "center"
    });

    const xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {
      categoryField: "ano",
      renderer: xRenderer,
      tooltip: am5.Tooltip.new(root, {})
    }));

    // Sort data by year just in case
    const sortedData = [...data].sort((a, b) => a.ano - b.ano).map(d => ({...d, ano: String(d.ano)}));
    xAxis.data.setAll(sortedData);

    // Y Axis 1 (Averages - Left)
    const yAxis1 = chart.yAxes.push(am5xy.ValueAxis.new(root, {
      renderer: am5xy.AxisRendererY.new(root, {})
    }));

    // Y Axis 2 (Volume - Right)
    const yAxis2 = chart.yAxes.push(am5xy.ValueAxis.new(root, {
      renderer: am5xy.AxisRendererY.new(root, {
        opposite: true
      })
    }));

    // Series 0: Inscritos (Column) - Total Registrations
    const seriesInscritos = chart.series.push(am5xy.ColumnSeries.new(root, {
      name: "Inscritos (Total)",
      xAxis: xAxis,
      yAxis: yAxis2,
      valueYField: "inscritos",
      categoryXField: "ano",
      tooltip: am5.Tooltip.new(root, {
        labelText: "{name}: {valueY}"
      })
    }));

    seriesInscritos.columns.template.setAll({
      fillOpacity: 0.3, // Lighter to distinguish
      strokeWidth: 0,
      cornerRadiusTL: 5,
      cornerRadiusTR: 5,
      fill: am5.color(0x9ca3af) // Grayish
    });

    seriesInscritos.data.setAll(sortedData);

    // Series 1: Provas (Column) - Actual Attendees
    const seriesProvas = chart.series.push(am5xy.ColumnSeries.new(root, {
      name: "Provas (Qtd)",
      xAxis: xAxis,
      yAxis: yAxis2,
      valueYField: "provas",
      categoryXField: "ano",
      tooltip: am5.Tooltip.new(root, {
        labelText: "{name}: {valueY}"
      })
    }));

    seriesProvas.columns.template.setAll({
      fillOpacity: 0.8,
      strokeWidth: 0,
      cornerRadiusTL: 5,
      cornerRadiusTR: 5,
      fill: am5.color(0x10b981) // Emerald
    });

    seriesProvas.data.setAll(sortedData);

      // Helper to create line series
    const createLineSeries = (name: string, field: string, color: string) => {
      const series = chart.series.push(am5xy.LineSeries.new(root, {
        name: name,
        xAxis: xAxis,
        yAxis: yAxis1,
        valueYField: field,
        categoryXField: "ano",
        stroke: am5.color(color),
        tooltip: am5.Tooltip.new(root, {
          labelText: "{name}: {valueY.formatNumber('#.0')}"
        })
      }));

      series.strokes.template.setAll({
        strokeWidth: 2
      });

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

      series.data.setAll(sortedData);
    };

    createLineSeries("Matemática", "matematica", "#ef4444"); // Red
    createLineSeries("Redação", "redacao", "#f97316"); // Orange
    createLineSeries("Ciências Natureza", "natureza", "#22c55e"); // Green
    createLineSeries("Ciências Humanas", "humanas", "#a855f7"); // Purple
    createLineSeries("Linguagens", "linguagens", "#3b82f6"); // Blue

    // Add legend
    const legend = chart.children.push(am5.Legend.new(root, {
      centerX: am5.p50,
      x: am5.p50
    }));
    legend.data.setAll(chart.series.values);

    return () => {
      root.dispose();
    };
  }, [data]);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>{title || "Desempenho Municipal"}</CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={chartRef} style={{ width: "100%", height: "500px" }}></div>
      </CardContent>
    </Card>
  );
}
