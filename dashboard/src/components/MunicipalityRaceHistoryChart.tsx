import React, { useLayoutEffect, useRef, useState, useMemo } from "react";
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";

export interface RaceHistoryData {
  year: number;
  race: string;
  grades: {
    media_geral: number;
    matematica: number;
    redacao: number;
    linguagens: number;
    humanas: number;
    natureza: number;
  };
}

interface MunicipalityRaceHistoryChartProps {
  data: RaceHistoryData[];
}

const SUBJECTS = [
  { key: "media_geral", label: "Média Geral" },
  { key: "matematica", label: "Matemática" },
  { key: "redacao", label: "Redação" },
  { key: "linguagens", label: "Linguagens e Códigos" },
  { key: "humanas", label: "Ciências Humanas" },
  { key: "natureza", label: "Ciências da Natureza" },
] as const;

type SubjectKey = typeof SUBJECTS[number]["key"];

export const MunicipalityRaceHistoryChart: React.FC<MunicipalityRaceHistoryChartProps> = ({ data }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<am5.Root | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<SubjectKey>("media_geral");

  const { chartData, uniqueRaces } = useMemo(() => {
    const racesSet = new Set<string>();
    const dataByYear: Record<string, any> = {};

    data.forEach((item) => {
      const yearKey = String(item.year);
      racesSet.add(item.race);

      if (!dataByYear[yearKey]) {
        dataByYear[yearKey] = { year: yearKey };
      }

      const grade = item.grades[selectedSubject];
      if (grade !== null && grade !== undefined) {
        dataByYear[yearKey][item.race] = grade;
      }
    });

    const sortedData = Object.values(dataByYear).sort((a, b) => 
      parseInt(a.year) - parseInt(b.year)
    );

    return {
      chartData: sortedData,
      uniqueRaces: Array.from(racesSet).sort(),
    };
  }, [data, selectedSubject]);

  useLayoutEffect(() => {
    if (!chartRef.current) return;

    // Dispose any previous root tied to this element to avoid multiple-root errors.
    if (rootRef.current) {
      rootRef.current.dispose();
    }

    const root = am5.Root.new(chartRef.current);
    rootRef.current = root;

    try {
      if (root._logo) {
        root._logo.dispose();
      }

      root.setThemes([am5themes_Animated.new(root)]);

      let chart = root.container.children.push(
        am5xy.XYChart.new(root, {
          panX: true,
          panY: false,
          wheelX: "panX",
          wheelY: "zoomX",
          layout: root.verticalLayout,
          paddingTop: 20,
        })
      );

      // 3. Cursor e Interatividade
      let cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
        behavior: "none", // Apenas hover
      }));
      cursor.lineY.set("visible", false);
      cursor.lineX.set("visible", false);

      // 5. Legenda Premium (Circular e Topo)
      let legend = chart.children.push(
        am5.Legend.new(root, {
          centerX: am5.percent(50),
          x: am5.percent(50),
          marginTop: 0,
          marginBottom: 25,
          clickTarget: "itemContainer",
        })
      );

      legend.markers.template.setAll({
        width: 12,
        height: 12,
      });

      // Transforma o marcador em círculo
      legend.markerRectangles.template.setAll({
        cornerRadiusTL: 50,
        cornerRadiusTR: 50,
        cornerRadiusBL: 50,
        cornerRadiusBR: 50,
      });

      legend.labels.template.setAll({
        fontSize: 12,
        fontWeight: "500",
        fill: am5.color(0x64748b), // Slate 500
      });

      // 2. Limpeza dos Eixos e Grades
      let xAxis = chart.xAxes.push(
        am5xy.CategoryAxis.new(root, {
          categoryField: "year",
          renderer: am5xy.AxisRendererX.new(root, {
            minGridDistance: 30,
            minorGridEnabled: false,
          }),
          tooltip: am5.Tooltip.new(root, {}),
        })
      );

      // Labels do Eixo X
      xAxis.get("renderer").labels.template.setAll({
        fill: am5.color(0x64748b), // Slate 500
        fontSize: 12,
        fontWeight: "500",
        paddingTop: 10,
      });

      // Remove Grid Vertical
      xAxis.get("renderer").grid.template.set("forceHidden", true);

      let yAxis = chart.yAxes.push(
        am5xy.ValueAxis.new(root, {
          min: 0,
          max: 1000,
          renderer: am5xy.AxisRendererY.new(root, {}),
        })
      );

      // Labels do Eixo Y
      yAxis.get("renderer").labels.template.setAll({
        fill: am5.color(0x64748b),
        fontSize: 12,
      });

      // Grid Horizontal (Pontilhado e Sutil)
      yAxis.get("renderer").grid.template.setAll({
        strokeOpacity: 0.08,
        strokeDasharray: [4, 4],
        stroke: am5.color(0x000000),
      });

      xAxis.data.setAll(chartData);

      // Scrollbar estilizada (Minimalista)
      let scrollbar = chart.set(
        "scrollbarX",
        am5.Scrollbar.new(root, {
          orientation: "horizontal",
          marginBottom: 5,
          height: 8,
        })
      );
      scrollbar.startGrip.set("scale", 0.8);
      scrollbar.endGrip.set("scale", 0.8);
      scrollbar.thumb?.setAll({
        fill: am5.color(0xcbd5e1), // Slate 300
        fillOpacity: 0.5,
      });

      // 1. Paleta de Cores Premium
      // Azul Royal, Esmeralda, Laranja Queimado, Roxo Vibrante, Rosa, Ciano Escuro
      const palette = [
        0x3b82f6, // Blue 500
        0x10b981, // Emerald 500
        0xf97316, // Orange 500
        0x8b5cf6, // Violet 500
        0xec4899, // Pink 500
        0x06b6d4, // Cyan 500
      ];

      uniqueRaces.forEach((race, index) => {
        const color = am5.color(palette[index % palette.length]);

        let series = chart.series.push(
          am5xy.ColumnSeries.new(root, {
            name: race,
            xAxis: xAxis,
            yAxis: yAxis,
            valueYField: race,
            categoryXField: "year",
            clustered: true,
            fill: color,
            stroke: color,
          })
        );

        // 1. Estilização das Colunas
        series.columns.template.setAll({
          width: am5.percent(90),
          cornerRadiusTL: 4,
          cornerRadiusTR: 4,
          tooltipY: 0,
          strokeOpacity: 0,
        });

        // 4. Tooltip Melhorado (Escuro)
        let tooltip = am5.Tooltip.new(root, {
          labelText: `[bold]{name}[/] ({categoryX})\n[fontSize: 16px]{valueY.formatNumber("#.0")}[/]`,
        });

        tooltip.get("background")?.setAll({
          fill: am5.color(0x1e293b), // Slate 800
          stroke: am5.color(0xffffff),
          strokeOpacity: 0.1,
          shadowBlur: 8,
          shadowColor: am5.color(0x000000),
          shadowOpacity: 0.3,
          shadowOffsetX: 0,
          shadowOffsetY: 4,
        });

        tooltip.label.setAll({
          fill: am5.color(0xffffff), // White text
          textAlign: "center",
        });

        series.set("tooltip", tooltip);
        series.data.setAll(chartData);
      });

      legend.data.setAll(chart.series.values);

      chart.appear(1000, 100);
    } catch (error) {
      root.dispose();
      rootRef.current = null;
      throw error;
    }

    return () => {
      root.dispose();
      rootRef.current = null;
    };
  }, [chartData, uniqueRaces]);

  return (
    <div className="w-full flex flex-col gap-4 rounded-xl border bg-card text-card-foreground shadow-sm p-6 transition-all duration-300 hover:shadow-md">
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mb-2">
        <div>
          <h3 className="text-lg font-semibold leading-none tracking-tight flex items-center gap-2">
            Evolução Histórica por Raça/Cor
            <span className="inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-primary/10 text-primary hover:bg-primary/20">
              Premium
            </span>
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Análise longitudinal de desempenho por autodeclaração
          </p>
        </div>
        <div className="w-full sm:w-[250px]">
          <select
            className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm ring-offset-background focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={selectedSubject}
            onChange={(e) => setSelectedSubject(e.target.value as SubjectKey)}
          >
            {SUBJECTS.map((sub) => (
              <option key={sub.key} value={sub.key}>
                {sub.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div ref={chartRef} className="w-full h-[500px] relative" />
    </div>
  );
};
