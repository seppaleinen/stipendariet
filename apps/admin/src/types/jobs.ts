export type ActionState = {
  loading: boolean;
  message?: string;
  error?: string;
};

export type JobProgressState = {
  loading: boolean;
  message?: string;
  error?: string;
  progress?: number;
  completed?: number;
  total?: number;
  estimatedSecondsRemaining?: number | null;
};

export type FoundationStats = {
  total_foundations: number;
  translated: number;
  untranslated: number;
  embedded: number;
  not_embedded: number;
  translation_percentage: number;
  embedding_percentage: number;
};

export type EnrichmentStatus = {
  total: number;
  counts: Record<string, number>;
  completed_percentage: number;
  failed_count: number;
  remaining: number;
};

export type EnrichmentDetail = {
  id: number;
  name: string;
  status: string;
  last_run: string | null;
  error: string | null;
  website_url: string | null;
  application_deadline: string | null;
  application_start: string | null;
  application_method: string | null;
};

export type ActiveJob = {
  task_id: string;
  status: string;
} | null;

export type ActiveJobsSummary = Record<string, ActiveJob>;

export type FoundationSearchResult = {
  id: number;
  name: string;
  orgnr: string | null;
};

export type EnrichmentDefaults = {
  validation_system_prompt: string;
  validation_user_prompt: string;
  extraction_system_prompt: string;
  extraction_user_prompt: string;
  model: string;
};
