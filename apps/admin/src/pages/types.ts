// --- frontend/apps/admin/src/pages/types.ts ---
export interface EnrichmentSourceInDB {
  id: number;
  foundation_id: number | null;
  url: string;
  is_official: boolean;
  confidence: number;
  source_type: string | null;
  last_validated: string | null;
  created_at: string | null;
}
export interface EnrichmentSourceCreate {
  url: string;
  is_official?: boolean;
  confidence?: number;
  source_type?: string | null;
}
export interface EnrichmentSourceUpdate {
  url?: string;
  is_official?: boolean;
  confidence?: number;
  source_type?: string | null;
}