import React, { useState, useEffect } from "react";
import { Check, ChevronsUpDown, MapPin } from "lucide-react";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "./ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./ui/popover";
import { MultiSelect, Option } from "./ui/multi-select";
import { MunicipalityMixedChart } from "./MunicipalityMixedChart";
import { MunicipalityRaceHistoryChart, RaceHistoryData } from "./MunicipalityRaceHistoryChart";
import { getNotasGeo, getMunicipios, getAvailableYears, getSocioRace } from "../api/dashboard";

const UFS = [
  { value: "AC", label: "Acre" },
  { value: "AL", label: "Alagoas" },
  { value: "AP", label: "Amapá" },
  { value: "AM", label: "Amazonas" },
  { value: "BA", label: "Bahia" },
  { value: "CE", label: "Ceará" },
  { value: "DF", label: "Distrito Federal" },
  { value: "ES", label: "Espírito Santo" },
  { value: "GO", label: "Goiás" },
  { value: "MA", label: "Maranhão" },
  { value: "MT", label: "Mato Grosso" },
  { value: "MS", label: "Mato Grosso do Sul" },
  { value: "MG", label: "Minas Gerais" },
  { value: "PA", label: "Pará" },
  { value: "PB", label: "Paraíba" },
  { value: "PR", label: "Paraná" },
  { value: "PE", label: "Pernambuco" },
  { value: "PI", label: "Piauí" },
  { value: "RJ", label: "Rio de Janeiro" },
  { value: "RN", label: "Rio Grande do Norte" },
  { value: "RS", label: "Rio Grande do Sul" },
  { value: "RO", label: "Rondônia" },
  { value: "RR", label: "Roraima" },
  { value: "SC", label: "Santa Catarina" },
  { value: "SP", label: "São Paulo" },
  { value: "SE", label: "Sergipe" },
  { value: "TO", label: "Tocantins" },
];

