import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@stipendariet/ui';
import { Button, Input, Select, SelectItem, Form, Label, Badge } from '@stipendariet/ui';
import { api, request } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import { AlertCircle, CheckCircle, Clock, Menu, X } from 'lucide-react';

interface PromptVersion {
  id: number;
  name: string;
  version: string;
  is_production: boolean;
  created_at: string | null;
  avg_confidence: number;
  field_completeness: number;
  runs_count: number;
}

interface PromptMetrics {
  avg_confidence: number;
  field_completeness: number;
  runs_count: number;
}

const EnrichmentPromptsPage: React.FC = () => {
  const { user } = useAuth();
  const [prompts, setPrompts] = useState<PromptVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedName, setSelectedName] = useState<string>('');
  const [selectedVersion, setSelectedVersion] = useState<string>('');
  const [creatingVersion, setCreatingVersion] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showSetProduction, setShowSetProduction] = useState(false);
  const [metrics, setMetrics] = useState<Record<string, PromptMetrics>>({});
  const [editingMetrics, setEditingMetrics] = useState<{ name: string; version: string } | null>(null);

  const fetchPrompts = async () => {
    setLoading(true);
    try {
      const response = await request(api.get('/api/prompts/production'));
      setPrompts(response.data.prompts ?? []);
    } catch (e) {
      console.error('Failed to load prompts', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchMetrics = async (name: string) => {
    try {
      const response = await request(api.get(`/api/prompts/metrics?prompt_name=${name}`));
      setMetrics(prev => ({ ...prev, [name]: response.data.metrics }));
    } catch (e) {
      console.error('Failed to load metrics', e);
    }
  };

  useEffect(() => {
    fetchPrompts();
  }, []);

  const handleCreateVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingVersion(true);
    try {
      const versionInput = (e.target as any).elements.version.value;
      const templateText = (e.target as any).elements.template.value;
      const variablesInput = (e.target as any).elements.variables.value;
      const variables = variablesInput ? JSON.parse(variablesInput) : undefined;

      await request(api.post('/api/prompts', {
        name: selectedName,
        version: versionInput,
        content: templateText,
        template: selectedVersion || `${selectedVersion}.j2`,
        variables,
      }));

      setShowCreateModal(false);
      setCreatingVersion(false);
      fetchPrompts();
    } catch (e) {
      console.error('Failed to create prompt version', e);
      setCreatingVersion(false);
    }
  };

  const handleSetProduction = async (versionId: number, version: string) => {
    setShowSetProduction(false);
    try {
      await request(api.post('/api/prompts/set-production', {
        prompt_name: selectedName,
        version: version,
      }));
      fetchPrompts();
    } catch (e) {
      console.error('Failed to set production version', e);
    }
  };

  if (loading) {
    return (
      <Card className="h-full">
        <CardContent>
          <p className="text-muted-foreground">Laddar prompt-versioner...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Enrichment Prompts</CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <h2 className="text-xl font-bold mb-4">Prompt Management</h2>

          {/* Create Version Section */}
          <Card>
            <CardHeader>
              <CardTitle>Skapa ny version</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Form onSubmit={handleCreateVersion}>

                <div className="space-y-2">
                  <Label>Prompt namn</Label>
                  <Input
                    disabled
                    value={selectedName || ''}
                    placeholder="t.ex. extraction, validation, service_area"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Version (semver)</Label>
                  <Input
                    placeholder="t.ex. 1.0.0, 1.1.0"
                    defaultValue={selectedVersion || ''}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Jinja2 template innehåll</Label>
                  <Input
                    placeholder="Kopiera från validation.j2, extraction.j2 eller service_area.j2"
                    defaultValue=""
                    rows={8}
                  />
                </div>

                {selectedName && (
                  <div className="space-y-2">
                    <Label>Variabler (JSON)</Label>
                    <Input
                      placeholder='{"name": "...", "orgnr": "...", ...}'
                      defaultValue=""
                      rows={3}
                    />
                  </div>
                )}

                <Button type="submit" disabled={creatingVersion}>
                  {creatingVersion ? 'Skapar...' : 'Skapa version'}
                </Button>
              </Form>
            </CardContent>
          </Card>

          {/* Prompt List */}
          {selectedName && (
            <Card>
              <CardHeader>
                <CardTitle>Versioner för "{selectedName}"</CardTitle>
              </CardHeader>
              <CardContent>
                {prompts.map((prompt) => (
                  <div key={prompt.id} className="space-y-1 pt-2 border-b last:border-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{prompt.version}</span>
                      <Badge
                        variant={prompt.is_production ? "default" : "outline"}
                        className="text-[10px] px-2 py-0.5 rounded"
                      >
                        {prompt.is_production ? 'Production' : ''}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      Skapad: {prompt.created_at ? new Date(prompt.created_at).toLocaleDateString('sv-SE') : 'okänt'}
                    </div>

                    <div className="flex items-center gap-2 mt-1">
                      <Button
                        onClick={() => setSelectedVersion(prompt.version)}
                        variant="link"
                        size="sm"
                        className="text-primary"
                      >
                        Sätt som production
                      </Button>

      {prompt.is_production || (!prompts.some(p => p.name === selectedName && p.is_production))
        ? null
        : <Button
            variant="link"
            size="sm"
            className="text-danger"
            onClick={() => setShowSetProduction(true)}
          >
            Sätt production
          </Button>}

                      <Button
                        variant="link"
                        size="sm"
                        className="text-secondary"
                        onClick={() => fetchMetrics(selectedName)}
                      >
                        Visa mått
                      </Button>
                    </div>

                    {metrics[selectedName] && (
                      <div className="mt-2 small text-muted-foreground">
                        <div>Genomsnittlig konfidence: {metrics[selectedName].avg_confidence.toFixed(2)}</div>
                        <div>Fältfullständighet: {metrics[selectedName].field_completeness.toFixed(2)}%</div>
                        <div>Körningar: {metrics[selectedName].runs_count}</div>
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* No prompt selected */}
          {!selectedName && (
            <div className="text-center py-8 text-muted-foreground">
              Välj en prompt-ängobbe ovanför för att visa versioner och hantera dem.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default EnrichmentPromptsPage;