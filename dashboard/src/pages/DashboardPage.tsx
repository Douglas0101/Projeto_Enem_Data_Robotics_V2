import React from "react";
import {
  getAvailableYears,
  getNotasGeo,
  getNotasGeoUf,
  getNotasStats
} from "../api/dashboard";
import { useFilters } from "../context/FilterContext";
import { NotasStatsCards } from "../components/NotasStatsCards";
import { NotasGeoTable } from "../components/NotasGeoTable";
import NotasAmMap from "../components/NotasAmMap";
import NotasHistogram from "../components/NotasHistogram";
import NotasHeatmap from "../components/NotasHeatmap";
import { FilterBar } from "../components/FilterBar";
import { TbNotasGeoUfRow } from "../types/dashboard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";

export function DashboardPage() {
  const { year, setYear, uf } = useFilters();
  const [minCount, setMinCount] = React.useState<number>(30);
  const [statsLoading, setStatsLoading] = React.useState(false);
  const [geoLoading, setGeoLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [statsRow, setStatsRow] = React.useState<any | null>(null);
  const [geoRows, setGeoRows] = React.useState<any[]>([]);
  const [geoUfRows, setGeoUfRows] = React.useState<TbNotasGeoUfRow[]>([]);
  const [geoUfRowsAllYears, setGeoUfRowsAllYears] = React.useState<TbNotasGeoUfRow[]>([]);
  const [geoAllLoading, setGeoAllLoading] = React.useState(true);

  // Initial load of available years (to set default if needed, although context has default 2023)
  React.useEffect(() => {
    let cancelled = false;
    async function loadYears() {
      try {
        const ys = await getAvailableYears();
        // We could sync context with available years here if needed
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message);
        }
      }
    }
    loadYears();
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    async function loadAllYearsGeoUf() {
      try {
        setGeoAllLoading(true);
        const geoUfAll = await getNotasGeoUf({ minInscritos: 100 });
        if (!cancelled) {
          setGeoUfRowsAllYears(geoUfAll || []);
        }
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message);
        }
      } finally {
        if (!cancelled) {
          setGeoAllLoading(false);
        }
      }
    }
    void loadAllYearsGeoUf();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleRefresh = async () => {
    if (!year) {
      return;
    }
    setError(null);
    setStatsLoading(true);
    setGeoLoading(true);
    try {
      const [stats, geo, geoUf] = await Promise.all([
        getNotasStats({ anoInicio: year, anoFim: year }),
        getNotasGeo({
          ano: year,
          uf: uf === "all" ? undefined : uf,
          minCount,
          limit: 5000,
          page: 1
        }),
        getNotasGeoUf({ ano: year, minInscritos: 100, uf: uf === "all" ? undefined : uf }),
      ]);
      setStatsRow(stats[0] ?? null);
      setGeoRows(geo || []);
      setGeoUfRows(geoUf || []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setStatsLoading(false);
      setGeoLoading(false);
    }
  };

  // React to filter changes
  React.useEffect(() => {
    if (year != null) {
      void handleRefresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, uf, minCount]); // Trigger refresh when year or uf changes

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      
      <FilterBar />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Erro: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {/* Stats Row */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-foreground">Estatísticas Gerais</h2>
          {statsLoading && <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />}
        </div>
        {statsRow ? (
          <NotasStatsCards row={statsRow} />
        ) : (
          <p className="text-sm text-muted-foreground">
            Nenhuma estatística carregada ainda.
          </p>
        )}
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="mapa" className="space-y-4">
        <TabsList>
          <TabsTrigger value="mapa">Mapa Geográfico</TabsTrigger>
          <TabsTrigger value="histograma">Médias Nacionais</TabsTrigger>
          <TabsTrigger value="heatmap">Desempenho Unificado</TabsTrigger>
          <TabsTrigger value="tabela">Tabela Detalhada</TabsTrigger>
        </TabsList>
        
        <TabsContent value="mapa" className="space-y-4">
          <NotasAmMap
            data={geoUfRows}
            isLoading={geoLoading}
            year={year ?? 0}
          />
        </TabsContent>
        
        <TabsContent value="histograma">
          {year ? (
            <NotasHistogram year={year} />
          ) : (
            <div className="p-4 text-muted-foreground">Selecione um ano para ver as médias nacionais.</div>
          )}
        </TabsContent>
        
        <TabsContent value="heatmap">
          <NotasHeatmap
            data={geoUfRowsAllYears}
            isLoading={geoAllLoading}
            year={year ?? 0}
          />
        </TabsContent>
        
        <TabsContent value="tabela">
           <NotasGeoTable rows={geoRows} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