export function MunicipalityChartSection() {
  const [selectedUf, setSelectedUf] = useState<string>("");
  const [selectedCity, setSelectedCity] = useState<string>("");
  const [selectedYears, setSelectedYears] = useState<string[]>([]);
  const [cities, setCities] = useState<string[]>([]);
  const [availableYears, setAvailableYears] = useState<Option[]>([]);
  const [chartData, setChartData] = useState<any[]>([]);
  const [raceHistoryData, setRaceHistoryData] = useState<RaceHistoryData[]>([]);
  const [loading, setLoading] = useState(false);
  
  const [openUf, setOpenUf] = useState(false);
  const [openCity, setOpenCity] = useState(false);

  // 1. Load Available Years
  useEffect(() => {
    getAvailableYears().then(years => {
      const options = years
        .filter(y => y >= 2009) // Filter out years before 2009
        .sort((a, b) => b - a)
        .map(y => ({ label: String(y), value: String(y) }));
      setAvailableYears(options);
      // Default to latest 3 years
      if (options.length > 0) {
        setSelectedYears(options.slice(0, 3).map(o => o.value));
      }
    }).catch(console.error);
  }, []);

  // 2. Load Cities when UF changes
  useEffect(() => {
    if (selectedUf) {
      getMunicipios(selectedUf).then(cityList => {
        setCities(cityList);
        setSelectedCity(""); // Reset city on UF change
      }).catch(console.error);
    } else {
      setCities([]);
    }
  }, [selectedUf]);

  // 3. Fetch Data
  const fetchData = async () => {
    if (!selectedUf || !selectedCity || selectedYears.length === 0) return;

    setLoading(true);
    try {
      const years = selectedYears.map(Number);
      
      // Fetch Geo Data (Mixed Chart)
      const geoDataPromise = getNotasGeo({
        ano: years,
        uf: selectedUf,
        municipio: selectedCity,
        minCount: 0, // No minimum for specific city query usually
        limit: 100
      });

      // Fetch Race Data (History Chart) - Parallel Requests for each year
      const raceDataPromises = years.map(year => 
        getSocioRace({ year, uf: selectedUf, municipio: selectedCity })
          .then(rows => ({ year, rows }))
      );

      const [data, ...raceResults] = await Promise.all([geoDataPromise, ...raceDataPromises]);

      // Process Geo Data
      const formatted = data.map(row => ({
        ano: row.ANO,
        inscritos: row.INSCRITOS || 0, // Use INSCRITOS or 0
        provas: row.NOTA_REDACAO_count || 0,
        natureza: parseFloat((row.NOTA_CIENCIAS_NATUREZA_mean || 0).toFixed(1)),
        humanas: parseFloat((row.NOTA_CIENCIAS_HUMANAS_mean || 0).toFixed(1)),
        linguagens: parseFloat((row.NOTA_LINGUAGENS_CODIGOS_mean || 0).toFixed(1)),
        matematica: parseFloat((row.NOTA_MATEMATICA_mean || 0).toFixed(1)),
        redacao: parseFloat((row.NOTA_REDACAO_mean || 0).toFixed(1))
      }));
      setChartData(formatted);

      // Process Race Data
      const processedRaceData: RaceHistoryData[] = [];
      raceResults.forEach(({ year, rows }) => {
        rows.forEach(row => {
            processedRaceData.push({
                year: year,
                race: row.RACA,
                grades: {
                    media_geral: parseFloat((
                        ((row.NOTA_CIENCIAS_NATUREZA || 0) + 
                         (row.NOTA_CIENCIAS_HUMANAS || 0) + 
                         (row.NOTA_LINGUAGENS_CODIGOS || 0) + 
                         (row.NOTA_MATEMATICA || 0) + 
                         (row.NOTA_REDACAO || 0)) / 5
                    ).toFixed(1)),
                    matematica: row.NOTA_MATEMATICA || 0,
                    redacao: row.NOTA_REDACAO || 0,
                    linguagens: row.NOTA_LINGUAGENS_CODIGOS || 0,
                    humanas: row.NOTA_CIENCIAS_HUMANAS || 0,
                    natureza: row.NOTA_CIENCIAS_NATUREZA || 0
                }
            });
        });
      });
      setRaceHistoryData(processedRaceData);

    } catch (error) {
      console.error("Error fetching chart data:", error);
    } finally {
      setLoading(false);
    }
  };

  const totalInscritos = chartData.reduce((acc, curr) => acc + curr.inscritos, 0);
  const totalProvas = chartData.reduce((acc, curr) => acc + curr.provas, 0);
  const avgGeneral = chartData.length > 0 
    ? chartData.reduce((acc, curr) => acc + (curr.natureza + curr.humanas + curr.linguagens + curr.matematica + curr.redacao) / 5, 0) / chartData.length 
    : 0;

  return (
    <div className="space-y-8">
      <div className="p-4 bg-background border rounded-lg shadow-sm space-y-4">
        <h3 className="text-lg font-medium">Filtros do Gráfico Municipal</h3>
        <div className="flex flex-col md:flex-row gap-4">
          
          {/* UF Selector */}
          <Popover open={openUf} onOpenChange={setOpenUf}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={openUf}
                className="w-full md:w-[200px] justify-between"
              >
                {selectedUf
                  ? UFS.find((uf) => uf.value === selectedUf)?.label
                  : "Selecione o Estado..."}
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[200px] p-0">
              <Command>
                <CommandInput placeholder="Buscar estado..." />
                <CommandList>
                  <CommandEmpty>Estado não encontrado.</CommandEmpty>
                  <CommandGroup>
                    {UFS.map((uf) => (
                      <CommandItem
                        key={uf.value}
                        value={uf.label}
                        onSelect={() => {
                          setSelectedUf(uf.value);
                          setOpenUf(false);
                        }}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            selectedUf === uf.value ? "opacity-100" : "opacity-0"
                          )}
                        />
                        {uf.label}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>

          {/* City Selector */}
          <Popover open={openCity} onOpenChange={setOpenCity}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={openCity}
                disabled={!selectedUf}
                className="w-full md:w-[300px] justify-between"
              >
                {selectedCity || "Selecione o Município..."}
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[300px] p-0">
              <Command>
                <CommandInput placeholder="Buscar município..." />
                <CommandList>
                  <CommandEmpty>Município não encontrado.</CommandEmpty>
                  <CommandGroup className="max-h-64 overflow-auto">
                    {cities.map((city) => (
                      <CommandItem
                        key={city}
                        value={city}
                        onSelect={(currentValue) => {
                          // Command/cmdk uses lowercase values for internal logic, but we want the original casing usually.
                          // However, cmdk might return the normalized value. 
                          // Let's find the original from our cities list.
                          const original = cities.find(c => c.toLowerCase() === currentValue.toLowerCase()) || currentValue;
                          setSelectedCity(original);
                          setOpenCity(false);
                        }}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            selectedCity === city ? "opacity-100" : "opacity-0"
                          )}
                        />
                        {city}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>

          {/* Years MultiSelect */}
          <div className="w-full md:w-[400px]">
            <MultiSelect
              options={availableYears}
              selected={selectedYears}
              onChange={setSelectedYears}
              placeholder="Selecione os Anos"
            />
          </div>

          <Button onClick={fetchData} disabled={!selectedUf || !selectedCity || loading}>
            {loading ? "Carregando..." : "Gerar Gráfico"}
          </Button>
        </div>
      </div>

      {chartData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
           <div className="p-4 bg-white border rounded-lg shadow-sm">
              <p className="text-sm text-muted-foreground font-medium">Total de Inscritos (Período)</p>
              <p className="text-2xl font-bold text-blue-600">{totalInscritos.toLocaleString('pt-BR')}</p>
           </div>
           <div className="p-4 bg-white border rounded-lg shadow-sm">
              <p className="text-sm text-muted-foreground font-medium">Total de Provas (Período)</p>
              <p className="text-2xl font-bold text-indigo-600">{totalProvas.toLocaleString('pt-BR')}</p>
           </div>
           <div className="p-4 bg-white border rounded-lg shadow-sm">
              <p className="text-sm text-muted-foreground font-medium">Média Geral do Período</p>
              <p className="text-2xl font-bold text-emerald-600">{avgGeneral.toFixed(1)}</p>
           </div>
        </div>
      )}

      {chartData.length > 0 && (
        <MunicipalityMixedChart 
          data={chartData} 
          title={`Evolução - ${selectedCity}/${selectedUf}`} 
        />
      )}
      
      {raceHistoryData.length > 0 && (
          <MunicipalityRaceHistoryChart data={raceHistoryData} />
      )}
    </div>
  );
}
