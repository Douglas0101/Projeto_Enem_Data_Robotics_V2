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
  INSCRITOS?: number; // Added INSCRITOS for the histogram
}

interface Props {
  data: HistoryDataRow[];
  isLoading: boolean;
  entityName: string;
}

export function VerticallyStackedAxesChart({ data, isLoading, entityName }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<am5.Root | null>(null);

  useLayoutEffect(() => {
    if (isLoading || !chartRef.current) return;

    // Clean up previous instance if any
    if (rootRef.current) {
      rootRef.current.dispose();
    }

    const root = am5.Root.new(chartRef.current);
    rootRef.current = root;

    root.setThemes([am5themes_Animated.new(root)]);
    (root as any)._logo?.dispose();

    // Localize number formatting (pt-BR) so thousands/decimals match tooltips
    root.numberFormatter.setAll({ numberFormat: "#,###.##", intlLocales: "pt-BR" });

    // Process data: Sort by year and convert to strings for category axis
    const processedData = [...data]
      .sort((a, b) => a.ANO - b.ANO)
      .map(d => ({
      ...d,
      ANO: String(d.ANO)
    }));

    // Axis height distribution (percent of chart height) to give the histogram more room
    const disciplineAxisHeight = 14;
    const histogramAxisHeight = 30;

    // --- Chart Logic based on amCharts Demo ---
    
    var chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: true,
        panY: false,
        wheelX: "none", // Keeping as per demo
        wheelY: "zoomX", // Adjusted for standard behavior or "true" if it works, but zoomX is safer for TS
        arrangeTooltips: false,
        pinchZoomX: true
      })
    );

    // make y axes stack
    chart.leftAxesContainer.set("layout", root.verticalLayout);

    // Create X-Axis
    var xRenderer = am5xy.AxisRendererX.new(root, {
      minGridDistance: 70
    });
    xRenderer.labels.template.setAll({
      multiLocation: 0.5,
      location: 0.5,
      centerY: am5.p50,
      centerX: am5.p50,
      paddingTop: 10
    });
    xRenderer.grid.template.set("location", 0.5);

    var xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(root, {
        categoryField: "ANO",
        renderer: xRenderer
      })
    );
    xAxis.data.setAll(processedData);

    // Function to create stacked series
    function createSeries(field: keyof HistoryDataRow, name: string, margin: number, column: boolean, colorHex: number, minMax?: { min?: number, max?: number }) {
      const axisHeight = field === "INSCRITOS" ? histogramAxisHeight : disciplineAxisHeight;

      var yAxis = chart.yAxes.push(
        am5xy.ValueAxis.new(root, {
          renderer: am5xy.AxisRendererY.new(root, {}),
          x: am5.p100,
          centerX: am5.p100,
          marginTop: margin,
          min: minMax?.min,
          max: minMax?.max,
          height: am5.percent(axisHeight)
        })
      );

      var series;
      var color = am5.color(colorHex);

      let tooltipLabelText;
      if (field === "INSCRITOS") {
        tooltipLabelText = "Total de {name}: {valueY.formatNumber('#,###')}"; // Thousands separator, no decimals
      } else {
        tooltipLabelText = "{name}: {valueY.formatNumber('#,###.0')}"; // One decimal with localized separators
      }

      const seriesTooltip = am5.Tooltip.new(root, {
        pointerOrientation: "vertical",
        labelText: tooltipLabelText
      });

      seriesTooltip.get("background")?.setAll({
        fill: am5.color(0xffffff), // Force White Background
        fillOpacity: 0.9,
        stroke: am5.color(colorHex), // Colored Border
        strokeWidth: 2,
        strokeOpacity: 1
      });

      // Force tooltip text to stay black even when themes try to recolor labels
      const tooltipTextColor = am5.color(0x000000);
      seriesTooltip.label.setAll({ fill: tooltipTextColor, stroke: tooltipTextColor });
      seriesTooltip.label.adapters.add("fill", () => tooltipTextColor);
      seriesTooltip.label.adapters.add("stroke", () => tooltipTextColor);

      if (column) {
        series = chart.series.push(
          am5xy.ColumnSeries.new(root, {
            name: name,
            xAxis: xAxis,
            yAxis: yAxis,
            valueYField: field,
            categoryXField: "ANO",
            sequencedInterpolation: true,
            tooltip: seriesTooltip,
            fill: color,
            stroke: color
          })
        );
      } else {
        series = chart.series.push(
          am5xy.LineSeries.new(root, {
            name: name,
            xAxis: xAxis,
            yAxis: yAxis,
            valueYField: field,
            categoryXField: "ANO",
            sequencedInterpolation: true,
            tooltip: seriesTooltip,
            stroke: color
          })
        );
      }

      if (!column) {
        series.bullets.push(function() {
          return am5.Bullet.new(root, {
            locationY: 1,
            locationX: 0.5,
            sprite: am5.Circle.new(root, {
              radius: 4,
              fill: series.get("fill"),
              stroke: root.interfaceColors.get("background"),
              strokeWidth: 2
            })
          });
        });
      }

      series.data.setAll(processedData);
      series.appear();

      return series;
    }

    // Instantiate the series and their respective stacked axes
    // Disciplines (Lines, 0-1000 scale)
    // Using a base margin of 0 for all discipline axes to keep them close,
    // and a larger margin for INSCRITOS to separate it clearly.
    // Colors are from TailwindCSS default palette or similar.
    createSeries("NOTA_MATEMATICA_mean", "Matemática", 0, false, 0x3b82f6, { min: 0, max: 1000 }); // blue
    createSeries("NOTA_CIENCIAS_NATUREZA_mean", "Ciências da Natureza", 0, false, 0x22c55e, { min: 0, max: 1000 }); // green
    createSeries("NOTA_CIENCIAS_HUMANAS_mean", "Ciências Humanas", 0, false, 0xf97316, { min: 0, max: 1000 }); // orange
    createSeries("NOTA_LINGUAGENS_CODIGOS_mean", "Linguagens e Códigos", 0, false, 0xa855f7, { min: 0, max: 1000 }); // purple
    createSeries("NOTA_REDACAO_mean", "Redação", 0, false, 0xef4444, { min: 0, max: 1000 }); // red

    // Inscritos (Column/Histogram, auto-scaled, distinct margin)
    // This series will appear at the bottom of the chart due to the larger margin.
    createSeries("INSCRITOS", "Inscritos", 60, true, 0x6b7280); // gray

    // Add cursor
    var cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
      behavior: "none",
      xAxis: xAxis
    }));

    // show x Axis label next to the panel on which cursor currently is
    xAxis.set("layer", 50);

    // The interactive label movement logic from the demo
    cursor.events.on("cursormoved", function() {
      var position = cursor.getPrivate("positionY");
      if (typeof position !== 'number') return;

      var axisIndex = Math.floor(chart.yAxes.length * position);
      // Clamp index
      if (axisIndex < 0) axisIndex = 0;
      if (axisIndex >= chart.yAxes.length) axisIndex = chart.yAxes.length - 1;

      var axis = chart.yAxes.getIndex(axisIndex);

      if (axis) {
        var y = axis.y() + axis.height();
        var dy = Math.round(-(chart.plotContainer.height() - y));

        var tooltip = xAxis.get("tooltip");

        // We cast to any because "dy" might not be exposed on the public type interface for direct get() in strictly typed versions, 
        // but it works in the demo.
        if(Math.round((xAxis as any).get("dy") || 0) != dy){
          xAxis.animate({ key: "dy", to: dy, duration: 600, easing: am5.ease.out(am5.ease.cubic) });
          xAxis.set("y", 0);
          if(tooltip){
             tooltip.hide(0);
          }
        }
        else{
          if (tooltip) tooltip.show(300);
        }
      }
    });

    chart.appear(1000, 100);

    return () => {
      root.dispose();
    };
  }, [data, isLoading]);

  if (isLoading) {
    return (
        <DashboardCard>
          <DashboardCardContent>
            <div className="w-full h-[600px]">
              <Skeleton className="h-full w-full rounded-md" />
            </div>
          </DashboardCardContent>
        </DashboardCard>
    );
  }

  return (
    <DashboardCard>
      <DashboardCardHeader>
        <DashboardCardTitle>Evolução Comparativa (Eixos Empilhados): {entityName}</DashboardCardTitle>
        <p className="text-sm text-muted-foreground">
          Visualização interativa com eixos verticais independentes para as 5 disciplinas e o número de inscritos (histograma).
        </p>
      </DashboardCardHeader>
      <DashboardCardContent>
        <div ref={chartRef} className="w-full h-[600px]" />
      </DashboardCardContent>
    </DashboardCard>
  );
}
