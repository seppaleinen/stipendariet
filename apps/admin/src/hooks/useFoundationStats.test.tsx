import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useFoundationStats, FOUNDATION_STATS_POLL_INTERVAL_MS } from './useFoundationStats';
import { backendApi } from '@/lib/api';
import { FoundationStats } from '@/types/jobs';

vi.mock('@/lib/api', () => ({
  backendApi: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const STATS: FoundationStats = {
  total_foundations: 42,
  translated: 10,
  untranslated: 32,
  embedded: 5,
  not_embedded: 37,
  translation_percentage: 23.8,
  embedding_percentage: 11.9,
};

describe('useFoundationStats', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    (backendApi.get as any).mockResolvedValue({ data: STATS });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('fetches once on mount and exposes the stats', async () => {
    // Real timers here: waitFor cannot tick under fake timers.
    vi.useRealTimers();
    const { result } = renderHook(() => useFoundationStats());

    await waitFor(() => {
      expect(result.current.stats).toEqual(STATS);
    });
    expect(backendApi.get).toHaveBeenCalledTimes(1);
    expect(backendApi.get).toHaveBeenCalledWith('/admin/foundation-stats');
  });

  it('does not poll when idle (poll defaults to false)', async () => {
    renderHook(() => useFoundationStats());

    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(FOUNDATION_STATS_POLL_INTERVAL_MS * 3);

    expect(backendApi.get).toHaveBeenCalledTimes(1);
  });

  it('polls every ~10s only while poll is true', async () => {
    const { rerender } = renderHook(
      ({ poll }: { poll?: boolean }) => useFoundationStats({ poll }),
      { initialProps: { poll: false } }
    );

    // Idle: single mount fetch.
    await vi.advanceTimersByTimeAsync(0);
    expect(backendApi.get).toHaveBeenCalledTimes(1);

    // Job becomes active -> interval starts.
    rerender({ poll: true });
    await vi.advanceTimersByTimeAsync(FOUNDATION_STATS_POLL_INTERVAL_MS);
    expect(backendApi.get).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(FOUNDATION_STATS_POLL_INTERVAL_MS);
    expect(backendApi.get).toHaveBeenCalledTimes(3);

    // Job finishes -> interval is cleared.
    rerender({ poll: false });
    await vi.advanceTimersByTimeAsync(FOUNDATION_STATS_POLL_INTERVAL_MS * 3);
    expect(backendApi.get).toHaveBeenCalledTimes(3);
  });

  it('exposes reloadStats for manual refresh after a triggered action', async () => {
    const { result } = renderHook(() => useFoundationStats());

    await vi.advanceTimersByTimeAsync(0);
    expect(backendApi.get).toHaveBeenCalledTimes(1);

    result.current.reloadStats();
    await vi.advanceTimersByTimeAsync(0);
    expect(backendApi.get).toHaveBeenCalledTimes(2);
  });
});
