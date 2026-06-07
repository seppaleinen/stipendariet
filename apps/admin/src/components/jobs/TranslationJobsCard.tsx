import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { backendApi } from '@/lib/api';
import { JobProgressState, ActionState, FoundationStats } from '@/types/jobs';
import { formatTimeRemaining } from '@/lib/utils';

// --- Shared stats hook ---

const useFoundationStats = () => {
  const [stats, setStats] = useState<FoundationStats | null>(null);

  const load = async () => {
    try {
      const response = await backendApi.get('/admin/foundation-stats');
      setStats(response.data);
    } catch (e) {
      console.error('Failed to load foundation stats', e);
    }
  };

  useEffect(() => { load(); }, []);

  return { stats, reloadStats: load };
};

// --- Bulk translation with progress ---

interface TranslationBulkCardProps {
  activeJobId?: string;
  onComplete?: () => void;
}

export const TranslationBulkCard: React.FC<TranslationBulkCardProps> = ({ activeJobId, onComplete }) => {
  const { stats, reloadStats } = useFoundationStats();
  const [state, setState] = useState<JobProgressState>({ loading: false });
  const [forceRetranslate, setForceRetranslate] = useState(false);

  const pollStatus = async (taskId: string) => {
    try {
      const response = await backendApi.get(`/admin/bulk-translation-status/${taskId}`);
      const data = response.data;
      if (data.status === 'completed' || data.status === 'failed') {
        setState({
          loading: false,
          progress: 100,
          message: data.status === 'completed'
            ? `Färdig! ${data.completed} översatta.`
            : `Fel: ${data.error}`,
        });
        reloadStats();
        if (onComplete) onComplete();
      } else {
        setState({
          loading: true,
          progress: data.progress || 0,
          completed: data.completed,
          total: data.total,
          estimatedSecondsRemaining: data.estimated_remaining_seconds,
        });
        setTimeout(() => pollStatus(taskId), 2000);
      }
    } catch {
      setState({ loading: false, error: 'Kunde inte hämta status' });
    }
  };

  useEffect(() => {
    if (activeJobId && !state.loading) {
      setState({ loading: true });
      pollStatus(activeJobId);
    }
  }, [activeJobId]);

  const trigger = async () => {
    setState({ loading: true });
    try {
      const response = await backendApi.post(
        `/admin/trigger-bulk-purpose-translation${forceRetranslate ? '?force=true' : ''}`
      );
      pollStatus(response.data.task_id);
    } catch (e: any) {
      setState({ loading: false, error: e.message });
    }
  };

  return (
    <Card>
      <CardHeader><CardTitle>Översätt Ändamål</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {stats && (
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Översatta</span>
              <span>{stats.translated} / {stats.total_foundations} ({stats.translation_percentage}%)</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-primary h-2 rounded-full" style={{ width: `${stats.translation_percentage}%` }} />
            </div>
          </div>
        )}
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={forceRetranslate}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForceRetranslate(e.target.checked)}
          />
          Tvinga om-översättning
        </label>
        <Button onClick={trigger} disabled={state.loading}>
          {state.loading ? 'Översätter...' : 'Starta Översättning'}
        </Button>
        {state.loading && (
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{state.progress?.toFixed(1)}%</span>
            <span>{formatTimeRemaining(state.estimatedSecondsRemaining)}</span>
          </div>
        )}
        {state.message && <p className="text-sm text-green-600">{state.message}</p>}
        {state.error && <p className="text-sm text-destructive">{state.error}</p>}
      </CardContent>
    </Card>
  );
};

// --- Embeddings generation ---

export const EmbeddingsCard: React.FC = () => {
  const { stats } = useFoundationStats();
  const [state, setState] = useState<ActionState>({ loading: false });

  const trigger = async () => {
    setState({ loading: true });
    try {
      await backendApi.post('/admin/trigger-bulk-embedding-generation');
      setState({ loading: false, message: 'Startad!' });
    } catch {
      setState({ loading: false, error: 'Kunde inte starta' });
    }
  };

  return (
    <Card>
      <CardHeader><CardTitle>Generera Embeddings</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {stats && (
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Embeddings</span>
              <span>{stats.embedded} / {stats.total_foundations} ({stats.embedding_percentage}%)</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-green-500 h-2 rounded-full" style={{ width: `${stats.embedding_percentage}%` }} />
            </div>
          </div>
        )}
        <Button onClick={trigger} disabled={state.loading}>
          {state.loading ? 'Startar...' : 'Starta'}
        </Button>
        {state.message && <p className="text-sm text-green-600">{state.message}</p>}
        {state.error && <p className="text-sm text-destructive">{state.error}</p>}
      </CardContent>
    </Card>
  );
};

// --- Single-foundation translation test ---

export const TranslationTestCard: React.FC = () => {
  const [foundationId, setFoundationId] = useState('');
  const [testModel, setTestModel] = useState('');
  const [testPrompt, setTestPrompt] = useState('');
  const [state, setState] = useState<ActionState>({ loading: false });

  useEffect(() => {
    backendApi.get('/admin/translation-defaults')
      .then((r: any) => {
        setTestModel(r.data.model || '');
        setTestPrompt(r.data.prompt_template || '');
      })
      .catch((e: any) => console.error('Failed to load translation defaults', e));
  }, []);

  const translate = async () => {
    if (!foundationId) return;
    setState({ loading: true });
    try {
      const params = new URLSearchParams();
      if (testModel) params.append('model', testModel);
      if (testPrompt) params.append('prompt', testPrompt);
      const response = await backendApi.post(
        `/admin/translate-foundation/${foundationId}?${params.toString()}`
      );
      setState({ loading: false, message: JSON.stringify(response.data, null, 2) });
    } catch (e: any) {
      setState({ loading: false, error: e.message });
    }
  };

  return (
    <Card>
      <CardHeader><CardTitle>Testa Översättning</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <Input
          placeholder="Modell"
          value={testModel}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTestModel(e.target.value)}
        />
        <textarea
          className="w-full h-20 p-2 text-xs border rounded bg-muted/30 font-mono"
          placeholder="Prompt-mall"
          value={testPrompt}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setTestPrompt(e.target.value)}
        />
        <div className="flex gap-2">
          <Input
            placeholder="Stiftelse-ID"
            value={foundationId}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFoundationId(e.target.value)}
            className="w-32"
          />
          <Button onClick={translate} disabled={state.loading || !foundationId}>Testa</Button>
        </div>
        {state.message && (
          <pre className="text-[10px] p-2 bg-muted rounded overflow-auto max-h-40">{state.message}</pre>
        )}
        {state.error && <p className="text-sm text-destructive">{state.error}</p>}
      </CardContent>
    </Card>
  );
};

// Legacy combined export
export const TranslationJobsCard: React.FC<TranslationBulkCardProps> = (props) => (
  <div className="space-y-4">
    <TranslationBulkCard {...props} />
    <EmbeddingsCard />
    <TranslationTestCard />
  </div>
);
