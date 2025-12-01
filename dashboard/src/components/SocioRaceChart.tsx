import { useLayoutEffect, useRef, useState } from "react";
import * as am5 from "@amcharts/amcharts5";
import * as am5percent from "@amcharts/amcharts5/percent";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import { TbSocioRaceRow } from "../api/dashboard";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle,
} from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";

interface Props {
  data: TbSocioRaceRow[];
  isLoading: boolean;
}

const SUBJECTS = [
  { key: "GERAL", label: "Média Geral" },
  { key: "NOTA_MATEMATICA", label: "Matemática" },
  { key: "NOTA_CIENCIAS_NATUREZA", label: "Ciências da Natureza" },
  { key: "NOTA_CIENCIAS_HUMANAS", label: "Ciências Humanas" },
  { key: "NOTA_LINGUAGENS_CODIGOS", label: "Linguagens e Códigos" },
  { key: "NOTA_REDACAO", label: "Redação" },
] as const;

type SubjectKey = (typeof SUBJECTS)[number]["key"];

const SUBJECT_KEYS_CALC = [
  "NOTA_MATEMATICA",
  "NOTA_CIENCIAS_NATUREZA",
  "NOTA_CIENCIAS_HUMANAS",
  "NOTA_LINGUAGENS_CODIGOS",
  "NOTA_REDACAO",
];

export function SocioRaceChart({ data, isLoading }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [selectedSubject, setSelectedSubject] = useState<SubjectKey>("GERAL");

  useLayoutEffect(() => {
    if (!chartRef.current || isLoading || data.length === 0) return;

    const root = am5.Root.new(chartRef.current);
    root.setThemes([am5themes_Animated.new(root)]);
    (root as any)._logo?.dispose();

    const chart = root.container.children.push(
      am5percent.PieChart.new(root, {
        endAngle: 270,
        innerRadius: am5.percent(60),
        layout: root.verticalLayout,
      })
    );

    const series = chart.series.push(
      am5percent.PieSeries.new(root, {
        valueField: "score",
        categoryField: "RACA",
        endAngle: 270,
      })
    );

    series.slices.template.setAll({
      stroke: am5.color(0xffffff),
      strokeWidth: 2,
      strokeOpacity: 1,
    });

    series.states.create("hover", {
      scale: 1.1,
    });

    series.slices.template.events.on("click", (ev) => {
      if (ev.target.dataItem) {
        chart.zoomToDataItem(ev.target.dataItem);
      }
    });

    series.labels.template.setAll({
      radius: 40,
    });

    series.ticks.template.setAll({
      forceHidden: true,
    });

    series.slices.template.set("tooltipText", "{category}: {value.formatNumber('#.#')} ({valuePercentTotal.formatNumber('0.00')}%)");

    // Process Data based on Selection
    const processedData = data.map((item) => {
      let score = 0;
      
      if (selectedSubject === "GERAL") {
        let totalScore = 0;
        let subjectCount = 0;
        SUBJECT_KEYS_CALC.forEach((key) => {
          const val = (item as any)[key];
          if (val !== null && val !== undefined) {
            totalScore += val;
            subjectCount++;
          }
        });
        score = subjectCount > 0 ? totalScore / subjectCount : 0;
      } else {
        // Specific Subject
        score = (item as any)[selectedSubject] ?? 0;
      }

      return {
        RACA: item.RACA,
        score: score,
        COUNT: item.COUNT,
      };
    }).sort((a, b) => b.score - a.score); // Re-sort by score

    series.data.setAll(processedData);

    // Add Legend
    const legend = chart.children.push(am5.Legend.new(root, {
      centerX: am5.percent(50),
      x: am5.percent(50),
      marginTop: 15,
      marginBottom: 15
    }));
    
    legend.data.setAll(series.dataItems);

    series.appear(1000, 100);
    chart.appear(1000, 100);

    return () => {
      root.dispose();
    };
  }, [data, isLoading, selectedSubject]);

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

  if (data.length === 0) {
    return (
      <DashboardCard>
        <DashboardCardHeader>
          <DashboardCardTitle>Desempenho Médio por Cor/Raça</DashboardCardTitle>
          <p className="text-sm text-muted-foreground">
            Comparativo nacional (todos os estados) para o ano selecionado.
          </p>
        </DashboardCardHeader>
        <DashboardCardContent>
          <div className="w-full h-[500px] flex items-center justify-center text-muted-foreground">
            Sem dados disponíveis para o período selecionado.
          </div>
        </DashboardCardContent>
      </DashboardCard>
    );
  }

  return (
    <DashboardCard>
      <DashboardCardHeader>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <DashboardCardTitle>Desempenho Médio por Cor/Raça</DashboardCardTitle>
            <p className="text-sm text-muted-foreground">
              Média {selectedSubject === 'GERAL' ? 'geral' : 'da disciplina'} por autodeclaração (Nacional).
            </p>
          </div>
          
          <div className="min-w-[200px]">
            <select
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value as SubjectKey)}
              className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            >
              {SUBJECTS.map((subj) => (
                <option key={subj.key} value={subj.key}>
                  {subj.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </DashboardCardHeader>
      <DashboardCardContent>
        <div ref={chartRef} className="w-full h-[500px]" />
      </DashboardCardContent>
    </DashboardCard>
  );
}