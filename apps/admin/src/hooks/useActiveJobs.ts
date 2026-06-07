import { useState, useEffect } from 'react';
import { backendApi } from '@/lib/api';
import { ActiveJobsSummary } from '@/types/jobs';

export const useActiveJobs = () => {
  const [activeJobs, setActiveJobs] = useState<ActiveJobsSummary>({});
  const [loading, setLoading] = useState(true);

  const fetchActiveJobs = async () => {
    try {
      const response = await backendApi.get('/admin/active-jobs');
      setActiveJobs(response.data);
    } catch (error) {
      console.error('Failed to fetch active jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActiveJobs();
    const interval = setInterval(fetchActiveJobs, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  return { activeJobs, loading, refresh: fetchActiveJobs };
};
