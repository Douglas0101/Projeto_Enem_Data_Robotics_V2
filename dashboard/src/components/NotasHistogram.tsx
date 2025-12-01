import React, { useLayoutEffect, useRef, useState, useEffect } from "react";
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import { TbNotasHistogramRow } from "../types/dashboard";
import { getAvailableYears, getNotasHistograma } from "../api/dashboard";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle
} from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";

interface Props {
  year: number;
}

const DISCIPLINAS = {
  NOTA_MATEMATICA: "Matemática",
  NOTA_CIENCIAS_NATUREZA: "Ciências da Natureza",
  NOTA_CIENCIAS_HUMANAS: "Ciências Humanas",
  NOTA_LINGUAGENS_CODIGOS: "Linguagens e Códigos",
  NOTA_REDACAO: "Redação",
} as const;

type DisciplinaKey = keyof typeof DISCIPLINAS;

export default function NotasHistogram({ year }: Props) {
  const [disciplina, setDisciplina] = useState<DisciplinaKey>("NOTA_MATEMATICA");
  const [data, setData] = useState<TbNotasHistogramRow[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [displayYear, setDisplayYear] = useState<number>(year);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const chartRef = useRef<HTMLDivElement>(null);

  // Carrega anos disponíveis uma única vez para permitir fallback automático
  useEffect(() => {
    let cancelled = false;
    const loadYears = async () => {
      try {
        const years = await getAvailableYears();
        if (!cancelled && Array.isArray(years) && years.length > 0) {
          // Ordena desc para facilitar o fallback
          const sorted = [...years].sort((a, b) => b - a);
          setAvailableYears(sorted);
        }
      } catch (err) {
        console.error("Erro ao buscar anos disponíveis para histograma:", err);
      }
    };
    loadYears();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setInfoMessage(null);
      setDisplayYear(year);

      const safeFetch = async (ano: number) => {
        try {
          return await getNotasHistograma({ year: ano, disciplina });
        } catch (error) {
          console.error(`Erro ao buscar histograma para ${ano}:`, error);
          return [];
        }
      };

      // 1) Tenta ano selecionado
      try {
        const histData = await safeFetch(year);
        if (histData.length > 0) {
          setData(histData);
          return;
        }

        // 2) Fallback: usa ano mais recente disponível (<= selecionado, senão o mais alto)
        const yearsList = availableYears.length
          ? availableYears
          : await getAvailableYears().catch(() => []);

        if (Array.isArray(yearsList) && yearsList.length > 0) {
          if (availableYears.length === 0) {
            // Cacheia para próximas buscas
            setAvailableYears([...yearsList].sort((a, b) => b - a));
          }

          const sortedDesc = [...yearsList].sort((a, b) => b - a);
          const fallbackYear =
            sortedDesc.find((y) => y <= year) ?? sortedDesc[0];

          if (fallbackYear && fallbackYear !== year) {
            const fallbackData = await safeFetch(fallbackYear);
            if (fallbackData.length > 0) {
              setData(fallbackData);
              setDisplayYear(fallbackYear);
              setInfoMessage(`Dados de ${year} indisponíveis. Exibindo ${fallbackYear}.`);
              return;
            }
          }
        }

        // 3) Sem dados em nenhuma fonte
        setData([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [year, disciplina]);

  useLayoutEffect(() => {
    if (!chartRef.current || data.length === 0) return;

    const root = am5.Root.new(chartRef.current);

    root.setThemes([am5themes_Animated.new(root)]);
    (root as any)._logo?.dispose();

    // Create chart
    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: true,
        panY: false, // Usually histograms don't pan Y
        wheelX: "panX",
        wheelY: "zoomX",
        layout: root.verticalLayout
      })
    );

    // Add cursor
    const cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
      behavior: "none"
    }));
    cursor.lineY.set("visible", false);

    // Create axes
    const xAxis = chart.xAxes.push(
      am5xy.ValueAxis.new(root, {
        min: 0,
        max: 1000,
        renderer: am5xy.AxisRendererX.new(root, {
          minGridDistance: 50
        }),
        tooltip: am5.Tooltip.new(root, {})
      })
    );

    // Clean vertical grid
    xAxis.get("renderer").grid.template.set("visible", false);

    const yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        extraMax: 0.1, // Add breathing room
        renderer: am5xy.AxisRendererY.new(root, {})
      })
    );

    // Process data to find peak
    let maxVal = -Infinity;
    let maxIndex = -1;
    data.forEach((item, index) => {
        if (item.CONTAGEM > maxVal) {
            maxVal = item.CONTAGEM;
            maxIndex = index;
        }
    });

    const processedData = data.map((item, index) => ({
        ...item,
        isPeak: index === maxIndex
    }));

    // Create series
    const series = chart.series.push(
      am5xy.SmoothedXLineSeries.new(root, {
        name: "Frequência",
        xAxis: xAxis,
        yAxis: yAxis,
        valueYField: "CONTAGEM",
        valueXField: "BIN_START",
        tooltip: am5.Tooltip.new(root, {
          labelText: "{valueY} alunos\nNota: {valueX}"
        })
      })
    );

    // Gradient Fill
    series.fills.template.setAll({
      fillOpacity: 1,
      visible: true,
      fillGradient: am5.LinearGradient.new(root, {
        stops: [
          { opacity: 0.8 },
          { opacity: 0.1 }
        ],
        rotation: 90
      })
    });

    series.strokes.template.setAll({
      strokeWidth: 2
    });

    // Add bullets for all points (standard)
    series.bullets.push(function(root, series, dataItem) {
        // If it is the peak, we handle it in the next bullet pusher to keep logic clean
        if (dataItem.dataContext && (dataItem.dataContext as any).isPeak) {
            return undefined; 
        }
        
        return am5.Bullet.new(root, {
            sprite: am5.Circle.new(root, {
                radius: 4,
                fill: series.get("fill"),
                stroke: root.interfaceColors.get("background"),
                strokeWidth: 2
            })
        });
    });

    // Peak Bullet (Special)
    series.bullets.push(function(root, series, dataItem) {
      if (dataItem.dataContext && (dataItem.dataContext as any).isPeak) {
        const container = am5.Container.new(root, {});
        
        const circle = container.children.push(am5.Circle.new(root, {
          radius: 6,
          fill: series.get("fill"),
          stroke: root.interfaceColors.get("background"),
          strokeWidth: 2,
          tooltipText: "Pico: {valueY}"
        }));

        // Add pulsing animation
        const circle2 = container.children.push(am5.Circle.new(root, {
          radius: 6,
          fill: series.get("fill"),
          opacity: 0.5
        }));

        circle2.animate({
          key: "radius",
          to: 20,
          duration: 1000,
          easing: am5.ease.out(am5.ease.cubic),
          loops: Infinity
        });
        
        circle2.animate({
          key: "opacity",
          to: 0,
          duration: 1000,
          easing: am5.ease.out(am5.ease.cubic),
          loops: Infinity
        });

        return am5.Bullet.new(root, {
          sprite: container
        });
      }
      return undefined;
    });

    series.data.setAll(processedData);

    // Make stuff animate on load
    series.appear(1000);
    chart.appear(1000, 100);

    return () => {
      root.dispose();
    };
  }, [data]);

  return (
    <DashboardCard className="w-full">
      <DashboardCardHeader className="flex-col md:flex-row items-start md:items-center gap-4">
        <div className="flex-1">
          <DashboardCardTitle className="text-base font-medium">
            Distribuição de Frequência ({displayYear})
          </DashboardCardTitle>
          <p className="text-sm text-muted-foreground">
            Curva de distribuição das notas (Histograma suavizado).
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="w-[100%] md:w-[230px]">
            <select
              className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={disciplina}
              onChange={(e) => setDisciplina(e.target.value as DisciplinaKey)}
            >
              {Object.entries(DISCIPLINAS).map(([key, value]) => (
                <option key={key} value={key}>
                  {value}
                </option>
              ))}
            </select>
          </div>
        </div>
      </DashboardCardHeader>

      <DashboardCardContent>
        {infoMessage && (
          <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {infoMessage}
          </div>
        )}
        {isLoading ? (
          <div className="flex items-center justify-center h-[500px]">
            <Skeleton className="h-full w-full rounded-md" />
          </div>
        ) : !data || data.length === 0 ? (
          <div className="flex items-center justify-center h-[500px]">
            <p className="text-muted-foreground">Nenhum dado disponível.</p>
          </div>
        ) : (
           <div ref={chartRef} className="w-full h-[500px]" />
        )}
      </DashboardCardContent>
    </DashboardCard>
  );
}
