import { useEffect, useState } from "react";
import {
  FileDown,
  FileText,
  Filter,
  Loader2,
  Search,
  Download
} from "lucide-react";
import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { MultiSelect } from "./ui/multi-select";
import { NotasGeoTable } from "./NotasGeoTable";
import {
  getAvailableYears,
  getMunicipios,
  getNotasGeo,
  TbNotasGeoRow,
} from "../api/dashboard";

const UFS = [
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
  "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
  "SP", "SE", "TO",
];

export function PremiumReport() {
  // --- States ---
  const [years, setYears] = useState<string[]>([]);
  const [availableYears, setAvailableYears] = useState<number[]>([]);

  const [ufs, setUfs] = useState<string[]>([]);
  
  const [cities, setCities] = useState<string[]>([]);
  const [availableCities, setAvailableCities] = useState<string[]>([]);
  const [loadingCities, setLoadingCities] = useState(false);

  const [data, setData] = useState<TbNotasGeoRow[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  // --- Data Loading ---

  // 1. Load Available Years on Mount
  useEffect(() => {
    getAvailableYears().then((ys) => {
      // Filtrar anos para exibir apenas de 2009 em diante
      setAvailableYears(ys.filter(year => year >= 2009));
    });
  }, []);

  // 2. Load Cities based on selected UFs
  useEffect(() => {
    const loadCities = async () => {
      setLoadingCities(true);
      try {
        // If multiple UFs selected, we might need to fetch for each or fetch all if API supports list
        // Currently API supports single UF filter for fetching cities, or All.
        // To keep it simple for "Premium", let's fetch all if no UF or multiple.
        // Optimization: If 1 UF, fetch specific. If > 1, fetch ALL (or user types to search).
        
        // For now, let's fetch all available cities if list is empty to populate cache? 
        // Actually, fetching 5000 cities is heavy. 
        // Better UX: Only fetch cities if 1 or 2 UFs are selected. Else, rely on search?
        // Let's fetch ALL for now but user filters via MultiSelect local search.
        
        const ufParam = ufs.length === 1 ? ufs[0] : undefined;
        const c = await getMunicipios(ufParam);
        setAvailableCities(c);
      } finally {
        setLoadingCities(false);
      }
    };
    loadCities();
  }, [ufs]);

  // 3. Fetch Preview Data
  const handleSearch = async () => {
    setLoadingData(true);
    try {
      const result = await getNotasGeo({
        ano: years.map(Number),
        uf: ufs,
        municipio: cities,
        limit: 100, // Preview limit
        minCount: 10
      });
      setData(result);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingData(false);
    }
  };

  // --- Export Logic ---
  const handleExport = (format: 'excel' | 'pdf') => {
    const params = new URLSearchParams();
    
    years.forEach(y => params.append("ano", y));
    ufs.forEach(u => params.append("uf", u));
    cities.forEach(c => params.append("municipio", c));
    
    params.append("format", format);
    params.append("min_count", "10"); // Default for report

    // Open in new tab/window to trigger download
    // Assuming API base URL is relative or proxied via Vite
    const baseUrl = "/v1/dashboard/notas/geo/export"; 
    window.open(`${baseUrl}?${params.toString()}`, "_blank");
  };

  return (
    <div className="space-y-6">
      <Card className="border-primary/20 shadow-md bg-gradient-to-b from-background to-muted/20">
        <CardHeader>
          <div className="flex items-center justify-between">
             <div className="space-y-1">
                <CardTitle className="text-xl flex items-center gap-2">
                    <Filter className="w-5 h-5 text-primary" />
                    Configuração do Relatório
                </CardTitle>
                <CardDescription>
                    Selecione múltiplos filtros para gerar uma análise personalizada.
                </CardDescription>
             </div>
             <Button onClick={handleSearch} disabled={loadingData}>
                {loadingData ? <Loader2 className="w-4 h-4 animate-spin mr-2"/> : <Search className="w-4 h-4 mr-2"/>}
                Atualizar Prévia
             </Button>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          {/* Years Filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Anos de Referência</label>
            <MultiSelect
              options={availableYears.map((y) => ({ label: String(y), value: String(y) }))}
              selected={years}
              onChange={setYears}
              placeholder="Selecione os anos..."
            />
          </div>

          {/* UFs Filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Estados (UF)</label>
            <MultiSelect
              options={UFS.map((uf) => ({ label: uf, value: uf }))}
              selected={ufs}
              onChange={setUfs}
              placeholder="Selecione os estados..."
            />
          </div>

          {/* Cities Filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center gap-2">
                Municípios 
                {loadingCities && <Loader2 className="w-3 h-3 animate-spin" />}
            </label>
            <MultiSelect
              options={availableCities.map((c) => ({ label: c, value: c }))}
              selected={cities}
              onChange={setCities}
              placeholder={ufs.length === 0 ? "Selecione um estado primeiro..." : "Selecione os municípios..."}
              className={ufs.length === 0 && cities.length === 0 ? "opacity-50 cursor-not-allowed" : ""}
            />
          </div>

        </CardContent>
      </Card>

      {/* Actions Bar */}
      <div className="flex justify-end gap-3">
        <Button 
            variant="outline" 
            className="gap-2 border-green-600 text-green-700 hover:bg-green-50"
            onClick={() => handleExport('excel')}
        >
            <FileText className="w-4 h-4" />
            Baixar Excel (.xlsx)
        </Button>
        <Button 
            className="gap-2 bg-red-600 hover:bg-red-700 text-white"
            onClick={() => handleExport('pdf')}
        >
            <FileDown className="w-4 h-4" />
            Baixar Relatório PDF
        </Button>
      </div>

      {/* Preview Table */}
      <div className="border rounded-lg bg-background overflow-hidden">
        <div className="p-4 bg-muted/30 border-b font-medium text-sm flex items-center gap-2">
            <Download className="w-4 h-4 text-muted-foreground" />
            Pré-visualização dos Dados (Top 100)
        </div>
        <div className="p-0">
            <NotasGeoTable rows={data} isLoading={loadingData} />
        </div>
      </div>
    </div>
  );
}
