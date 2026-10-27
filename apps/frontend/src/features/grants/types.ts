import type { Grant } from "@/types/grants";
import type { GrantsResponse } from "@stipendariet/types";
export type { Grant, GrantsResponse };

export interface GrantsQueryParams {
  search?: string;
  category?: string;
  skip?: number;
  limit?: number;
}

export interface GrantsFilterState {
  searchQuery: string;
  categoryFilter: string;
  categories: string[];
}