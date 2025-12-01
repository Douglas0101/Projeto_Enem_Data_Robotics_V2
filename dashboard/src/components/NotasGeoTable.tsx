import { FileDown, FileText } from "lucide-react";
import type { TbNotasGeoRow } from "../types/dashboard";
import {
  DashboardCard,
  DashboardCardContent,
  DashboardCardHeader,
  DashboardCardTitle
} from "./ui/DashboardCard";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "./ui/table";
import { Button } from "./ui/button";
import { Skeleton } from "./ui/skeleton";

interface Props {
  rows: TbNotasGeoRow[];
  isLoading?: boolean; // Adicionamos prop de loading
}

export function NotasGeoTable({ rows, isLoading }: Props) {
  const hasRows = rows.length > 0;

  const formatScore = (value?: number | null) =>
    value === null || value === undefined ? "" : value.toFixed(1);

  const escapeForCsv = (value: string | number | null | undefined) => {
    if (value === null || value === undefined) return '""';
    const safe = String(value).replace(/"/g, '""');
    return `"${safe}"`;
  };

  const handleExportCsv = () => {
    if (!hasRows) return;
    const headers = [
      "Ano",
      "UF",
      "Município",
      "Natureza",
      "Humanas",
      "Linguagens",
      "Matemática",
      "Redação",
    ];

    const lines = rows.map((row) =>
      [
        row.ANO,
        row.SG_UF_PROVA,
        row.NO_MUNICIPIO_PROVA,
        formatScore(row.NOTA_CIENCIAS_NATUREZA_mean),
        formatScore(row.NOTA_CIENCIAS_HUMANAS_mean),
        formatScore(row.NOTA_LINGUAGENS_CODIGOS_mean),
        formatScore(row.NOTA_MATEMATICA_mean),
        formatScore(row.NOTA_REDACAO_mean),
      ]
        .map(escapeForCsv)
        .join(";")
    );

    const csvContent = [headers.join(";"), ...lines].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `detalhamento-municipal-${rows[0]?.ANO ?? "dados"}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const escapeHtml = (value: string | number | null | undefined) => {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  };

  const handleExportPdf = () => {
    if (!hasRows || typeof window === "undefined") return;
    const popup = window.open("", "_blank", "width=1024,height=768");
    if (!popup) return;

    const headerHtml = `
      <tr>
        <th>Ano</th>
        <th>UF</th>
        <th>Município</th>
        <th>Natureza</th>
        <th>Humanas</th>
        <th>Linguagens</th>
        <th>Matemática</th>
        <th>Redação</th>
      </tr>
    `;

    const rowsHtml = rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.ANO)}</td>
            <td>${escapeHtml(row.SG_UF_PROVA)}</td>
            <td>${escapeHtml(row.NO_MUNICIPIO_PROVA)}</td>
            <td>${escapeHtml(formatScore(row.NOTA_CIENCIAS_NATUREZA_mean))}</td>
            <td>${escapeHtml(formatScore(row.NOTA_CIENCIAS_HUMANAS_mean))}</td>
            <td>${escapeHtml(formatScore(row.NOTA_LINGUAGENS_CODIGOS_mean))}</td>
            <td>${escapeHtml(formatScore(row.NOTA_MATEMATICA_mean))}</td>
            <td>${escapeHtml(formatScore(row.NOTA_REDACAO_mean))}</td>
          </tr>
        `
      )
      .join("");

    const styles = `
      body { font-family: Inter, sans-serif; padding: 24px; color: #111827; }
      h2 { margin-bottom: 12px; }
      table { width: 100%; border-collapse: collapse; font-size: 12px; }
      th, td { border: 1px solid #e5e7eb; padding: 6px 8px; text-align: left; }
      th { background: #f3f4f6; font-weight: 600; }
      tr:nth-of-type(even) { background: #f9fafb; }
    `;

    popup.document.write(
      `
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>Detalhamento Municipal</title>
          <style>${styles}</style>
        </head>
        <body>
          <h2>Detalhamento Municipal</h2>
          <table>
            <thead>${headerHtml}</thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </body>
      </html>
    `
    );
    popup.document.close();
    popup.focus();
    popup.print();
  };

  if (isLoading) {
    return (
      <DashboardCard className="h-full w-full flex flex-col">
        <DashboardCardHeader className="flex-row items-center justify-between space-y-0 pb-4">
          <div className="space-y-1">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-3 w-64" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-8 w-24 rounded-full" />
          </div>
        </DashboardCardHeader>
        <DashboardCardContent className="p-0 flex-1 min-h-[45vh] overflow-hidden">
          <div className="h-full w-full overflow-hidden">
            <Table>
              <TableHeader className="sticky top-0 bg-background shadow-sm z-10">
                <TableRow className="hover:bg-transparent">
                  {[...Array(8)].map((_, i) => (
                    <TableHead key={i}>
                      <Skeleton className="h-4 w-16" />
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...Array(10)].map((_, i) => ( // 10 skeleton rows
                  <TableRow key={i}>
                    {[...Array(8)].map((_, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-20" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </DashboardCardContent>
      </DashboardCard>
    );
  }

  return (
    <DashboardCard className="h-full w-full flex flex-col">
      <DashboardCardHeader className="flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <DashboardCardTitle className="text-base font-medium text-foreground">
            Detalhamento Municipal
          </DashboardCardTitle>
          <p className="text-sm text-muted-foreground">
            Dados detalhados por município e disciplina
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-2"
              onClick={handleExportCsv}
              disabled={!hasRows}
            >
              <FileText className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Excel</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-2"
              onClick={handleExportPdf}
              disabled={!hasRows}
            >
              <FileDown className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">PDF</span>
            </Button>
          </div>
          <div className="inline-flex h-8 items-center rounded-full border bg-secondary px-2.5 text-xs font-semibold text-secondary-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2">
            {rows.length} registros
          </div>
        </div>
      </DashboardCardHeader>

      <DashboardCardContent className="p-0 flex-1 min-h-0 overflow-hidden">
        {!rows.length ? (
          <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
            Nenhum registro encontrado para os filtros selecionados.
          </div>
        ) : (
          <div className="h-full w-full overflow-auto">
            <Table>
              <TableHeader className="sticky top-0 bg-background shadow-sm z-10">
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-[80px]">Ano</TableHead>
                  <TableHead className="w-[60px]">UF</TableHead>
                  <TableHead>Município</TableHead>
                  <TableHead className="text-right">Natureza</TableHead>
                  <TableHead className="text-right">Humanas</TableHead>
                  <TableHead className="text-right">Linguagens</TableHead>
                  <TableHead className="text-right font-bold text-primary">Matemática</TableHead>
                  <TableHead className="text-right">Redação</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={`${row.ANO}-${row.SG_UF_PROVA}-${row.CO_MUNICIPIO_PROVA}`}>
                    <TableCell className="font-medium">{row.ANO}</TableCell>
                    <TableCell>{row.SG_UF_PROVA}</TableCell>
                    <TableCell className="max-w-[200px] truncate" title={row.NO_MUNICIPIO_PROVA}>
                      {row.NO_MUNICIPIO_PROVA}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {row.NOTA_CIENCIAS_NATUREZA_mean?.toFixed(1) ?? "–"}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {row.NOTA_CIENCIAS_HUMANAS_mean?.toFixed(1) ?? "–"}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {row.NOTA_LINGUAGENS_CODIGOS_mean?.toFixed(1) ?? "–"}
                    </TableCell>
                    <TableCell className="text-right font-semibold text-blue-600 dark:text-blue-400">
                      {row.NOTA_MATEMATICA_mean?.toFixed(1) ?? "–"}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {row.NOTA_REDACAO_mean?.toFixed(1) ?? "–"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </DashboardCardContent>
    </DashboardCard>
  );
}
