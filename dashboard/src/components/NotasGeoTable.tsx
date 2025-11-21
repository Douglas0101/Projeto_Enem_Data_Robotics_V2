import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Text
} from "@chakra-ui/react";
import type { TbNotasGeoRow } from "../types/dashboard";

interface Props {
  rows: TbNotasGeoRow[];
}

export function NotasGeoTable({ rows }: Props) {
  if (!rows.length) {
    return (
      <Box>
        <Text fontSize="sm" color="gray.500">
          Nenhum registro encontrado para os filtros selecionados.
        </Text>
      </Box>
    );
  }

  return (
    <Box overflowX="auto">
      <Table size="sm">
        <Thead>
          <Tr>
            <Th>Ano</Th>
            <Th>UF</Th>
            <Th>Município</Th>
            <Th isNumeric>CN (média)</Th>
            <Th isNumeric>CH (média)</Th>
            <Th isNumeric>LC (média)</Th>
            <Th isNumeric>MT (média)</Th>
            <Th isNumeric>RD (média)</Th>
          </Tr>
        </Thead>
        <Tbody>
          {rows.map((row) => (
            <Tr key={`${row.ANO}-${row.SG_UF_PROVA}-${row.CO_MUNICIPIO_PROVA}`}>
              <Td>{row.ANO}</Td>
              <Td>{row.SG_UF_PROVA}</Td>
              <Td>{row.NO_MUNICIPIO_PROVA}</Td>
              <Td isNumeric>{row.NOTA_CIENCIAS_NATUREZA_mean?.toFixed(1) ?? "–"}</Td>
              <Td isNumeric>{row.NOTA_CIENCIAS_HUMANAS_mean?.toFixed(1) ?? "–"}</Td>
              <Td isNumeric>{row.NOTA_LINGUAGENS_CODIGOS_mean?.toFixed(1) ?? "–"}</Td>
              <Td isNumeric>{row.NOTA_MATEMATICA_mean?.toFixed(1) ?? "–"}</Td>
              <Td isNumeric>{row.NOTA_REDACAO_mean?.toFixed(1) ?? "–"}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
}

