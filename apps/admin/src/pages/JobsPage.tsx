import React, { useState } from 'react';
import { SyncFoundationsCard } from '@/components/jobs/SyncFoundationsCard';
import { TranslationBulkCard, EmbeddingsCard, TranslationTestCard } from '@/components/jobs/TranslationJobsCard';
import { EnrichmentBulkCard, EnrichmentTestCard } from '@/components/jobs/EnrichmentJobsCard';
import { SystemActionsCard } from '@/components/jobs/SystemActionsCard';
import { useActiveJobs } from '@/hooks/useActiveJobs';
import { useFoundationStats } from '@/hooks/useFoundationStats';

const TABS = ['Berikning', 'Sync & Översättning', 'Systemåtgärder'] as const;
type Tab = typeof TABS[number];

const JobsPage: React.FC = () => {
  const { activeJobs, refresh } = useActiveJobs();
  const [activeTab, setActiveTab] = useState<Tab>('Berikning');

  // Single shared foundation-stats fetcher/poller for all cards on this page.
  // Polls every ~10s only while a relevant background job is running.
  const hasActiveStatsJob = Boolean(
    activeJobs.sync_foundations || activeJobs.bulk_translation || activeJobs.bulk_embeddings
  );
  const { stats, reloadStats } = useFoundationStats({ poll: hasActiveStatsJob });

  // Refresh both active-job summary and stats when any tracked job completes.
  const handleJobComplete = () => {
    refresh();
    reloadStats();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Backend Jobs</h1>
        <p className="text-muted-foreground">
          Hantera bakgrundsjobb, översättningar och berikning av stiftelsedata.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex border-b">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === tab
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Berikning */}
      {activeTab === 'Berikning' && (
        <div className="grid gap-6 md:grid-cols-2">
          <EnrichmentBulkCard />
          <EnrichmentTestCard />
        </div>
      )}

      {/* Sync & Översättning */}
      {activeTab === 'Sync & Översättning' && (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="space-y-6">
            <SyncFoundationsCard
              activeJobId={activeJobs.sync_foundations?.task_id}
              onComplete={handleJobComplete}
              stats={stats}
            />
            <TranslationBulkCard
              activeJobId={activeJobs.bulk_translation?.task_id}
              onComplete={handleJobComplete}
              stats={stats}
            />
          </div>
          <div className="space-y-6">
            <EmbeddingsCard
              activeJobId={activeJobs.bulk_embeddings?.task_id}
              stats={stats}
            />
            <TranslationTestCard />
          </div>
        </div>
      )}

      {/* Systemåtgärder */}
      {activeTab === 'Systemåtgärder' && (
        <div className="max-w-md">
          <SystemActionsCard />
        </div>
      )}
    </div>
  );
};

export default JobsPage;
