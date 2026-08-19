import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SyncFoundationsCard } from './SyncFoundationsCard';
import { backendApi } from '@/lib/api';

// Mock the backendApi module
vi.mock('@/lib/api', () => ({
  backendApi: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('SyncFoundationsCard', () => {
  it('renders correctly in initial state', () => {
    render(<SyncFoundationsCard />);
    expect(screen.getByText('Synka Stiftelser')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Starta Sync/i })).toBeInTheDocument();
  });

  it('triggers sync and handles successful completion through polling', async () => {
    // 1. Mock trigger response
    (backendApi.post as any).mockResolvedValue({ data: { task_id: 'task-123' } });
    
    // 2. Mock status polling
    // First call: in progress
    (backendApi.get as any).mockResolvedValueOnce({
      data: {
        status: 'running',
        progress: 50,
        completed: 10,
        total: 20,
        estimated_remaining_seconds: 30,
      }
    });
    // Second call: completed
    (backendApi.get as any).mockResolvedValueOnce({
      data: {
        status: 'completed',
        progress: 100,
        completed: 20,
        total: 20,
        result: { created: 15, updated: 5, failed: 0 },
      }
    });

    render(<SyncFoundationsCard />);

    const startButton = screen.getByRole('button', { name: /Starta Sync/i });
    fireEvent.click(startButton);

    // Check loading state
    expect(screen.getByText(/Synkar.../i)).toBeInTheDocument();

    // Wait for completion message
    await waitFor(() => {
      expect(screen.getByText(/Färdig! 15 nya, 5 uppdaterade, 0 misslyckades/i)).toBeInTheDocument();
    }, { timeout: 5000 });
  });

  it('handles error during sync trigger', async () => {
    (backendApi.post as any).mockRejectedValue(new Error('API Error'));

    render(<SyncFoundationsCard />);
    const startButton = screen.getByRole('button', { name: /Starta Sync/i });
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(screen.getByText(/API Error/i)).toBeInTheDocument();
    });
  });

  it('handles error during polling', async () => {
    (backendApi.post as any).mockResolvedValue({ data: { task_id: 'task-123' } });
    (backendApi.get as any).mockRejectedValue(new Error('Polling failed'));

    render(<SyncFoundationsCard />);
    const startButton = screen.getByRole('button', { name: /Starta Sync/i });
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(screen.getByText(/Kunde inte hämta status/i)).toBeInTheDocument();
    });
  });
});
