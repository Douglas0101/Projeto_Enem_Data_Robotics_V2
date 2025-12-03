import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import { Check, ChevronsUpDown, MapPin, Building2 } from "lucide-react";
import { DashboardCard, DashboardCardContent, DashboardCardHeader, DashboardCardTitle } from "./ui/DashboardCard";
import { Skeleton } from "./ui/skeleton";
import { useFilters } from "../context/FilterContext";
import { getMunicipios, getSocioRace, TbSocioRaceRow } from "../api/dashboard";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "./ui/command";

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

const YEAR_MIN = 2009;
const YEAR_MAX = 2024;

export function RaceHistoryChart() {
  const chartRef = useRef<HTMLDivElement>(null);
  const { uf, setUf } = useFilters();

  const [municipios, setMunicipios] = useState<string[]>([]);
  const [selectedMunicipio, setSelectedMunicipio] = useState<string>("");
  const [raceData, setRaceData] = useState<TbSocioRaceRow[]>([]);

  const [loadingCities, setLoadingCities] = useState(false);
  const [loadingData, setLoadingData] = useState(false);

  const [openUf, setOpenUf] = useState(false);
  const [openCity, setOpenCity] = useState(false);

  const currentUfLabel = useMemo(() => {
    if (!uf || uf === "all") return "Escolha o estado (obrigatório)";
    return UFS.find((item) => item.value === uf)?.label || uf;
  }, [uf]);

  // Carrega municípios assim que o estado é escolhido
  useEffect(() => {
    if (!uf || uf === "all") {
      setMunicipios([]);
      setSelectedMunicipio("");
      setRaceData([]);
      return;
    }

    let cancelled = false;
    setLoadingCities(true);

    getMunicipios(uf)
      .then((cities) => {
        if (cancelled) return;
        setMunicipios(cities);

        // Seleciona o primeiro município para já exibir o gráfico
        if (cities.length > 0) {
          const normalized = cities.find((c) => c === selectedMunicipio);
          setSelectedMunicipio(normalized || cities[0]);
        } else {
          setSelectedMunicipio("");
        }
      })
      .catch((err) => {
        console.error("Erro ao carregar municípios:", err);
        setMunicipios([]);
        setSelectedMunicipio("");
      })
      .finally(() => {
        if (!cancelled) setLoadingCities(false);
      });

    return () => {
      cancelled = true;
    };
  }, [uf]);

  // Busca o histórico (todos os anos) para UF + município
  useEffect(() => {
    if (!uf || uf === "all" || !selectedMunicipio) {
      setRaceData([]);
      return;
    }

    let cancelled = false;
    setLoadingData(true);

    getSocioRace({ uf, municipio: selectedMunicipio })
      .then((response) => {
        if (cancelled) return;
        const filtered = response.filter(
          (row) => row.ANO && row.ANO >= YEAR_MIN && row.ANO <= YEAR_MAX
        );
        setRaceData(filtered);
      })
      .catch((err) => {
        console.error("Erro ao carregar série histórica de raça:", err);
        setRaceData([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingData(false);
      });

    return () => {
      cancelled = true;
    };
  }, [uf, selectedMunicipio]);

  // Processa os dados para o gráfico (todas as séries por raça)
  const processed = useMemo(() => {
    if (!raceData.length) {
      return { data: [] as Record<string, any>[], races: [] as { name: string; slug: string }[], maxValue: 0 };
    }

    const byYear = new Map<string, Record<string, any>>();
    const racesSet = new Map<string, string>(); // name -> slug
    let maxValue = 0;

    const disciplines = [
      { key: "NOTA_MATEMATICA", label: "Matemática", slug: "matematica" },
      { key: "NOTA_CIENCIAS_NATUREZA", label: "Ciências da Natureza", slug: "natureza" },
      { key: "NOTA_CIENCIAS_HUMANAS", label: "Ciências Humanas", slug: "humanas" },
      { key: "NOTA_LINGUAGENS_CODIGOS", label: "Linguagens e Códigos", slug: "linguagens" },
      { key: "NOTA_REDACAO", label: "Redação", slug: "redacao" },
    ] as const;

    const slugify = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-zA-Z0-9]+/g, "_");

    raceData.forEach((row) => {
      const year = row.ANO;
      if (!year || year < YEAR_MIN || year > YEAR_MAX) return;

      const race = row.RACA || "Não declarada";
      const raceSlug = slugify(race);

      // Calcula média e contagem de provas válidas dinamicamente
      // Nota: Para provas objetivas (TRI), nota 0 é tecnicamente impossível/inválida (indica falta de dados/zeros preenchidos)
      // Para Redação, 0 é uma nota válida.
      const validScores = disciplines
        .map((d) => {
          const val = (row as any)[d.key] as number | null | undefined;
          if (val === null || val === undefined) return null;
          if (d.slug !== "redacao" && val === 0) return null; // Filtra zeros de objetivas
          return val;
        })
        .filter((v) => v !== null) as number[];

      const countDisciplines = validScores.length;
      const avg = countDisciplines > 0 ? validScores.reduce((a, b) => a + b, 0) / countDisciplines : 0;
      const value = Number(avg.toFixed(1));

      const key = String(year);

      const existing = byYear.get(key) || { year: key };
      existing[`${raceSlug}_value`] = value;
      existing[`${raceSlug}_count`] = row.COUNT ?? 0;
      existing[`${raceSlug}_discipline_count`] = countDisciplines;
      disciplines.forEach((disc) => {
        const val = (row as any)[disc.key];
        existing[`${raceSlug}_${disc.slug}`] = val != null ? Number(val).toFixed(1) : "s/d";
      });

      byYear.set(key, existing);

      racesSet.set(race, raceSlug);
      if (value > maxValue) maxValue = value;
    });

    const races = Array.from(racesSet.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([name, slug]) => ({ name, slug }));

    // Garante todos os anos no eixo X (mesmo sem dados); não injeta zeros para evitar barras falsas
    for (let y = YEAR_MIN; y <= YEAR_MAX; y++) {
      const key = String(y);
      if (!byYear.has(key)) {
        byYear.set(key, { year: key });
      }
    }

    const data = Array.from(byYear.values()).sort((a, b) => Number(a.year) - Number(b.year));
    return { data, races, maxValue };
  }, [raceData]);

  // Desenha o gráfico com amCharts
  useLayoutEffect(() => {
    if (!chartRef.current) return;
    if (loadingData || !processed.data.length || !processed.races.length) return;

    const root = am5.Root.new(chartRef.current);
    root.setThemes([am5themes_Animated.new(root)]);
    (root as any)._logo?.dispose();

    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: false,
        panY: false,
        wheelX: "panX",
        wheelY: "zoomX",
        paddingLeft: 0,
        layout: root.verticalLayout,
      })
    );

    chart.set(
      "scrollbarX",
      am5.Scrollbar.new(root, {
        orientation: "horizontal",
      })
    );

    const xRenderer = am5xy.AxisRendererX.new(root, {
      minorGridEnabled: true,
      minGridDistance: 30,
      cellStartLocation: 0.1,
      cellEndLocation: 0.9,
    });

    const xAxis = chart.xAxes.push(
      am5xy.CategoryAxis.new(root, {
        categoryField: "year",
        renderer: xRenderer,
      })
    );
    xRenderer.grid.template.setAll({ location: 1 });
    xAxis.data.setAll(processed.data);

    const yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        min: 0,
        renderer: am5xy.AxisRendererY.new(root, {
          strokeOpacity: 0.1,
        }),
      })
    );

    const legend = chart.children.push(
      am5.Legend.new(root, {
        centerX: am5.p50,
        x: am5.p50,
      })
    );

    const colorSet = am5.ColorSet.new(root, { step: 2 });

    const makeSeries = (name: string, slug: string, fieldName: string, index: number) => {
      const color = colorSet.getIndex(index);
      const tooltipText = [
        "[bold]{name}[/]",
        "Ano: {categoryX}",
        "Média Geral: {valueY}",
        `Provas Contabilizadas: {${slug}_discipline_count}/5`,
        `Participantes: {${slug}_count}`,
        `Matemática: {${slug}_matematica}`,
        `Ciências da Natureza: {${slug}_natureza}`,
        `Ciências Humanas: {${slug}_humanas}`,
        `Linguagens e Códigos: {${slug}_linguagens}`,
        `Redação: {${slug}_redacao}`,
      ].join("\n");

      const series = chart.series.push(
        am5xy.ColumnSeries.new(root, {
          name,
          stacked: true,
          xAxis,
          yAxis,
          valueYField: fieldName,
          categoryXField: "year",
          fill: color,
          stroke: color,
        })
      );

      series.columns.template.setAll({
        width: am5.percent(90),
        tooltipY: am5.percent(10),
        tooltipText: tooltipText,
      });

      series.data.setAll(processed.data);
      series.appear();

      // Label interno com a média (fonte branca)
      series.bullets.push(() =>
        am5.Bullet.new(root, {
          sprite: am5.Label.new(root, {
            text: "{valueY}",
            fill: root.interfaceColors.get("alternativeText"),
            centerY: am5.p50,
            centerX: am5.p50,
            populateText: true,
            fontSize: 13,
          }),
        })
      );

      legend.data.push(series);
    };

    processed.races.forEach(({ name, slug }, idx) =>
      makeSeries(name, slug, `${slug}_value`, idx)
    );

    chart.appear(1000, 100);

    return () => {
      root.dispose();
    };
  }, [processed, loadingData]);

  const isReadyToDraw = uf !== "all" && selectedMunicipio && !loadingData && processed.data.length > 0;

  return (
    <DashboardCard>
      <DashboardCardHeader>
        <div className="flex flex-col gap-2">
          <DashboardCardTitle>Desempenho Histórico por Raça (Município)</DashboardCardTitle>
          <p className="text-sm text-muted-foreground">
            Selecione um estado (obrigatório) e um município para ver toda a série histórica por raça.
          </p>
        </div>
      </DashboardCardHeader>
      <DashboardCardContent className="space-y-4">
        <div className="flex flex-col lg:flex-row gap-3 lg:items-center lg:justify-between">
          <div className="flex flex-col sm:flex-row gap-3">
            {/* UF Selector */}
            <Popover open={openUf} onOpenChange={setOpenUf}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={openUf}
                  className="w-full sm:w-[240px] justify-between"
                >
                  <span className="flex items-center gap-2">
                    <MapPin className="h-4 w-4" />
                    {currentUfLabel}
                  </span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[240px] p-0">
                <Command>
                  <CommandInput placeholder="Buscar estado..." />
                  <CommandList>
                    <CommandEmpty>Estado não encontrado.</CommandEmpty>
                    <CommandGroup>
                      {UFS.map((item) => (
                        <CommandItem
                          key={item.value}
                          value={item.label}
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

            {/* Município Selector */}
            <Popover open={openCity} onOpenChange={setOpenCity}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={openCity}
                  disabled={uf === "all" || loadingCities || municipios.length === 0}
                  className="w-full sm:w-[260px] justify-between"
                >
                  <span className="flex items-center gap-2">
                    <Building2 className="h-4 w-4" />
                    {selectedMunicipio
                      ? selectedMunicipio
                      : loadingCities
                        ? "Carregando municípios..."
                        : uf === "all"
                          ? "Escolha o estado primeiro"
                          : "Selecione o município"}
                  </span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[260px] p-0">
                <Command>
                  <CommandInput placeholder="Buscar município..." />
                  <CommandList>
                    <CommandEmpty>Município não encontrado.</CommandEmpty>
                    <CommandGroup className="max-h-64 overflow-auto">
                      {municipios.map((city) => (
                        <CommandItem
                          key={city}
                          value={city}
                          onSelect={(value) => {
                            setSelectedMunicipio(value);
                            setOpenCity(false);
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              selectedMunicipio === city ? "opacity-100" : "opacity-0"
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

          </div>

          {selectedMunicipio && uf !== "all" && (
            <div className="text-sm text-muted-foreground">
              {selectedMunicipio} • {currentUfLabel} • Todos os anos disponíveis
            </div>
          )}
        </div>

        {uf === "all" && (
          <div className="flex items-center justify-between gap-3 rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            <div>
              Selecione um estado para liberar a lista de municípios e carregar a série histórica.
            </div>
            <Button variant="outline" size="sm" onClick={() => setOpenUf(true)}>
              Escolher estado
            </Button>
          </div>
        )}

        {(loadingData || loadingCities) && (
          <Skeleton className="w-full h-[520px]" />
        )}

        {!loadingData && !loadingCities && uf !== "all" && selectedMunicipio && processed.data.length === 0 && (
          <div className="w-full h-[520px] flex items-center justify-center rounded-md border text-sm text-muted-foreground">
            Nenhum dado encontrado para {selectedMunicipio}/{uf}. Tente outro município.
          </div>
        )}

        {isReadyToDraw && <div ref={chartRef} className="w-full h-[520px]" />}
      </DashboardCardContent>
    </DashboardCard>
  );
}
