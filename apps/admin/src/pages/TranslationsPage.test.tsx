import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TranslationsPage from './TranslationsPage';
import { api, request } from '@/lib/api';
import type { PaginatedFoundationsTranslationResponse } from '@stipendariet/types';

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  request: vi.fn(async (promise) => {
    const result = await promise;
    return { data: result.data };
  }),
}));

const RESPONSE: PaginatedFoundationsTranslationResponse = {
  total: 2,
  page: 1,
  page_size: 50,
  items: [
    {
      id: 1,
      foundation_id: 100,
      name: 'Fond A',
      orgnr: '123456-7890',
      purpose: 'Att främja barns utbildning',
      translated_purpose: 'Främja barns utbildning',
      summary: null,
      address: 'Gata 1',
      postnr: '12345',
      postort: 'Stockholm',
      county_code: '01',
      municipality_code: '0180',
      parsed_service_area: {
        municipality_code: '0180',
        county_code: '01',
        municipality_name: 'Stockholm',
        county_name: 'Stockholms län',
        source_text: 'verkar i Stockholms län',
        confidence: 'high',
      },
      category: null,
      last_updated: '2024-01-01',
    },
    {
      id: 2,
      foundation_id: 200,
      name: 'Fond B',
      orgnr: '222222-2222',
      purpose: 'Att dela ut stipendier',
      translated_purpose: null,
      summary: null,
      address: null,
      postnr: null,
      postort: 'Göteborg',
      county_code: '14',
      municipality_code: '1480',
      parsed_service_area: null,
      category: null,
      last_updated: '2024-01-02',
    },
  ],
};

const renderPage = () =>
  render(
    <TranslationsPage />
  );

describe('TranslationsPage', () => {
  beforeEach(() => {
    (api.get as any).mockResolvedValue({ data: RESPONSE });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('fetches the translation list on mount and renders one row per foundation', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Fond A')).toBeInTheDocument();
      expect(screen.getByText('Fond B')).toBeInTheDocument();
    });

    expect(api.get).toHaveBeenCalledTimes(1);
    expect(api.get).toHaveBeenCalledWith('/admin/foundations/translations', { page: 1, page_size: 50, status: 'all' });
  });

  it('shows translation status for each foundation', async () => {
    renderPage();

    await waitFor(() => {
      // "Översatta" is the filter label; the per-row badge is "Översatt" (no 'a').
      expect(screen.getByText('Översatt')).toBeInTheDocument();
      // "Saknar översättning" appears both as the filter button and as Fond B's badge.
      expect(screen.getAllByText('Saknar översättning').length).toBeGreaterThanOrEqual(2);
    });
  });

  it('expands a row to show original and translated text side by side', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Fond A')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Fond A'));

    await waitFor(() => {
      // Both original and translated text present in the expanded panel
      expect(screen.getByText('Att främja barns utbildning')).toBeInTheDocument();
      expect(screen.getByText('Främja barns utbildning')).toBeInTheDocument();
    });
    // Parsed metadata names shown (Stockholm appears in row column + metadata panel)
    expect(screen.getAllByText(/Stockholm/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Stockholms län').length).toBeGreaterThanOrEqual(1);
  });

  it('maps an empty translated_purpose to a "Saknar översättning" placeholder in the expanded panel', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Fond B')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Fond B'));

    await waitFor(() => {
      // The original purpose text is present
      expect(screen.getByText('Att dela ut stipendier')).toBeInTheDocument();
    });
    // "Saknar översättning" placeholder (badge) for the missing translation
    expect(screen.getAllByText('Saknar översättning').length).toBeGreaterThan(0);
  });
});
