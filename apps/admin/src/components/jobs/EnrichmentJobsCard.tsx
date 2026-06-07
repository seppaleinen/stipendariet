import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { backendApi } from '@/lib/api';
import { EnrichmentStatus, FoundationSearchResult, EnrichmentDefaults } from '@/types/jobs';

// --- Bulk enrichment status + trigger ---

export const EnrichmentBulkCard: React.FC = () => {
  const [status, setStatus] = useState<EnrichmentStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const loadStatus = async () => {
    try {
      const response = await backendApi.get('/admin/enrich/status');
      setStatus(response.data);
    } catch (e) {
      console.error('Failed to load enrichment status', e);
    }
  };

  useEffect(() => { loadStatus(); }, []);

  const triggerEnrichment = async () => {
    setLoading(true);
    try {
      const response = await backendApi.post('/admin/enrich/start');
      setMessage(`Startad! ${response.data.enqueued} i kö.`);
      setTimeout(loadStatus, 2000);
    } catch {
      setMessage('Fel vid start');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader><CardTitle>Berikning (Pipeline)</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {status && (
          <div className="space-y-1 p-3 bg-muted/50 rounded-lg text-sm">
            <div className="flex justify-between">
              <span>Klara</span>
              <span className="text-green-600 font-medium">
                {status.counts.COMPLETED || 0} / {status.total} ({status.completed_percentage}%)
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-green-500 h-2 rounded-full" style={{ width: `${status.completed_percentage}%` }} />
            </div>
            {Object.entries(status.counts)
              .filter(([k]) => k !== 'COMPLETED')
              .map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs text-muted-foreground">
                  <span>{k}</span><span>{v as number}</span>
                </div>
              ))}
          </div>
        )}
        <div className="flex gap-2">
          <Button onClick={triggerEnrichment} disabled={loading}>Starta Bulk</Button>
          <Button variant="outline" onClick={loadStatus}>Uppdatera</Button>
        </div>
        {message && <p className="text-sm text-green-600 font-medium">{message}</p>}
      </CardContent>
    </Card>
  );
};

// --- Single-foundation test with collapsible prompt editor ---

