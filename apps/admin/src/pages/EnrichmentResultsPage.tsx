import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { backendApi } from '@/lib/api';
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Search,
  FlaskConical,
  Eye,
  X,
} from 'lucide-react';

interface EnrichmentResult {
  id: number;
  name: string;
  status: string;
  last_run: string | null;
  error: string | null;
  website_url: string | null;
  application_deadline: string | null;
  application_start: string | null;
  application_method: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  who_can_apply: string | null;
  enrichment_notes: string | null;
}

interface TraceValidation {
  url: string;
  title: string;
  snippet: string;
  is_match: boolean;
  confidence: number;
  raw_llm_response: string | null;
  llm_error: string | null;
  prompt_used: string | null;
}

interface TracePage {
  url: string;
  type: string;
  size: number;
  preview: string;
}

interface TraceSource {
  url: string;
  is_aggregator: boolean;
  pages: TracePage[];
  extraction: Record<string, string | null> | null;
  fields_extracted: string[];
}

interface Trace {
  foundation_id: number;
  name: string;
  discovery: any[];
  validation: TraceValidation[];
  sources: TraceSource[];
  merged: Record<string, string | null> | null;
}

const STATUS_FILTERS = ['ALL', 'COMPLETED', 'NO_DATA', 'FAILED', 'no_valid_site', 'NO_CANDIDATES', 'PROCESSING', 'PENDING', 'UNPROCESSED'];

