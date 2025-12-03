import React, { useLayoutEffect, useRef, useMemo } from "react";
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";

// Interface exata vinda do Backend (pode conter nulls)
interface RaceDataRaw {
  RACA: string;
  NOTA_MATEMATICA?: number | null;
  NOTA_CIENCIAS_NATUREZA?: number | null;
  NOTA_CIENCIAS_HUMANAS?: number | null;
  NOTA_LINGUAGENS_CODIGOS?: number | null;
  NOTA_REDACAO?: number | null;
  COUNT: number;
}

interface RacePerformanceChartProps {
  data: RaceDataRaw[];
}

export const RacePerformanceChart: React.FC<RacePerformanceChartProps> = ({ data }) => {
  // 1. UseRef para referenciar a DIV do DOM. Evita conflitos de ID.
  const chartRef = useRef<HTMLDivElement>(null);

  // 2. Tratamento de Dados (Null Safety): Sanitização com useMemo para performance
  const processedData = useMemo(() => {
    return data.map((item) => ({
      RACA: item.RACA || "Não Informado",
      NOTA_MATEMATICA: item.NOTA_MATEMATICA ?? 0,
      NOTA_CIENCIAS_NATUREZA: item.NOTA_CIENCIAS_NATUREZA ?? 0,
      NOTA_CIENCIAS_HUMANAS: item.NOTA_CIENCIAS_HUMANAS ?? 0,
      NOTA_LINGUAGENS_CODIGOS: item.NOTA_LINGUAGENS_CODIGOS ?? 0,
      NOTA_REDACAO: item.NOTA_REDACAO ?? 0,
      COUNT: item.COUNT ?? 0,
    }));
  }, [data]);

  useLayoutEffect(() => {
    // Segurança: Se a ref não estiver montada, não faz nada
    if (!chartRef.current) return;

    // Criação da Root no elemento referenciado
    let root = am5.Root.new(chartRef.current);

    // Ocultar a marca d'água (logo) do AmCharts, conforme instruído pelo usuário.
    if (root._logo) {
      root._logo.dispose();
    }

    // Tema Animado
    root.setThemes([am5themes_Animated.new(root)]);

    // Instância do Gráfico
    let chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: false,
        panY: false,
        wheelX: "none",
        wheelY: "none",
        layout: root.verticalLayout, // Legenda fica melhor posicionada com verticalLayout
      })
    );

    // --- EIXO Y (Categorias - Raça) ---
    let yRenderer = am5xy.AxisRendererY.new(root, {
      inversed: true, // Ordem correta (top-down)
      cellStartLocation: 0.1,
      cellEndLocation: 0.9,
      minGridDistance: 20, // Garante que todas as categorias apareçam
    });

    // Ajuste de Labels para não cortar texto
    yRenderer.labels.template.setAll({
      oversizedBehavior: "wrap", // Quebra linha se for muito longo
      maxWidth: 120, // Limite de largura
      textAlign: "end",
      centerY: am5.percent(50),
      paddingRight: 10,
      fontSize: 12, // Fonte ajustada para legibilidade
    });

    let yAxis = chart.yAxes.push(
      am5xy.CategoryAxis.new(root, {
        categoryField: "RACA",
        renderer: yRenderer,
        tooltip: am5.Tooltip.new(root, {}),
      })
    );

    yAxis.data.setAll(processedData);

    // --- EIXO X (Valores - Notas) ---
    let xRenderer = am5xy.AxisRendererX.new(root, {
      strokeOpacity: 0,
      minGridDistance: 50,
    });

    // Ocultar labels do eixo X conforme solicitado
    xRenderer.labels.template.setAll({
      forceHidden: true,
    });

    // Ocultar grid vertical para limpar o visual
    xRenderer.grid.template.setAll({
      forceHidden: true,
    });

    let xAxis = chart.xAxes.push(
      am5xy.ValueAxis.new(root, {
        min: 0,
        renderer: xRenderer,
        tooltip: am5.Tooltip.new(root, {}),
      })
    );

    // Cores
    const colors: Record<string, am5.Color> = {
      NOTA_CIENCIAS_NATUREZA: am5.color(0x88CCEE),
      NOTA_CIENCIAS_HUMANAS: am5.color(0xDDCC77),
      NOTA_LINGUAGENS_CODIGOS: am5.color(0xAA4466),
      NOTA_MATEMATICA: am5.color(0x4477AA),
      NOTA_REDACAO: am5.color(0xEE6677),
    };

    // Função Factory de Séries
    function createSeries(field: keyof typeof processedData[0], name: string) {
      let series = chart.series.push(
        am5xy.ColumnSeries.new(root, {
          name: name,
          stacked: true,
          xAxis: xAxis,
          yAxis: yAxis,
          valueXField: field as string,
          categoryYField: "RACA",
          fill: colors[field as string] || am5.color(0xcccccc),
          stroke: colors[field as string] || am5.color(0xcccccc),
        })
      );

      // Configuração Visual das Colunas e Tooltip
      series.columns.template.setAll({
        height: am5.percent(70), // Altura da barra
        tooltipText: "[bold]{name}[/]\nMédia: {valueX.formatNumber('#.0')}", // Tooltip melhorado
        tooltipY: am5.percent(50),
      });

      // Estilo do Tooltip (Fundo escuro para contraste)
      series.columns.template.adapters.add("tooltipHTML", () => {
        return undefined; // Garante uso do texto padrão, se necessário personalizar HTML, usar aqui.
      });

      // Labels centralizadas (Valores dentro da barra)
      series.bullets.push(function () {
        return am5.Bullet.new(root, {
          locationX: 0.5,
          locationY: 0.5,
          sprite: am5.Label.new(root, {
            text: "{valueX.formatNumber('#.0')}", // Apenas 1 casa decimal
            fill: am5.color(0xffffff),
            centerY: am5.percent(50),
            centerX: am5.percent(50),
            populateText: true,
            fontSize: 13, // Fonte ajustada (aumentada de 11 para 13)
            fontWeight: "500",
          }),
          // Ocultar label se o valor for muito pequeno para caber
          adapter: {
            sprite: function (sprite, target) {
              if (target.dataItem) {
                const value = target.dataItem.get("valueX");
                // Se nota < 20 (exemplo), oculta o texto para não encavalar
                if (typeof value === "number" && value < 20) {
                  sprite.set("visible", false);
                } else {
                  sprite.set("visible", true);
                }
              }
              return sprite;
            },
          },
        });
      });

      series.data.setAll(processedData);
    }

    // Criação das Séries na Ordem desejada
    createSeries("NOTA_CIENCIAS_NATUREZA", "Ciências da Natureza");
    createSeries("NOTA_CIENCIAS_HUMANAS", "Ciências Humanas");
    createSeries("NOTA_LINGUAGENS_CODIGOS", "Linguagens e Códigos");
    createSeries("NOTA_MATEMATICA", "Matemática");
    createSeries("NOTA_REDACAO", "Redação");

    // Animação de Entrada
    chart.appear(1000, 100);

    // --- LEGENDA ---
    let legend = chart.children.push(
      am5.Legend.new(root, {
        centerX: am5.percent(50),
        x: am5.percent(50),
        marginTop: 20,
        layout: root.horizontalLayout, // Legenda horizontal
        clickTarget: "itemContainer", // Melhora a área de clique
      })
    );

    // Espaçamento e estilo da legenda
    legend.markers.template.setAll({
      width: 16,
      height: 16,
      strokeWidth: 0,
    });

    legend.labels.template.setAll({
      fontSize: 12,
      fontWeight: "500",
    });

    // Vincula dados da legenda às séries (habilita o toggle de visibilidade)
    legend.data.setAll(chart.series.values);

    // 1. Correção de Ciclo de Vida: Cleanup Function
    return () => {
      root.dispose();
    };
  }, [processedData]); // Recria o gráfico apenas se os dados processados mudarem

  // Container com altura fixa e largura total via Tailwind
  return <div ref={chartRef} className="w-full h-[500px] relative" />;
};
