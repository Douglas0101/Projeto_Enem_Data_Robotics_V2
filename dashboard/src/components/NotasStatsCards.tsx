import {
  Cpu,
  BookOpen,
  MessageSquare,
  Edit3,
  TrendingUp,
  Calculator,
} from "lucide-react";
import type { TbNotasStatsRow } from "../types/dashboard";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle,
  DashboardCardFooter,
} from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";

interface Props {
  row: TbNotasStatsRow | null; // Pode ser null agora
}

export function NotasStatsCards({ row }: Props) {
  const metrics = [
    {
      label: "Matemática",
      key: "MAT",
      mean: row?.NOTA_MATEMATICA_mean,
      count: row?.NOTA_MATEMATICA_count,
      icon: Calculator,
      colorClass: "text-blue-500",
    },
    {
      label: "Ciências da Natureza",
      key: "CN",
      mean: row?.NOTA_CIENCIAS_NATUREZA_mean,
      count: row?.NOTA_CIENCIAS_NATUREZA_count,
      icon: Cpu,
      colorClass: "text-green-500",
    },
    {
      label: "Ciências Humanas",
      key: "CH",
      mean: row?.NOTA_CIENCIAS_HUMANAS_mean,
      count: row?.NOTA_CIENCIAS_HUMANAS_count,
      icon: BookOpen,
      colorClass: "text-orange-500",
    },
    {
      label: "Linguagens e Códigos",
      key: "LC",
      mean: row?.NOTA_LINGUAGENS_CODIGOS_mean,
      count: row?.NOTA_LINGUAGENS_CODIGOS_count,
      icon: MessageSquare,
      colorClass: "text-purple-500",
    },
    {
      label: "Redação",
      key: "RED",
      mean: row?.NOTA_REDACAO_mean,
      count: row?.NOTA_REDACAO_count,
      icon: Edit3,
      colorClass: "text-red-500",
    },
  ];

  if (!row) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <DashboardCard key={i}>
            <DashboardCardHeader className="flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4 rounded-full" />
            </DashboardCardHeader>
            <DashboardCardContent className="space-y-0 p-6 pt-0 flex justify-center">
              <Skeleton className="h-8 w-20" />
            </DashboardCardContent>
            <DashboardCardFooter className="space-x-2 pt-0">
              <Skeleton className="h-4 w-4 rounded-full" />
              <Skeleton className="h-4 w-32" />
            </DashboardCardFooter>
          </DashboardCard>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
      {metrics.map((m) => (
        <DashboardCard key={m.key}>
          <DashboardCardHeader className="flex-row items-center justify-between space-y-0 pb-2">
            <DashboardCardTitle className="text-sm font-medium">
              {m.label}
            </DashboardCardTitle>
            <m.icon className="h-4 w-4 text-muted-foreground" />
          </DashboardCardHeader>
          <DashboardCardContent className="space-y-0 p-6 pt-0 text-center">
            <div className="text-2xl font-bold">
              {m.mean != null ? m.mean.toFixed(1) : "–"}
            </div>
          </DashboardCardContent>
          <DashboardCardFooter className="space-x-2 pt-0 text-xs text-muted-foreground">
            <TrendingUp className="h-4 w-4 text-green-500" />
            <p>
              <span className="font-medium text-foreground">
                {m.count?.toLocaleString() ?? "0"}
              </span>{" "}
              participantes
            </p>
          </DashboardCardFooter>
        </DashboardCard>
      ))}
    </div>
  );
}
