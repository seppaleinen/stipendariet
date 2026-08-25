import { useCallback, useEffect, useState } from 'react';
import { backendApi } from '@/lib/api';
import { FoundationStats } from '@/types/jobs';

/** Poll interval used while a relevant background job is running. */
export const FOUNDATION_STATS_POLL_INTERVAL_MS = 10_000;

interface UseFoundationStatsOptions {
  /** When true, poll /admin/foundation-stats every ~10s (i.e. while a relevant job runs). */
  poll?: boolean;
}

/**
 * Shared hook for foundation stats (/admin/foundation-stats).
 * Fetches once on mount; optionally polls at FOUNDATION_STATS_POLL_INTERVAL_MS
 * while `poll` is true. Instantiate ONCE (e.g. in the page) and pass `stats`
 * down to consumers so we never run multiple pollers against the same endpoint.
 */
export const useFoundationStats = ({ poll = false }: UseFoundationStatsOptions = {}) => {
  const [stats, setStats] = useState<FoundationStats | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const response = await backendApi.get('/admin/foundation-stats');
      setStats(response.data);
    } catch (e) {
      console.error('Failed to load foundation stats', e);
    }
  }, []);

  // Always fetch once on mount.
  useEffect(() => { loadStats(); }, [loadStats]);

  // While a relevant job is active, keep the numbers fresh.
  useEffect(() => {
    if (!poll) return;
    const interval = setInterval(loadStats, FOUNDATION_STATS_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [poll, loadStats]);

  return { stats, reloadStats: loadStats };
};
