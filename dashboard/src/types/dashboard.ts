export interface TbNotasStatsRow {
  ANO: number;
  TOTAL_INSCRITOS: number;

  NOTA_CIENCIAS_NATUREZA_count: number;
  NOTA_CIENCIAS_NATUREZA_mean: number | null;
  NOTA_CIENCIAS_NATUREZA_std: number | null;
  NOTA_CIENCIAS_NATUREZA_min: number | null;
  NOTA_CIENCIAS_NATUREZA_median: number | null;
  NOTA_CIENCIAS_NATUREZA_max: number | null;

  NOTA_CIENCIAS_HUMANAS_count: number;
  NOTA_CIENCIAS_HUMANAS_mean: number | null;
  NOTA_CIENCIAS_HUMANAS_std: number | null;
  NOTA_CIENCIAS_HUMANAS_min: number | null;
  NOTA_CIENCIAS_HUMANAS_median: number | null;
  NOTA_CIENCIAS_HUMANAS_max: number | null;

  NOTA_LINGUAGENS_CODIGOS_count: number;
  NOTA_LINGUAGENS_CODIGOS_mean: number | null;
  NOTA_LINGUAGENS_CODIGOS_std: number | null;
  NOTA_LINGUAGENS_CODIGOS_min: number | null;
  NOTA_LINGUAGENS_CODIGOS_median: number | null;
  NOTA_LINGUAGENS_CODIGOS_max: number | null;

  NOTA_MATEMATICA_count: number;
  NOTA_MATEMATICA_mean: number | null;
  NOTA_MATEMATICA_std: number | null;
  NOTA_MATEMATICA_min: number | null;
  NOTA_MATEMATICA_median: number | null;
  NOTA_MATEMATICA_max: number | null;

  NOTA_REDACAO_count: number;
  NOTA_REDACAO_mean: number | null;
  NOTA_REDACAO_std: number | null;
  NOTA_REDACAO_min: number | null;
  NOTA_REDACAO_median: number | null;
  NOTA_REDACAO_max: number | null;
}

export interface TbNotasGeoRow {
  ANO: number;
  SG_UF_PROVA: string;
  CO_MUNICIPIO_PROVA: string;
  NO_MUNICIPIO_PROVA: string;
  INSCRITOS?: number;

  NOTA_CIENCIAS_NATUREZA_count: number;
  NOTA_CIENCIAS_NATUREZA_mean: number | null;
  NOTA_CIENCIAS_HUMANAS_count: number;
  NOTA_CIENCIAS_HUMANAS_mean: number | null;
  NOTA_LINGUAGENS_CODIGOS_count: number;
  NOTA_LINGUAGENS_CODIGOS_mean: number | null;
  NOTA_MATEMATICA_count: number;
  NOTA_MATEMATICA_mean: number | null;
  NOTA_REDACAO_count: number;
  NOTA_REDACAO_mean: number | null;
}

export interface TbNotasGeoUfRow {
  ANO: number;
  SG_UF_PROVA: string;
  INSCRITOS: number;

  NOTA_CIENCIAS_NATUREZA_mean: number | null;
  NOTA_CIENCIAS_HUMANAS_mean: number | null;
  NOTA_LINGUAGENS_CODIGOS_mean: number | null;
  NOTA_MATEMATICA_mean: number | null;
  NOTA_REDACAO_mean: number | null;
}

export interface TbNotasHistogramRow {
  ANO: number;
  DISCIPLINA: string;
  BIN_START: number;
  BIN_END: number;
  CONTAGEM: number;
}

