import React, { useEffect, useState } from "react";
import { useFilters } from "../context/FilterContext";
import { FilterBar } from "../components/FilterBar";
import { ComparativoRadar } from "../components/ComparativoRadar";
import { SocioRaceChart } from "../components/SocioRaceChart";
import { StatePerformanceChart } from "../components/StatePerformanceChart";
import { StateHistoryChart } from "../components/StateHistoryChart"; // New import
import { VerticallyStackedAxesChart } from "../components/VerticallyStackedAxesChart";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs"; // New import
import {
  getRadarData,
  getSocioRace,
  getNotasGeoUf,
  getNotasStats, // New import
  TbRadarRow,
  TbSocioRaceRow,
  TbNotasGeoUfRow,
} from "../api/dashboard";

export function AdvancedPage() {
  const { year, uf, setUf } = useFilters();
  const [radarData, setRadarData] = useState<TbRadarRow[]>([]);
  const [raceData, setRaceData] = useState<TbSocioRaceRow[]>([]);
  const [geoUfData, setGeoUfData] = useState<TbNotasGeoUfRow[]>([]);
  
  // History Data State
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch Overview Data (Specific Year)
  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [radar, race, geoUf] = await Promise.all([
          getRadarData({ year, uf }),
          getSocioRace({ year, uf }), // Added uf filter here too for consistency if supported, or keep as is
          getNotasGeoUf({ ano: year, minInscritos: 500 }), 
        ]);

        if (!cancelled) {
          setRadarData(radar);
          setRaceData(race);
          setGeoUfData(geoUf);
        }
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, [year, uf]);

  // Fetch History Data (All Years)
  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      setHistoryLoading(true);
      try {
        let data;
        if (uf === "all") {
          // Fetch National Stats History
          data = await getNotasStats({});
        } else {
          // Fetch specific UF History (no year param = all years)
          data = await getNotasGeoUf({ uf, minInscritos: 0 });
        }

        if (!cancelled) {
          // Filter data to valid range 2009-2024 as per market standard
          let filteredData = Array.isArray(data) 
            ? data.filter((d: any) => d.ANO >= 2009 && d.ANO <= 2024)
            : [];

          // Normalize data: Map TOTAL_INSCRITOS to INSCRITOS for National Stats so the chart can use it
          if (uf === "all") {
            filteredData = filteredData.map((d: any) => ({
              ...d,
              INSCRITOS: d.TOTAL_INSCRITOS
            }));
          }
          
          setHistoryData(filteredData);
        }
      } catch (err) {
        console.error("Failed to load history:", err);
      } finally {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      }
    }

    loadHistory();

    return () => {
      cancelled = true;
    };
  }, [uf]); // Re-run when UF changes

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tight">Explorador Avançado</h1>
          <p className="text-muted-foreground">
            Ferramentas de análise comparativa e inteligência de dados (Nível Premium).
          </p>
      </div>

      <FilterBar />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
          <strong>Erro:</strong> {error}
        </div>
      )}

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-[400px] grid-cols-2">
          <TabsTrigger value="overview">Visão Geral ({year})</TabsTrigger>
          <TabsTrigger value="history">Evolução Histórica</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Row: Radar Chart (Full Width) */}
              <div className="col-span-1 lg:col-span-2">
                  <ComparativoRadar data={radarData} isLoading={loading} uf={uf} />
              </div>

              {/* Second Row: Socioeconomic Analysis (Race Chart) */}
              <div className="col-span-1 lg:col-span-2">
                <SocioRaceChart data={raceData} isLoading={loading} />
              </div>

              {/* Third Row: State Performance Ranking */}
              <div className="col-span-1 lg:col-span-2">
                <StatePerformanceChart 
                  data={geoUfData} 
                  isLoading={loading} 
                  onStateClick={(newUf) => setUf(newUf)}
                  selectedUf={uf}
                />
              </div>
          </div>
        </TabsContent>

        <TabsContent value="history" className="mt-6 space-y-6">
          <StateHistoryChart 
            data={historyData} 
            isLoading={historyLoading} 
            entityName={uf === "all" ? "Brasil (Média Nacional)" : uf}
          />
          <VerticallyStackedAxesChart 
            data={historyData} 
            isLoading={historyLoading} 
            entityName={uf === "all" ? "Brasil (Média Nacional)" : uf}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}