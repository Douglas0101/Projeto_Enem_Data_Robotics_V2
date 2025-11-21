import { Box, SimpleGrid, Stat, StatHelpText, StatLabel, StatNumber } from "@chakra-ui/react";
import type { TbNotasStatsRow } from "../types/dashboard";

interface Props {
  row: TbNotasStatsRow;
}

export function NotasStatsCards({ row }: Props) {
  const metrics = [
    {
      label: "Ciências da Natureza",
      mean: row.NOTA_CIENCIAS_NATUREZA_mean,
      count: row.NOTA_CIENCIAS_NATUREZA_count
    },
    {
      label: "Ciências Humanas",
      mean: row.NOTA_CIENCIAS_HUMANAS_mean,
      count: row.NOTA_CIENCIAS_HUMANAS_count
    },
    {
      label: "Linguagens e Códigos",
      mean: row.NOTA_LINGUAGENS_CODIGOS_mean,
      count: row.NOTA_LINGUAGENS_CODIGOS_count
    },
    {
      label: "Matemática",
      mean: row.NOTA_MATEMATICA_mean,
      count: row.NOTA_MATEMATICA_count
    },
    {
      label: "Redação",
      mean: row.NOTA_REDACAO_mean,
      count: row.NOTA_REDACAO_count
    }
  ];

  return (
    <SimpleGrid columns={{ base: 1, md: 3, lg: 5 }} spacing={4}>
      {metrics.map((m) => (
        <Box key={m.label} borderWidth="1px" borderRadius="lg" p={4}>
          <Stat>
            <StatLabel>{m.label}</StatLabel>
            <StatNumber>
              {m.mean != null ? m.mean.toFixed(1) : "–"}
            </StatNumber>
            <StatHelpText>{m.count.toLocaleString()} participantes</StatHelpText>
          </Stat>
        </Box>
      ))}
    </SimpleGrid>
  );
}

