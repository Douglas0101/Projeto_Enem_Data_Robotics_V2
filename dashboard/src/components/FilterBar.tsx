import * as React from "react";
import { Calendar, Check, ChevronsUpDown, MapPin, FilterX } from "lucide-react";
import { cn } from "@/lib/utils";
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
import { useFilters } from "../context/FilterContext";
import { getAvailableYears } from "../api/dashboard";

const UFS = [
  { value: "all", label: "Todos os Estados" },
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

export function FilterBar() {
  const { year, setYear, uf, setUf } = useFilters();
  const [openUf, setOpenUf] = React.useState(false);
  const [openYear, setOpenYear] = React.useState(false);
  const [years, setYears] = React.useState<number[]>([]);

  // Helper to find the current UF label
  const currentUfLabel = React.useMemo(() => {
    if (uf === "all") return "Todos os Estados";
    return UFS.find((framework) => framework.value === uf)?.label || "Selecione o estado...";
  }, [uf]);

  // Carrega anos disponíveis e ajusta o ano atual para o mais recente se necessário
  React.useEffect(() => {
    let cancelled = false;
    const loadYears = async () => {
      try {
        const available = await getAvailableYears();
        if (cancelled) return;
        if (Array.isArray(available) && available.length > 0) {
          const filtered = available.filter(y => y >= 2009); // Filter out years before 2009
          const sorted = [...filtered].sort((a, b) => b - a); // desc
          setYears(sorted);
          if (!sorted.includes(year)) {
            setYear(sorted[0]);
          }
        }
      } catch (err) {
        console.error("Erro ao carregar anos disponíveis:", err);
        // fallback para lista estática caso a API falhe
        const fallback = Array.from({ length: 2024 - 2009 + 1 }, (_, i) => 2024 - i);
        setYears(fallback);
      }
    };
    loadYears();
    return () => { cancelled = true; };
  }, [setYear, year]);

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between p-4 bg-background border-b">
      <div className="flex flex-1 items-center gap-4">
        
        {/* UF Selector (Combobox) */}
        <Popover open={openUf} onOpenChange={setOpenUf}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={openUf}
              className="w-[200px] justify-between"
            >
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 shrink-0 opacity-50" />
                {currentUfLabel}
              </div>
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[200px] p-0">
            <Command>
              <CommandInput placeholder="Buscar estado..." />
              <CommandList>
                <CommandEmpty>Estado não encontrado.</CommandEmpty>
                <CommandGroup>
                  {UFS.map((item) => (
                    <CommandItem
                      key={item.value}
                      value={item.label} // Use label for search and display in CommandInput
                      onSelect={() => {
                        setUf(item.value);
                        setOpenUf(false);
                      }}
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          uf === item.value ? "opacity-100" : "opacity-0"
                        )}
                      />
                      {item.label}
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>

        {/* Year Selector (Dropdown/Combobox simpler) */}
        <Popover open={openYear} onOpenChange={setOpenYear}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={openYear}
              className="w-[140px] justify-between"
            >
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 shrink-0 opacity-50" />
                {year ? `Ano ${year}` : "Selecione o ano..."}
              </div>
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[140px] p-0">
            <Command>
              <CommandInput placeholder="Buscar ano..." />
              <CommandList>
                <CommandEmpty>Ano não encontrado.</CommandEmpty>
                <CommandGroup>
                  {(years.length ? years : Array.from({ length: 2024 - 2009 + 1 }, (_, i) => 2024 - i)).map((y) => (
                    <CommandItem
                      key={y}
                      value={y.toString()}
                      onSelect={(currentValue) => {
                        setYear(Number(currentValue));
                        setOpenYear(false);
                      }}
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          year === y ? "opacity-100" : "opacity-0"
                        )}
                      />
                      {y}
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>

        <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => {
                const defaultYear = years.length ? years[0] : 2023;
                setYear(defaultYear);
                setUf("all"); // Reset to "all" states
            }}
            title="Resetar filtros"
        >
            <FilterX className="h-4 w-4 text-muted-foreground" />
        </Button>

      </div>
    </div>
  );
}
