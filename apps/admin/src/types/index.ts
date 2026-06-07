export interface Scholarship {
  id: string;
  name: string;
  organization_name: string;
  description: string | null;
  requirements: string | null;
  amount: string | null;
  deadline: string | null;
  application_method: string | null;
  official_url: string | null;
  status: 'NEW' | 'NEEDS_REVIEW' | 'PUBLISHED' | 'FAILED';
  raw_scraped_content: string | null;
  embedding: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ScholarshipQueueItem {
  id: string;
  name: string;
  organization_name: string;
  status: 'NEW' | 'FAILED';
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}