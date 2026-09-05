import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@stipendariet/ui';
import { api, request } from '@/lib/api';
import { Plus, Pencil, Trash2, X } from 'lucide-react';
import type { EnrichmentSourceInDB, EnrichmentSourceCreate, EnrichmentSourceUpdate } from './types';

interface Filters {
  foundationId?: number | undefined;
  isOfficial?: boolean | undefined;
  sourceType?: string | undefined;
}

function EnrichmentSourcesPage() {
  const [sources, setSources] = useState<EnrichmentSourceInDB[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingSource, setEditingSource] = useState<EnrichmentSourceInDB | null>(null);

  const loadSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number | undefined> = {};
      if (filters.foundationId !== undefined) params.foundation_id = filters.foundationId;
      if (filters.isOfficial !== undefined) params.is_official = String(filters.isOfficial);
      if (filters.sourceType !== undefined) params.source_type = filters.sourceType;

      const response = await request(api.get<EnrichmentSourceInDB[]>('/admin/sources', params));
      setSources(response.data);
    } catch (err) {
      console.error('Failed to load sources:', err);
      setError('Failed to load sources');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const handleAddSource = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: EnrichmentSourceCreate = {
      url: formData.get('url') as string,
      is_official: formData.get('is_official') === 'on',
      confidence: parseFloat(formData.get('confidence') as string) || 0.5,
      source_type: (formData.get('source_type') as string) || null,
    };

    try {
      await request(api.post('/admin/sources', data));
      setShowAddForm(false);
      loadSources();
    } catch (err) {
      console.error('Failed to add source:', err);
    }
  };

  const handleUpdateSource = async (source: EnrichmentSourceInDB, e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: EnrichmentSourceUpdate = {
      url: (formData.get('url') as string) || source.url,
      is_official: formData.get('is_official') === 'on',
      confidence: parseFloat(formData.get('confidence') as string) || source.confidence,
      source_type: (formData.get('source_type') as string) || null,
    };

    try {
      await request(api.put(`/admin/sources/${source.id}`, data));
      setEditingSource(null);
      loadSources();
    } catch (err) {
      console.error('Failed to update source:', err);
    }
  };

  const handleDeleteSource = async (sourceId: number) => {
    if (!window.confirm('Are you sure you want to delete this source?')) {
      return;
    }
    try {
      await request(api.del(`/admin/sources/${sourceId}`));
      loadSources();
    } catch (err) {
      console.error('Failed to delete source:', err);
    }
  };

  const handleFilterChange = (key: keyof Filters, value: string | number | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const sourceTypeOptions = [
    { value: 'aggregator', label: 'Aggregator' },
    { value: 'official', label: 'Official' },
    { value: 'blog', label: 'Blog' },
    { value: 'directory', label: 'Directory' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Enrichment Sources</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Manage the web sources used during enrichment crawling
          </p>
        </div>
        <Button onClick={() => setShowAddForm(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Source
        </Button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Foundation ID</label>
              <input
                type="number"
                onChange={(e) =>
                  handleFilterChange('foundationId', e.target.value ? Number(e.target.value) : undefined)
                }
                className="w-full px-3 py-2 border rounded"
                placeholder="All"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Official</label>
              <select
                onChange={(e) =>
                  handleFilterChange('isOfficial', e.target.value ? e.target.value === 'true' : undefined)
                }
                className="w-full px-3 py-2 border rounded"
              >
                <option value="">All</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Source Type</label>
              <select
                onChange={(e) => handleFilterChange('sourceType', e.target.value || undefined)}
                className="w-full px-3 py-2 border rounded"
              >
                <option value="">All</option>
                {sourceTypeOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <Button
                variant="outline"
                onClick={() => setFilters({})}
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sources Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-muted-foreground">Loading sources...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">URL</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Foundation</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Official</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Confidence</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Type</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-background divide-y divide-gray-200">
                  {sources.map((source) => (
                    <tr key={source.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{source.id}</td>
                      <td className="px-6 py-4 text-sm">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline"
                        >
                          {source.url}
                        </a>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {source.foundation_id ?? '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span
                          className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            source.is_official
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {source.is_official ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{source.confidence}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">{source.source_type ?? '—'}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditingSource(source)}
                          className="gap-1"
                        >
                          <Pencil className="h-3 w-3" />
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteSource(source.id)}
                          className="gap-1 text-red-600 hover:text-red-800"
                        >
                          <Trash2 className="h-3 w-3" />
                          Delete
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {sources.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-6 py-4 text-center text-sm text-muted-foreground">
                        No sources found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Source Modal */}
      {showAddForm && (
        <Modal title="Add New Source" onClose={() => setShowAddForm(false)}>
          <form onSubmit={handleAddSource} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">URL</label>
              <input type="url" name="url" required className="w-full px-3 py-2 border rounded" />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" name="is_official" id="add-official" />
              <label htmlFor="add-official" className="text-sm">Official source</label>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Confidence (0.0–1.0)</label>
              <input
                type="number"
                name="confidence"
                step="0.1"
                min="0"
                max="1"
                defaultValue="0.5"
                className="w-full px-3 py-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Source Type</label>
              <select name="source_type" className="w-full px-3 py-2 border rounded">
                <option value="">None</option>
                {sourceTypeOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setShowAddForm(false)}>
                Cancel
              </Button>
              <Button type="submit">Add Source</Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Edit Source Modal */}
      {editingSource && (
        <Modal title="Edit Source" onClose={() => setEditingSource(null)}>
          <form onSubmit={(e) => handleUpdateSource(editingSource, e)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">URL</label>
              <input
                type="url"
                name="url"
                defaultValue={editingSource.url}
                className="w-full px-3 py-2 border rounded"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                name="is_official"
                id="edit-official"
                defaultChecked={editingSource.is_official}
              />
              <label htmlFor="edit-official" className="text-sm">Official source</label>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Confidence (0.0–1.0)</label>
              <input
                type="number"
                name="confidence"
                step="0.1"
                min="0"
                max="1"
                defaultValue={editingSource.confidence}
                className="w-full px-3 py-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Source Type</label>
              <select
                name="source_type"
                defaultValue={editingSource.source_type ?? ''}
                className="w-full px-3 py-2 border rounded"
              >
                <option value="">None</option>
                {sourceTypeOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setEditingSource(null)}>
                Cancel
              </Button>
              <Button type="submit">Save Changes</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

// Simple centered modal component
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md bg-background rounded-lg shadow-lg">
        <div className="flex items-center justify-between border-b px-5 py-3">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export default EnrichmentSourcesPage;