export const EnrichmentTestCard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [foundationId, setFoundationId] = useState('');
  const [forceSearch, setForceSearch] = useState(false);
  const [singleResult, setSingleResult] = useState<unknown>(null);
  const [showPrompts, setShowPrompts] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<FoundationSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const [prompts, setPrompts] = useState<EnrichmentDefaults>({
    validation_system_prompt: '',
    validation_user_prompt: '',
    extraction_system_prompt: '',
    extraction_user_prompt: '',
    model: '',
  });

  useEffect(() => {
    backendApi.get('/admin/enrich/defaults')
      .then((r: any) => setPrompts(r.data))
      .catch((e: any) => console.error('Failed to load enrichment defaults', e));
  }, []);

  useEffect(() => {
    if (searchQuery.length < 3) { setSearchResults([]); return; }
    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const response = await backendApi.get(`/admin/foundations/search?q=${encodeURIComponent(searchQuery)}`);
        setSearchResults(response.data);
      } catch (e: any) {
        console.error('Search failed', e);
      } finally {
        setIsSearching(false);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const selectFoundation = (f: FoundationSearchResult) => {
    setFoundationId(f.id.toString());
    setSearchQuery(f.name);
    setSearchResults([]);
  };

  const testSingle = async () => {
    if (!foundationId) return;
    setLoading(true);
    setSingleResult(null);
    setMessage('');
    try {
      const response = await backendApi.post(`/admin/enrich/foundation/${foundationId}`, {
        force_search: forceSearch,
        validation_sys_prompt: prompts.validation_system_prompt,
        validation_usr_prompt: prompts.validation_user_prompt,
        extraction_sys_prompt: prompts.extraction_system_prompt,
        extraction_usr_prompt: prompts.extraction_user_prompt,
      });
      if (response.data.status === 'enqueued') {
        setMessage(`Jobb köat (ID: ${response.data.job_id.substring(0, 8)}...). Kolla status i Berikning-kortet.`);
      } else {
        setSingleResult(response.data);
      }
    } catch (e: any) {
      setSingleResult({ error: e.message });
      setMessage('Fel vid test-körning');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Testa Pipeline</CardTitle>
          <button
            onClick={() => setShowPrompts((p) => !p)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2"
          >
            {showPrompts ? 'Dölj prompts ▲' : 'Justera prompts ▼'}
          </button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">

        {/* Foundation search */}
        <div className="space-y-1 relative">
          <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
            Sök stiftelse
          </label>
          <div className="relative">
            <Input
              placeholder="Sök på namn (min 3 tecken)..."
              value={searchQuery}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
            />
            {isSearching && (
              <span className="absolute right-3 top-2 text-[10px] animate-pulse text-muted-foreground">
                Söker...
              </span>
            )}
          </div>
          {searchResults.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-popover border rounded-md shadow-lg max-h-48 overflow-auto">
              {searchResults.map((f) => (
                <button
                  key={f.id}
                  onClick={() => selectFoundation(f)}
                  className="w-full text-left p-2 hover:bg-muted text-xs truncate"
                >
                  <span className="font-medium">{f.name}</span>
                  <span className="ml-2 text-muted-foreground">({f.orgnr})</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Collapsible prompt editor */}
        {showPrompts && (
          <div className="grid grid-cols-2 gap-4 pt-2 border-t text-xs">
            <div className="space-y-3 border-r pr-4">
              <h4 className="font-bold text-primary uppercase tracking-wider text-[10px]">
                1. Validerings-steg
              </h4>
              <div className="space-y-1">
                <label className="text-muted-foreground">System Prompt</label>
                <textarea
                  className="w-full h-28 p-2 border rounded font-mono bg-muted/30 text-xs"
                  value={prompts.validation_system_prompt}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                    setPrompts((prev: EnrichmentDefaults) => ({ ...prev, validation_system_prompt: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1">
                <label className="text-muted-foreground">User Prompt</label>
                <textarea
                  className="w-full h-28 p-2 border rounded font-mono bg-muted/30 text-xs"
                  value={prompts.validation_user_prompt}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                    setPrompts((prev: EnrichmentDefaults) => ({ ...prev, validation_user_prompt: e.target.value }))
                  }
                />
              </div>
            </div>
            <div className="space-y-3">
              <h4 className="font-bold text-primary uppercase tracking-wider text-[10px]">
                2. Extraktions-steg
              </h4>
              <div className="space-y-1">
                <label className="text-muted-foreground">System Prompt</label>
                <textarea
                  className="w-full h-28 p-2 border rounded font-mono bg-muted/30 text-xs"
                  value={prompts.extraction_system_prompt}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                    setPrompts((prev: EnrichmentDefaults) => ({ ...prev, extraction_system_prompt: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1">
                <label className="text-muted-foreground">User Prompt</label>
                <textarea
                  className="w-full h-28 p-2 border rounded font-mono bg-muted/30 text-xs"
                  value={prompts.extraction_user_prompt}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                    setPrompts((prev: EnrichmentDefaults) => ({ ...prev, extraction_user_prompt: e.target.value }))
                  }
                />
              </div>
            </div>
          </div>
        )}

        {/* Run controls */}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={forceSearch}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForceSearch(e.target.checked)}
              />
              Forcera ny sökning
            </label>
            {foundationId && (
              <span className="text-xs text-muted-foreground font-mono">ID {foundationId}</span>
            )}
          </div>
          <Button onClick={testSingle} disabled={loading || !foundationId}>
            {loading ? 'Kör...' : 'Testa Pipeline'}
          </Button>
        </div>

        {message && <p className="text-sm text-green-600 font-medium">{message}</p>}

        {singleResult && (
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Resultat</p>
            <pre className="text-[10px] p-3 bg-slate-950 text-slate-50 rounded-lg overflow-auto max-h-80">
              {JSON.stringify(singleResult, null, 2)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Legacy combined export
export const EnrichmentJobsCard: React.FC = () => (
  <div className="space-y-4">
    <EnrichmentBulkCard />
    <EnrichmentTestCard />
  </div>
);
