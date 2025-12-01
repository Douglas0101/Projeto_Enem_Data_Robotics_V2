import React, { useLayoutEffect, useRef, useState, useMemo, useEffect } from "react";
import * as am5 from "@amcharts/amcharts5";
import * as am5map from "@amcharts/amcharts5/map";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import am5geodata_brazilLow from "@amcharts/amcharts5-geodata/brazilLow";

import { TbNotasGeoUfRow } from "../types/dashboard";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle
} from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";
import { useFilters } from "../context/FilterContext";

interface Props {
  data: TbNotasGeoUfRow[];
  isLoading: boolean;
  year: number;
}

const METRICS = [
  { key: "NOTA_MATEMATICA_mean", label: "Matemática" },
  { key: "NOTA_CIENCIAS_NATUREZA_mean", label: "Ciências da Natureza" },
  { key: "NOTA_CIENCIAS_HUMANAS_mean", label: "Ciências Humanas" },
  { key: "NOTA_LINGUAGENS_CODIGOS_mean", label: "Linguagens e Códigos" },
  { key: "NOTA_REDACAO_mean", label: "Redação" },
] as const;

type MetricKey = (typeof METRICS)[number]["key"];

const getMetricLabel = (key: MetricKey) =>
  METRICS.find((m) => m.key === key)?.label ?? "Média";

export default function NotasAmMap({ data, isLoading, year }: Props) {
  const { uf, setUf } = useFilters();
  const chartRef = useRef<HTMLDivElement>(null);
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>("NOTA_MATEMATICA_mean");
  const rootRef = useRef<am5.Root | null>(null);
  const metricLabelRef = useRef<string>(getMetricLabel("NOTA_MATEMATICA_mean"));

  // Process data to match amCharts format { id: "BR-SP", value: 500 }
  const mapData = useMemo(() => {
    if (!data) return [];
    
    return data
      .map((row) => {
        const rawValue = (row as any)[selectedMetric];
        const value = rawValue == null ? NaN : Number(rawValue);
        return {
          id: `BR-${row.SG_UF_PROVA}`,
          value,
          // Ensure 'name' property exists implicitly from GeoJSON or map it here if necessary. 
          // amCharts automatically merges data with geoJSON properties by ID.
          info: row,
        };
      })
      .filter((d) => !Number.isNaN(d.value));
  }, [data, selectedMetric]);

  useLayoutEffect(() => {
    if (!chartRef.current) return;

    const root = am5.Root.new(chartRef.current);
    rootRef.current = root;

    root.setThemes([am5themes_Animated.new(root)]);
    root.numberFormatter.set("numberFormat", "#,###.0");
    (root as any)._logo?.dispose();

    const chart = root.container.children.push(
      am5map.MapChart.new(root, {
        panX: "rotateX",
        panY: "rotateY",
        projection: am5map.geoMercator(),
        layout: root.horizontalLayout
      })
    );

    // Create polygon series
    const polygonSeries = chart.series.push(
      am5map.MapPolygonSeries.new(root, {
        geoJSON: am5geodata_brazilLow,
        valueField: "value",
        calculateAggregates: true
      })
    );

    polygonSeries.mapPolygons.template.setAll({
      tooltipText: "[bold]{name}[/]\n{value.formatNumber('#.0')}",
    });

    polygonSeries.set("heatRules", [{
      target: polygonSeries.mapPolygons.template,
      dataField: "value",
      min: am5.color(0xe0f2fe),
      max: am5.color(0x0c4a6e),
      key: "fill"
    }]);

    polygonSeries.mapPolygons.template.events.on("click", function(ev) {
      const dataItem = ev.target.dataItem;
      if (dataItem) {
        const id = (dataItem.dataContext as any).id; 
        if (id) {
            const ufCode = id.replace("BR-", "");
            setUf(ufCode);
        }
      }
    });

    polygonSeries.mapPolygons.template.states.create("hover", {
      fill: am5.color(0x297373)
    });

    const heatLegend = chart.children.push(
      am5.HeatLegend.new(root, {
        orientation: "vertical",
        startColor: am5.color(0xe0f2fe),
        endColor: am5.color(0x0c4a6e),
        startText: "Menor",
        endText: "Maior",
        stepCount: 5
      })
    );

    heatLegend.startLabel.setAll({
      fontSize: 12,
      fill: heatLegend.get("startColor")
    });

    heatLegend.endLabel.setAll({
      fontSize: 12,
      fill: heatLegend.get("endColor")
    });

    // change this to template event, because if we use "pointerover" on series
    // it will not trigger for polygons that are not visible
    polygonSeries.mapPolygons.template.events.on("pointerover", function (ev) {
      const di = ev.target.dataItem;
      if (di) {
         const value = di.get("value");
         if (typeof value === "number") {
           heatLegend.showValue(value);
         }
      }
    });

    polygonSeries.events.on("datavalidated", function () {
      heatLegend.set("startValue", polygonSeries.getPrivate("valueLow"));
      heatLegend.set("endValue", polygonSeries.getPrivate("valueHigh"));
    });

    // Initial Data Load
    if (mapData.length > 0) {
        polygonSeries.data.setAll(mapData);
    }

    // Cleanup
    return () => {
      root.dispose();
    };
  }, []); // Empty dependency array to mount once, we update data via separate effect if needed or key

  // Effect to update data when props change
  useEffect(() => {
    if (!rootRef.current) return;
    const chart = rootRef.current.container.children.getIndex(0) as am5map.MapChart;
    if (!chart) return;
    const series = chart.series.getIndex(0) as am5map.MapPolygonSeries;
    if (series) {
        series.data.setAll(mapData);
        
        // Update Tooltip format dynamically if metric changes
        metricLabelRef.current = getMetricLabel(selectedMetric);
        series.mapPolygons.template.set("tooltipText", `[bold]{name}[/]\n${metricLabelRef.current}: {value.formatNumber('#.0')}`);
        series.mapPolygons.each((polygon) => {
             polygon.set("tooltipText", `[bold]{name}[/]\n${metricLabelRef.current}: {value.formatNumber('#.0')}`);
        })
    }
  }, [mapData, selectedMetric]);


  return (
    <DashboardCard className="h-full">
      <DashboardCardHeader className="flex flex-wrap items-start md:items-center gap-4 pb-4">
        <div className="space-y-1">
          <DashboardCardTitle className="text-base font-medium">
            Mapa de Calor - Desempenho Regional ({year})
          </DashboardCardTitle>
          <p className="text-sm text-muted-foreground">
            Distribuição geográfica das médias por estado (Heatmap).
          </p>
        </div>
        <div className="min-w-[220px]">
          <select
            className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
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
      <DashboardCardContent className="p-0 relative">
        {isLoading ? (
             <div className="flex h-[760px] items-center justify-center">
                <Skeleton className="h-full w-full rounded-md opacity-20" />
             </div>
        ) : (
            <div ref={chartRef} className="w-full h-[720px]" />
        )}
        
        {uf !== 'all' && (
            <div className="absolute top-4 right-4 bg-white/90 p-2 rounded shadow text-xs font-bold border border-blue-200 text-blue-800">
                Filtro Ativo: {uf}
            </div>
        )}
      </DashboardCardContent>
    </DashboardCard>
  );
}
