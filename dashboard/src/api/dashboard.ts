import { apiClient } from "./client";
import type {
  TbNotasGeoRow,
  TbNotasStatsRow,
  TbNotasGeoUfRow,
  TbNotasHistogramRow,
} from "../types/dashboard";

export async function getAvailableYears(): Promise<number[]> {
  return apiClient.get<number[]>("/v1/dashboard/anos-disponiveis");
}

export interface NotasStatsParams {
  anoInicio?: number;
  anoFim?: number;
}

export async function getNotasStats(
  params: NotasStatsParams
): Promise<TbNotasStatsRow[]> {
  const search = new URLSearchParams();
  if (params.anoInicio != null) {
    search.set("ano_inicio", String(params.anoInicio));
  }
  if (params.anoFim != null) {
    search.set("ano_fim", String(params.anoFim));
  }
  const query = search.toString();
  const path = query ? `/v1/dashboard/notas/stats?${query}` : "/v1/dashboard/notas/stats";
  return apiClient.get<TbNotasStatsRow[]>(path);
}

export interface NotasGeoParams {
  ano?: number | number[];
  uf?: string | string[];
  municipio?: string | string[];
  minCount?: number;
  limit?: number;
  page?: number;
}

export async function getNotasGeo(
  params: NotasGeoParams
): Promise<TbNotasGeoRow[]> {
  const search = new URLSearchParams();
  
  if (params.ano != null) {
    const anos = Array.isArray(params.ano) ? params.ano : [params.ano];
    anos.forEach(a => search.append("ano", String(a)));
  }
  
  if (params.uf) {
    const ufs = Array.isArray(params.uf) ? params.uf : [params.uf];
    ufs.forEach(u => {
      if (u !== 'all') search.append("uf", u);
    });
  }

  if (params.municipio) {
    const cities = Array.isArray(params.municipio) ? params.municipio : [params.municipio];
    cities.forEach(c => search.append("municipio", c));
  }
  
  if (params.minCount != null) {
    search.set("min_count", String(params.minCount));
  }
  if (params.limit != null) {
    search.set("limit", String(params.limit));
  }
  if (params.page != null) {
    search.set("page", String(params.page));
  }
  const query = search.toString();
  const path = query ? `/v1/dashboard/notas/geo?${query}` : "/v1/dashboard/notas/geo";
  return apiClient.get<TbNotasGeoRow[]>(path);
}

export async function getMunicipios(uf?: string): Promise<string[]> {
  const search = new URLSearchParams();
  if (uf && uf !== 'all') {
    search.set("uf", uf);
  }
  const query = search.toString();
  const path = query ? `/v1/dashboard/municipios?${query}` : "/v1/dashboard/municipios";
  return apiClient.get<string[]>(path);
}

export interface NotasGeoUfParams {
  ano?: number;
  minInscritos?: number;
  uf?: string;
}

export async function getNotasGeoUf(
  params: NotasGeoUfParams
): Promise<TbNotasGeoUfRow[]> {
  const search = new URLSearchParams();
  if (params.ano != null) {
    search.set("ano", String(params.ano));
  }
  if (params.minInscritos != null) {
    search.set("min_inscritos", String(params.minInscritos));
  }
  if (params.uf) {
    search.set("uf", params.uf);
  }
  const query = search.toString();
  const path = query
    ? `/v1/dashboard/notas/geo-uf?${query}`
    : "/v1/dashboard/notas/geo-uf";
  return apiClient.get<TbNotasGeoUfRow[]>(path);
}

export interface NotasHistogramParams {
  year: number;
  disciplina: string;
}

export async function getNotasHistograma(
  params: NotasHistogramParams
): Promise<TbNotasHistogramRow[]> {
  const search = new URLSearchParams();
  search.set("ano", String(params.year));
  search.set("disciplina", params.disciplina);
  const query = search.toString();
  const path = `/v1/dashboard/notas/histograma?${query}`;
  return apiClient.get<TbNotasHistogramRow[]>(path);
}

export interface TbRadarRow {
  metric: string;
  uf_mean: number | null;
  br_mean: number | null;
  best_uf_mean: number | null;
  full_mark: number;
}

export interface RadarParams {
  year: number;
  uf?: string;
}

export async function getRadarData(
  params: RadarParams
): Promise<TbRadarRow[]> {
  const search = new URLSearchParams();
  search.set("ano", String(params.year));
  if (params.uf && params.uf !== "all") {
    search.set("uf", params.uf);
  }
  const query = search.toString();
  return apiClient.get<TbRadarRow[]>(`/v1/dashboard/advanced/radar?${query}`);
}

export interface TbSocioRaceRow {
  ANO?: number;
  RACA: string;
  NOTA_MATEMATICA?: number;
  NOTA_CIENCIAS_NATUREZA?: number;
  NOTA_CIENCIAS_HUMANAS?: number;
  NOTA_LINGUAGENS_CODIGOS?: number;
  NOTA_REDACAO?: number;
  COUNT: number;
}

export interface TbSocioIncomeRow {
  CLASSE: string;
  LOW: number;
  Q1: number;
  MEDIAN: number;
  Q3: number;
  HIGH: number;
}

export interface SocioRaceParams {
  year?: number;
  uf?: string;
  municipio?: string;
}

export async function getSocioRace(
  params: SocioRaceParams
): Promise<TbSocioRaceRow[]> {
  const search = new URLSearchParams();
  if (params.year) {
    search.set("ano", String(params.year));
  }
  if (params.uf && params.uf !== "all") {
    search.set("uf", params.uf);
  }
  if (params.municipio) {
    search.set("municipio", params.municipio);
  }
  const query = search.toString();
  return apiClient.get<TbSocioRaceRow[]>(`/v1/dashboard/advanced/socioeconomic/race?${query}`);
}

export async function getSocioIncome(year: number): Promise<TbSocioIncomeRow[]> {
  return apiClient.get<TbSocioIncomeRow[]>(`/v1/dashboard/advanced/socioeconomic/income?ano=${year}`);
}