const statusConfig: Record<string, { label: string; icon: React.ReactNode; badgeClass: string }> = {
  COMPLETED: {
    label: 'Klar',
    icon: <CheckCircle className="h-4 w-4 text-green-500" />,
    badgeClass: 'bg-green-100 text-green-800 border-green-200',
  },
  FAILED: {
    label: 'Misslyckades',
    icon: <XCircle className="h-4 w-4 text-red-500" />,
    badgeClass: 'bg-red-100 text-red-800 border-red-200',
  },
  NO_DATA: {
    label: 'Ingen data',
    icon: <AlertTriangle className="h-4 w-4 text-orange-500" />,
    badgeClass: 'bg-orange-100 text-orange-800 border-orange-200',
  },
  no_valid_site: {
    label: 'Ingen hemsida',
    icon: <AlertTriangle className="h-4 w-4 text-orange-500" />,
    badgeClass: 'bg-orange-100 text-orange-800 border-orange-200',
  },
  NO_CANDIDATES: {
    label: 'Ej hittad',
    icon: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    badgeClass: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  },
  PROCESSING: {
    label: 'Bearbetar',
    icon: <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />,
    badgeClass: 'bg-blue-100 text-blue-800 border-blue-200',
  },
  PENDING: {
    label: 'Väntar',
    icon: <Clock className="h-4 w-4 text-yellow-500" />,
    badgeClass: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  },
  UNPROCESSED: {
    label: 'Obehandlad',
    icon: <Clock className="h-4 w-4 text-gray-400" />,
    badgeClass: 'bg-gray-100 text-gray-600 border-gray-200',
  },
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const config = statusConfig[status] ?? {
    label: status,
    icon: null,
    badgeClass: 'bg-gray-100 text-gray-600 border-gray-200',
  };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.badgeClass}`}>
      {config.icon}
      {config.label}
    </span>
  );
};

// --- Trace Panel ---
const FIELD_LABELS: Record<string, string> = {
  application_deadline: 'Sista ansökningsdag',
  application_open: 'Ansökan öppnar',
  how_to_apply: 'Ansökningsmetod',
  contact_email: 'E-post',
  contact_phone: 'Telefon',
  who_can_apply: 'Vem kan söka',
  notes: 'Övrigt',
};

const TracePanel: React.FC<{ foundationId: number; onClose: () => void }> = ({ foundationId, onClose }) => {
  const [trace, setTrace] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedVal, setExpandedVal] = useState<number | null>(null);
  const [expandedSource, setExpandedSource] = useState<number | null>(null);
  const [expandedPage, setExpandedPage] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    backendApi.get(`/admin/enrich/trace/${foundationId}`)
      .then(r => setTrace(r.data.trace))
      .catch(e => setError(e.response?.data?.detail ?? e.message))
      .finally(() => setLoading(false));
  }, [foundationId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b flex-shrink-0">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2">
              <FlaskConical className="h-5 w-5 text-primary" />
              Pipeline Trace
            </h2>
            {trace && <p className="text-sm text-muted-foreground">{trace.name} (ID {trace.foundation_id})</p>}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-auto p-4 space-y-4 flex-1">
          {loading && <p className="text-sm text-muted-foreground animate-pulse">Laddar trace...</p>}
          {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">{error}</div>}

          {trace && (
            <>
              {/* Discovery */}
              <Section title={`🔍 Discovery (${trace.discovery.length} kandidater)`}>
                <div className="space-y-1">
                  {trace.discovery.map((d, i) => (
                    <a key={i} href={d.url} target="_blank" rel="noopener noreferrer"
                      className="flex items-start gap-2 p-2 rounded hover:bg-muted text-xs group">
                      <ExternalLink className="h-3 w-3 mt-0.5 flex-shrink-0 text-muted-foreground group-hover:text-primary" />
                      <div>
                        <p className="font-medium text-foreground">{d.title || d.url}</p>
                        <p className="text-muted-foreground truncate">{d.url}</p>
                        {d.snippet && <p className="text-muted-foreground mt-0.5 line-clamp-2">{d.snippet}</p>}
                      </div>
                    </a>
                  ))}
                  {trace.discovery.length === 0 && <p className="text-xs text-muted-foreground italic">Inga kandidater hittades.</p>}
                </div>
              </Section>

              {/* Validation */}
              <Section title={`🤖 Validering (${trace.validation.length} URL:er)`}>
                <div className="space-y-2">
                  {trace.validation.map((v, i) => (
                    <div key={i} className={`rounded-lg border ${v.is_match ? 'border-green-300 bg-green-50' : 'border-muted bg-muted/30'}`}>
                      <button
                        className="w-full flex items-center gap-2 p-2 text-xs text-left"
                        onClick={() => setExpandedVal(expandedVal === i ? null : i)}
                      >
                        {v.is_match
                          ? <CheckCircle className="h-3.5 w-3.5 text-green-600 flex-shrink-0" />
                          : <XCircle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />}
                        <span className="flex-1 font-mono truncate">{v.url}</span>
                        <span className="text-muted-foreground font-semibold">{(v.confidence * 100).toFixed(0)}%</span>
                        {expandedVal === i ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      </button>

                      {expandedVal === i && (
                        <div className="px-3 pb-3 space-y-2 border-t border-muted">
                          {v.snippet && (
                            <div className="mt-2">
                              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Snippet från sökning</p>
                              <p className="text-xs">{v.snippet}</p>
                            </div>
                          )}
                          {v.llm_error && (
                            <div className="p-2 bg-red-50 rounded text-xs text-red-700">
                              <strong>LLM-fel:</strong> {v.llm_error}
                            </div>
                          )}
                          {v.raw_llm_response && (
                            <div>
                              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">LLM svar (rå JSON)</p>
                              <pre className="text-[10px] p-2 bg-slate-950 text-slate-100 rounded overflow-auto max-h-24">
                                {v.raw_llm_response}
                              </pre>
                            </div>
                          )}
                          {v.prompt_used && (
                            <div>
                              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Prompt (trunkerad)</p>
                              <pre className="text-[10px] p-2 bg-muted rounded overflow-auto max-h-32 whitespace-pre-wrap">
                                {v.prompt_used}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                  {trace.validation.length === 0 && <p className="text-xs text-muted-foreground italic">Ingen validering utfördes.</p>}
                </div>
              </Section>

              {/* Per-source crawl + extraction */}
              <Section title={`🕷️ Källor (${trace.sources.length} matchade)`}>
                {trace.sources.length === 0
                  ? <p className="text-xs text-muted-foreground italic">Inga matchande källor hittades.</p>
                  : (
                  <div className="space-y-3">
                    {trace.sources.map((src, i) => {
                      const hasExtraction = src.extraction && src.fields_extracted.length > 0;
                      const isOpen = expandedSource === i;
                      return (
                        <div key={i} className={`rounded-lg border ${hasExtraction ? 'border-green-300' : 'border-muted'}`}>
                          <button
                            className="w-full flex items-center gap-2 p-2.5 text-xs text-left"
                            onClick={() => setExpandedSource(isOpen ? null : i)}
                          >
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold flex-shrink-0 ${src.is_aggregator ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700'}`}>
                              {src.is_aggregator ? 'aggregator' : 'egen sida'}
                            </span>
                            <span className="flex-1 font-mono truncate text-muted-foreground">{src.url}</span>
                            {hasExtraction
                              ? <span className="text-green-600 font-semibold text-[10px]">{src.fields_extracted.length} fält</span>
                              : <span className="text-muted-foreground text-[10px]">ingen data</span>
                            }
                            {isOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                          </button>

                          {isOpen && (
                            <div className="px-3 pb-3 border-t border-muted space-y-3">
                              {/* Extracted fields summary */}
                              <div className="mt-2">
                                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Extraherade fält</p>
                                {src.extraction ? (
                                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                                    {Object.entries(FIELD_LABELS).map(([key, label]) => {
                                      const val = src.extraction![key];
                                      return (
                                        <div key={key} className="flex items-start gap-1.5 text-[10px]">
                                          {val
                                            ? <CheckCircle className="h-3 w-3 text-green-500 flex-shrink-0 mt-0.5" />
                                            : <XCircle className="h-3 w-3 text-muted-foreground/40 flex-shrink-0 mt-0.5" />}
                                          <span className={val ? 'text-foreground' : 'text-muted-foreground/50'}>
                                            <span className="font-medium">{label}:</span>{' '}
                                            {val ?? '–'}
                                          </span>
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <p className="text-xs text-muted-foreground italic">LLM returnerade inga fält.</p>
                                )}
                              </div>

                              {/* Pages crawled */}
                              {src.pages.length > 0 && (
                                <div>
                                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">{src.pages.length} sida(or) crawlade</p>
                                  <div className="space-y-1">
                                    {src.pages.map((pg, pi) => {
                                      const pageKey = `${i}-${pi}`;
                                      return (
                                        <div key={pi} className="rounded border bg-muted/30">
                                          <button
                                            className="w-full flex items-center gap-2 p-1.5 text-[10px] text-left"
                                            onClick={() => setExpandedPage(expandedPage === pageKey ? null : pageKey)}
                                          >
                                            <span className="px-1 py-0.5 bg-muted rounded font-mono">{pg.type}</span>
                                            <span className="flex-1 truncate text-muted-foreground font-mono">{pg.url}</span>
                                            <span className="text-muted-foreground">{(pg.size / 1000).toFixed(1)}kb</span>
                                            {expandedPage === pageKey ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                                          </button>
                                          {expandedPage === pageKey && pg.preview && (
                                            <div className="px-2 pb-2 border-t border-muted">
                                              <pre className="text-[10px] p-1.5 bg-muted rounded overflow-auto max-h-32 whitespace-pre-wrap mt-1">
                                                {pg.preview}
                                              </pre>
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </Section>

              {/* Merged result */}
              <Section title="📦 Sammanslaget resultat">
                {trace.merged ? (
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                    {Object.entries(FIELD_LABELS).map(([key, label]) => {
                      const val = trace.merged![key];
                      return (
                        <div key={key} className="flex items-start gap-1.5 text-xs">
                          {val
                            ? <CheckCircle className="h-3.5 w-3.5 text-green-500 flex-shrink-0 mt-0.5" />
                            : <XCircle className="h-3.5 w-3.5 text-muted-foreground/30 flex-shrink-0 mt-0.5" />}
                          <span>
                            <span className="font-medium text-foreground">{label}:</span>{' '}
                            <span className={val ? 'text-foreground' : 'text-muted-foreground/40'}>{val ?? '–'}</span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">Ingen data extraherades från någon källa.</p>
                )}
              </Section>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div>
    <h3 className="text-sm font-semibold mb-2">{title}</h3>
    {children}
  </div>
);

const ExpandableRow: React.FC<{ result: EnrichmentResult; onViewTrace: (id: number) => void }> = ({ result, onViewTrace }) => {
  const [expanded, setExpanded] = useState(false);
  const hasData = result.website_url || result.application_deadline || result.application_start ||
    result.application_method || result.contact_email || result.contact_phone ||
    result.who_can_apply || result.enrichment_notes;

  return (
    <>
      <tr
        className={`border-b transition-colors hover:bg-muted/30 cursor-pointer ${expanded ? 'bg-muted/20' : ''}`}
        onClick={() => setExpanded(!expanded)}
      >
        <td className="py-3 px-4">
          <div className="font-medium text-sm truncate max-w-xs">{result.name}</div>
          <div className="text-[10px] text-muted-foreground font-mono">ID {result.id}</div>
        </td>
        <td className="py-3 px-4"><StatusBadge status={result.status} /></td>
        <td className="py-3 px-4 text-xs text-muted-foreground">
          {result.last_run ? new Date(result.last_run).toLocaleString('sv-SE') : '—'}
        </td>
        <td className="py-3 px-4">
          {result.website_url ? (
            <a href={result.website_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
              onClick={(e) => e.stopPropagation()}>
              Öppna <ExternalLink className="h-3 w-3" />
            </a>
          ) : <span className="text-xs text-muted-foreground">—</span>}
        </td>
        <td className="py-3 px-4 text-right">
          <div className="flex items-center justify-end gap-2">
            <button
              className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              title="Visa pipeline-trace"
              onClick={(e) => { e.stopPropagation(); onViewTrace(result.id); }}
            >
              <Eye className="h-3.5 w-3.5" />
            </button>
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </div>
        </td>
      </tr>

      {expanded && (
        <tr className="bg-muted/10 border-b">
          <td colSpan={5} className="px-6 py-4">
            {result.error && (
              <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700 font-mono">
                <p className="font-semibold mb-1">Felmeddelande:</p>
                <p>{result.error}</p>
              </div>
            )}
            {hasData ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <DataField label="Hemsida" value={result.website_url} isLink />
                <DataField label="Sista ansökningsdag" value={result.application_deadline} />
                <DataField label="Ansökan öppnar" value={result.application_start} />
                <DataField label="Ansökningsmetod" value={result.application_method} />
                <DataField label="E-post" value={result.contact_email} />
                <DataField label="Telefon" value={result.contact_phone} />
                <DataField label="Vem kan söka" value={result.who_can_apply} />
                <DataField label="Övrigt" value={result.enrichment_notes} />
              </div>
            ) : !result.error && (
              <p className="text-sm text-muted-foreground italic">Ingen data extraherades. Klicka 👁 för att se pipeline-trace.</p>
            )}
          </td>
        </tr>
      )}
    </>
  );
};

const DataField: React.FC<{ label: string; value: string | null; isLink?: boolean }> = ({ label, value, isLink }) => (
  <div className="space-y-1">
    <p className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">{label}</p>
    {value ? (
      isLink ? (
        <a href={value} target="_blank" rel="noopener noreferrer"
          className="text-xs text-blue-600 hover:underline break-all flex items-center gap-1">
          {value.length > 40 ? value.substring(0, 40) + '…' : value}
          <ExternalLink className="h-3 w-3 flex-shrink-0" />
        </a>
      ) : <p className="text-xs font-medium">{value}</p>
    ) : <p className="text-xs text-muted-foreground italic">Saknas</p>}
  </div>
);

// --- Main Page ---
const EnrichmentResultsPage: React.FC = () => {
  const [results, setResults] = useState<EnrichmentResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [limit, setLimit] = useState(50);
  const [search, setSearch] = useState('');
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [traceFoundationId, setTraceFoundationId] = useState<number | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { limit };
      if (statusFilter !== 'ALL') params.status = statusFilter;
      const response = await backendApi.get('/admin/enrich/details', { params });
      setResults(response.data.foundations ?? []);
    } catch (e) {
      console.error('Failed to load enrichment results', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await backendApi.get('/admin/enrich/status');
      setSummary(response.data.counts ?? {});
    } catch (e) {
      console.error('Failed to load summary', e);
    }
  };

  useEffect(() => { fetchResults(); fetchSummary(); }, [statusFilter, limit]);

  const filtered = search
    ? results.filter(r => r.name.toLowerCase().includes(search.toLowerCase()) || r.id.toString().includes(search))
    : results;

  const totalByStatus = Object.entries(summary).sort(([, a], [, b]) => b - a);

  return (
    <div className="space-y-6">
      {traceFoundationId !== null && (
        <TracePanel foundationId={traceFoundationId} onClose={() => setTraceFoundationId(null)} />
      )}

      <div>
        <h1 className="text-2xl font-bold tracking-tight">Berikningsresultat</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Granska utfall och pipeline-trace för alla körda stiftelser.
        </p>
      </div>

      {/* Summary cards */}
      {totalByStatus.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {totalByStatus.map(([s, count]) => (
            <Card key={s}
              className={`cursor-pointer transition-all hover:shadow-md ${statusFilter === s ? 'ring-2 ring-primary' : ''}`}
              onClick={() => setStatusFilter(statusFilter === s ? 'ALL' : s)}>
              <CardContent className="p-3">
                <div className="mb-1"><StatusBadge status={s} /></div>
                <p className="text-2xl font-bold">{count}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-3 items-center">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <input type="text" placeholder="Sök på namn eller ID..." value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border rounded-md bg-background" />
            </div>
            <div className="flex flex-wrap gap-1.5">
              {STATUS_FILTERS.map(f => (
                <button key={f} onClick={() => setStatusFilter(f)}
                  className={`px-3 py-1.5 text-xs rounded-full border font-medium transition-colors ${
                    statusFilter === f
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-background hover:bg-muted border-input text-muted-foreground'
                  }`}>
                  {f === 'ALL' ? 'Alla' : (statusConfig[f]?.label ?? f)}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <select value={limit} onChange={e => setLimit(Number(e.target.value))}
                className="text-xs border rounded-md px-2 py-1.5 bg-background">
                {[25, 50, 100, 200].map(n => <option key={n} value={n}>{n} resultat</option>)}
              </select>
              <Button variant="outline" size="sm" onClick={fetchResults} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
                Uppdatera
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {loading ? 'Laddar...' : `${filtered.length} stiftelser`}
            <span className="ml-2 text-[10px] text-muted-foreground/60">• Klicka 👁 för att se pipeline-trace</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="py-3 px-4 text-left font-semibold">Stiftelse</th>
                  <th className="py-3 px-4 text-left font-semibold">Status</th>
                  <th className="py-3 px-4 text-left font-semibold">Senast kördes</th>
                  <th className="py-3 px-4 text-left font-semibold">Hemsida</th>
                  <th className="py-3 px-4" />
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-muted-foreground text-sm">
                      {loading ? 'Hämtar data...' : 'Inga resultat hittades.'}
                    </td>
                  </tr>
                ) : (
                  filtered.map(r => (
                    <ExpandableRow key={r.id} result={r} onViewTrace={setTraceFoundationId} />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default EnrichmentResultsPage;
