import { apiClient } from "./client";
import type { TbNotasGeoRow, TbNotasStatsRow } from "../types/dashboard";

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
  ano?: number;
  uf?: string;
  minCount?: number;
  limit?: number;
  page?: number;
}

export async function getNotasGeo(
  params: NotasGeoParams
): Promise<TbNotasGeoRow[]> {
  const search = new URLSearchParams();
  if (params.ano != null) {
    search.set("ano", String(params.ano));
  }
  if (params.uf) {
    search.set("uf", params.uf);
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

