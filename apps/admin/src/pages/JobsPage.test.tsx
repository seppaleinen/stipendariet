import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import JobsPage from './JobsPage';

// -- Mock hooks --
vi.mock('@/hooks/useActiveJobs', () => ({
  useActiveJobs: () => ({
    activeJobs: {},
    loading: false,
    refresh: vi.fn(),
  }),
}));

vi.mock('@/hooks/useFoundationStats', () => ({
  useFoundationStats: () => ({
    stats: null,
    reloadStats: vi.fn(),
  }),
}));

// -- Mock card components --
vi.mock('@/components/jobs/EnrichmentJobsCard', () => ({
  EnrichmentBulkCard: () => <div data-testid="enrichment-bulk-card" />,
  EnrichmentTestCard: () => <div data-testid="enrichment-test-card" />,
}));

vi.mock('@/components/jobs/SyncFoundationsCard', () => ({
  SyncFoundationsCard: () => <div data-testid="sync-foundations-card" />,
}));

vi.mock('@/components/jobs/TranslationJobsCard', () => ({
  TranslationBulkCard: () => <div data-testid="translation-bulk-card" />,
  EmbeddingsCard: () => <div data-testid="embeddings-card" />,
  TranslationTestCard: () => <div data-testid="translation-test-card" />,
}));

vi.mock('@/components/jobs/SystemActionsCard', () => ({
  SystemActionsCard: () => <div data-testid="system-actions-card" />,
}));

const renderPage = () => render(<JobsPage />);

describe('JobsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // TC-J1: renders page heading and description
  it('renders page heading and description', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: 'Backend Jobs' })).toBeInTheDocument();
    expect(
      screen.getByText('Hantera bakgrundsjobb, översättningar och berikning av stiftelsedata.'),
    ).toBeInTheDocument();
  });

  // TC-J2: renders all three tab buttons
  it('renders all three tab buttons', () => {
    renderPage();

    expect(screen.getByRole('button', { name: 'Berikning' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sync & Översättning' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Systemåtgärder' })).toBeInTheDocument();
  });

  // TC-J3: defaults to Berikning tab
  it('defaults to Berikning tab with enrichment cards visible', () => {
    renderPage();

    expect(screen.getByTestId('enrichment-bulk-card')).toBeInTheDocument();
    expect(screen.getByTestId('enrichment-test-card')).toBeInTheDocument();
    expect(screen.queryByTestId('sync-foundations-card')).not.toBeInTheDocument();
  });

  // TC-J4: switches to Sync & Översättning tab
  it('switches to Sync & Översättning tab showing sync/translation/embeddings cards', () => {
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Sync & Översättning' }));

    expect(screen.getByTestId('sync-foundations-card')).toBeInTheDocument();
    expect(screen.getByTestId('translation-bulk-card')).toBeInTheDocument();
    expect(screen.getByTestId('embeddings-card')).toBeInTheDocument();
    expect(screen.getByTestId('translation-test-card')).toBeInTheDocument();
    expect(screen.queryByTestId('enrichment-bulk-card')).not.toBeInTheDocument();
  });

  // TC-J5: switches to Systemåtgärder tab
  it('switches to Systemåtgärder tab showing system-actions card', () => {
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Systemåtgärder' }));

    expect(screen.getByTestId('system-actions-card')).toBeInTheDocument();
    expect(screen.queryByTestId('enrichment-bulk-card')).not.toBeInTheDocument();
    expect(screen.queryByTestId('sync-foundations-card')).not.toBeInTheDocument();
  });

  // TC-J6: switches back to Berikning tab
  it('switches back to Berikning tab', () => {
    renderPage();

    // Go to Systemåtgärder first
    fireEvent.click(screen.getByRole('button', { name: 'Systemåtgärder' }));
    expect(screen.queryByTestId('enrichment-bulk-card')).not.toBeInTheDocument();

    // Switch back to Berikning
    fireEvent.click(screen.getByRole('button', { name: 'Berikning' }));
    expect(screen.getByTestId('enrichment-bulk-card')).toBeInTheDocument();
    expect(screen.getByTestId('enrichment-test-card')).toBeInTheDocument();
    expect(screen.queryByTestId('system-actions-card')).not.toBeInTheDocument();
  });

  // TC-J7: applies active styling to selected tab
  it('applies active styling to selected tab', () => {
    renderPage();

    const berikningTab = screen.getByRole('button', { name: 'Berikning' });
    // Default tab should be active
    expect(berikningTab.className).toContain('border-primary');
    expect(berikningTab.className).toContain('text-primary');
  });

  // TC-J8: applies inactive styling to non-selected tabs
  it('applies inactive styling to non-selected tabs', () => {
    renderPage();

    const syncTab = screen.getByRole('button', { name: 'Sync & Översättning' });
    // Should NOT have active classes
    expect(syncTab.className).toContain('border-transparent');
  });
});
