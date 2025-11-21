import {
  Box,
  Heading,
  HStack,
  Select,
  Spinner,
  Text,
  VStack,
  Button,
  Input
} from "@chakra-ui/react";
import React from "react";
import {
  getAvailableYears,
  getNotasGeo,
  getNotasStats
} from "../api/dashboard";
import { NotasStatsCards } from "../components/NotasStatsCards";
import { NotasGeoTable } from "../components/NotasGeoTable";

export function DashboardPage() {
  const [years, setYears] = React.useState<number[]>([]);
  const [selectedYear, setSelectedYear] = React.useState<number | undefined>();
  const [selectedUf, setSelectedUf] = React.useState<string>("");
  const [minCount, setMinCount] = React.useState<number>(30);
  const [statsLoading, setStatsLoading] = React.useState(false);
  const [geoLoading, setGeoLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [statsRow, setStatsRow] = React.useState<any | null>(null);
  const [geoRows, setGeoRows] = React.useState<any[]>([]);

  React.useEffect(() => {
    let cancelled = false;
    async function loadYears() {
      try {
        const ys = await getAvailableYears();
        if (!cancelled) {
          setYears(ys);
          setSelectedYear(ys[ys.length - 1]); // ano mais recente
        }
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

  const handleRefresh = async () => {
    if (!selectedYear) {
      return;
    }
    setError(null);
    setStatsLoading(true);
    setGeoLoading(true);
    try {
      const [stats, geo] = await Promise.all([
        getNotasStats({ anoInicio: selectedYear, anoFim: selectedYear }),
        getNotasGeo({
          ano: selectedYear,
          uf: selectedUf || undefined,
          minCount,
          limit: 5000,
          page: 1
        })
      ]);
      setStatsRow(stats[0] ?? null);
      setGeoRows(geo);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setStatsLoading(false);
      setGeoLoading(false);
    }
  };

  React.useEffect(() => {
    if (selectedYear != null) {
      void handleRefresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedYear]);

  return (
    <VStack align="stretch" spacing={6}>
      <HStack spacing={4} align="flex-end">
        <Box>
          <Text fontSize="sm" mb={1}>
            Ano
          </Text>
          <Select
            value={selectedYear ?? ""}
            onChange={(e) =>
              setSelectedYear(
                e.target.value ? Number(e.target.value) : undefined
              )
            }
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </Select>
        </Box>
        <Box>
          <Text fontSize="sm" mb={1}>
            UF (opcional)
          </Text>
          <Input
            placeholder="SP, RJ, MG..."
            maxLength={2}
            value={selectedUf}
            onChange={(e) => setSelectedUf(e.target.value.toUpperCase())}
          />
        </Box>
        <Box>
          <Text fontSize="sm" mb={1}>
            Mín. participantes (amostra)
          </Text>
          <Input
            type="number"
            min={0}
            value={minCount}
            onChange={(e) => setMinCount(Number(e.target.value) || 0)}
          />
        </Box>
        <Button onClick={handleRefresh} colorScheme="blue">
          Atualizar
        </Button>
      </HStack>

      {error && (
        <Box>
          <Text color="red.500" fontSize="sm">
            {error}
          </Text>
        </Box>
      )}

      <Box>
        <HStack mb={2} spacing={2}>
          <Heading size="md">Estatísticas anuais</Heading>
          {statsLoading && <Spinner size="sm" />}
        </HStack>
        {statsRow ? (
          <NotasStatsCards row={statsRow} />
        ) : (
          <Text fontSize="sm" color="gray.500">
            Nenhuma estatística carregada ainda.
          </Text>
        )}
      </Box>

      <Box>
        <HStack mb={2} spacing={2}>
          <Heading size="md">Notas por UF/Município</Heading>
          {geoLoading && <Spinner size="sm" />}
        </HStack>
        <NotasGeoTable rows={geoRows} />
      </Box>
    </VStack>
  );
}
