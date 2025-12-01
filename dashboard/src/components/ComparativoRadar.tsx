import React, { useEffect, useState, useMemo } from "react";
import Highcharts from "highcharts";
import HighchartsReact from "highcharts-react-official";
import HighchartsMore from "highcharts/highcharts-more";
import { TbRadarRow } from "../api/dashboard";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle
} from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";

// Initialize Highcharts More module for Spider/Radar charts
if (typeof Highcharts === "object") {
  if (typeof HighchartsMore === "function") {
    HighchartsMore(Highcharts);
  } else if (typeof HighchartsMore === "object" && (HighchartsMore as any).default) {
    (HighchartsMore as any).default(Highcharts);
  }
}

// Helper to get CSS variable colors
const getThemeColor = (cssVar: string): string => {
  if (typeof window === 'undefined') return '#000000';
  return getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim() || '#000000';
};

interface Props {
  data: TbRadarRow[];
  isLoading: boolean;
  uf: string;
}

export function ComparativoRadar({ data, isLoading, uf }: Props) {
  
  const options: Highcharts.Options = useMemo(() => {
    const categories = data.map(d => d.metric);
    const brData = data.map(d => d.br_mean ?? 0);
    const ufData = data.map(d => d.uf_mean ?? 0);
    const bestData = data.map(d => d.best_uf_mean ?? 0);
    
    const primaryColorHSL = getThemeColor('--primary');
    const primaryColor = `hsl(${primaryColorHSL.replace(/\s+/g, ',')})`;
    const foregroundColorHSL = getThemeColor('--foreground');
    const foregroundColor = `hsl(${foregroundColorHSL.replace(/\s+/g, ',')})`;
    const gridColorHSL = getThemeColor('--border');
    const gridColor = `hsl(${gridColorHSL.replace(/\s+/g, ',')})`;

    return {
      chart: {
        polar: true,
        type: 'line',
        height: 500,
        backgroundColor: 'transparent',
        style: { fontFamily: 'Inter, sans-serif' }
      },
      accessibility: { enabled: false },
      title: { text: undefined },
      pane: {
        size: '80%'
      },
      xAxis: {
        categories: categories,
        tickmarkPlacement: 'on',
        lineWidth: 0,
        labels: {
          style: { color: foregroundColor, fontWeight: 'bold' },
          distance: 30
        },
        gridLineColor: gridColor
      },
      yAxis: {
        gridLineInterpolation: 'polygon',
        lineWidth: 0,
        min: 0,
        max: 1000, // Fixed scale for consistency
        gridLineColor: gridColor,
        labels: {
          enabled: false // Clean look
        }
      },
      tooltip: {
        shared: true,
        pointFormat: '<span style="color:{series.color}">{series.name}: <b>{point.y:,.0f}</b><br/>',
        backgroundColor: getThemeColor('--popover') ? `hsl(${getThemeColor('--popover').replace(/\s+/g, ',')})` : '#ffffff',
        style: { color: foregroundColor }
      },
      legend: {
        align: 'center',
        verticalAlign: 'bottom',
        itemStyle: { color: foregroundColor }
      },
      series: [
        {
          type: 'area',
          name: 'Melhor Estado (Benchmark)',
          data: bestData,
          color: '#10b981', // Emerald 500
          fillOpacity: 0.1,
          dashStyle: 'ShortDot'
        },
        {
          type: 'area',
          name: 'Média Brasil',
          data: brData,
          color: '#64748b', // Slate 500
          fillOpacity: 0.2
        },
        {
          type: 'area',
          name: uf === 'all' ? 'Todos Selecionados' : `Estado (${uf})`,
          data: ufData,
          color: primaryColor, // Theme Primary
          fillOpacity: 0.5,
          zIndex: 2
        }
      ]
    };
  }, [data, uf]);

  return (
    <DashboardCard className="w-full h-full">
      <DashboardCardHeader>
        <DashboardCardTitle className="text-lg font-bold">Comparativo de Competitividade</DashboardCardTitle>
        <p className="text-sm text-muted-foreground">
          Análise multidimensional: {uf === 'all' ? 'Brasil' : uf} vs Média Nacional vs Benchmark
        </p>
      </DashboardCardHeader>
      <DashboardCardContent>
        {isLoading ? (
          <div className="flex items-center justify-center h-[500px]">
            <Skeleton className="h-full w-full rounded-full opacity-20" />
          </div>
        ) : data.length > 0 ? (
          <HighchartsReact
            highcharts={Highcharts}
            options={options}
          />
        ) : (
          <div className="flex items-center justify-center h-[500px] text-muted-foreground">
            Sem dados para o radar com os filtros atuais.
          </div>
        )}
      </DashboardCardContent>
    </DashboardCard>
  );
}
