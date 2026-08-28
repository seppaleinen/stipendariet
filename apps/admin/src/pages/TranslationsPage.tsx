import React, { useCallback, useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
} from '@stipendariet/ui';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Languages,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { backendApi } from '@/lib/api';
import type {
  FoundationTranslationListItem,
  PaginatedFoundationsTranslationResponse,
} from '@stipendariet/types';

type TranslationStatus = 'all' | 'translated' | 'missing';

const STATUS_FILTERS: { value: TranslationStatus; label: string }[] = [
  { value: 'all', label: 'Alla' },
  { value: 'translated', label: 'Översatta' },
  { value: 'missing', label: 'Saknar översättning' },
];

const DEFAULT_PAGE_SIZE = 50;

const StatusBadge: React.FC<{ translated: boolean }> = ({ translated }) =>
  translated ? (
    <Badge variant="default" className="gap-1">
      <CheckCircle2 className="h-3 w-3" />
      Översatt
    </Badge>
  ) : (
    <Badge variant="secondary" className="gap-1">
      <XCircle className="h-3 w-3" />
      Saknar översättning
    </Badge>
  );

const MetadataField: React.FC<{ label: string; value: string | null }> = ({ label, value }) => (
  <div className="space-y-0.5">
    <p className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">{label}</p>
    <p className="text-xs font-medium break-words">{value || 'Saknas'}</p>
  </div>
);

/** Expandable row: shows the row data plus a side-by-side original | translated view. */
const ExpandableRow: React.FC<{ item: FoundationTranslationListItem }> = ({ item }) => {
  const [expanded, setExpanded] = useState(false);
  const hasTranslation = !!item.translated_purpose;
  const parsed = item.parsed_service_area;

  const translatedDisplay = hasTranslation
    ? item.translated_purpose
    : 'Saknar översättning';

  return (
    <>
      <tr
        className="border-b transition-colors hover:bg-muted/30 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="py-3 px-4">
          <div className="font-medium text-sm truncate max-w-xs">{item.name}</div>
          <div className="text-[10px] text-muted-foreground font-mono">
            {[item.orgnr, `ID ${item.id}`].filter(Boolean).join(' · ')}
          </div>
        </td>
        <td className="py-3 px-4 text-xs text-muted-foreground">
          {[item.postort, item.municipality_code && item.county_code
            ? `${item.municipality_code}/${item.county_code}`
            : null].filter(Boolean).join(', ') || '—'}
        </td>
        <td className="py-3 px-4 text-xs text-muted-foreground max-w-[220px]">
          {parsed
            ? [parsed.municipality_name, parsed.county_name].filter(Boolean).join(', ')
            : item.postort || '—'}
        </td>
        <td className="py-3 px-4">
          <StatusBadge translated={hasTranslation} />
        </td>
        <td className="py-3 px-4 text-right">
          <div className="flex items-center justify-end gap-2">
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </div>
        </td>
      </tr>

      {expanded && (
        <tr className="bg-muted/10 border-b">
          <td colSpan={5} className="px-6 py-4">
            <div className="space-y-4">
              {/* Parsed metadata */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <MetadataField label="Adress" value={item.address} />
                <MetadataField label="Postort" value={item.postort} />
                <MetadataField label="Kommun" value={parsed?.municipality_name ?? item.municipality_code} />
                <MetadataField label="Län" value={parsed?.county_name ?? item.county_code} />
                {parsed?.service_area_detail && (
                  <MetadataField label="Områdesdetalj" value={parsed.service_area_detail} />
                )}
                {parsed?.source_text && (
                  <MetadataField label="Källa" value={parsed.source_text} />
                )}
                {parsed?.confidence && (
                  <MetadataField label="Konfidens" value={parsed.confidence} />
                )}
                <MetadataField label="Kategori" value={item.category} />
              </div>

              {/* Side-by-side translation judging */}
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Languages className="h-4 w-4 text-muted-foreground" />
                    <h4 className="text-sm font-semibold">Original (äldre svenska)</h4>
                  </div>
                  <p className="text-sm whitespace-pre-wrap text-muted-foreground">
                    {item.purpose || 'Saknar purpose'}
                  </p>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Languages className="h-4 w-4 text-muted-foreground" />
                    <h4 className="text-sm font-semibold">Översättning</h4>
                  </div>
                  <p className={`text-sm whitespace-pre-wrap ${hasTranslation ? 'text-foreground' : 'text-muted-foreground italic'}`}>
                    {translatedDisplay}
                  </p>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
};

const TranslationsPage: React.FC = () => {
  const [items, setItems] = useState<FoundationTranslationListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<TranslationStatus>('all');
  const [loading, setLoading] = useState(false);

  const fetchPage = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        page,
        page_size: DEFAULT_PAGE_SIZE,
        status: statusFilter,
      };
      const response = await backendApi.get<PaginatedFoundationsTranslationResponse>(
        '/admin/foundations/translations',
        { params },
      );
      setItems(response.data.items ?? []);
      setTotal(response.data.total ?? 0);
    } catch (e) {
      console.error('Failed to load translations list', e);
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => { fetchPage(); }, [fetchPage]);

  const totalPages = Math.max(1, Math.ceil(total / DEFAULT_PAGE_SIZE));

  const handleFilterChange = (value: TranslationStatus) => {
    setStatusFilter(value);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-3xl font-bold">Översättningsgranskning</h1>
        </div>
        <p className="text-muted-foreground">
          Granska LLM-översättningar av stiftelsers ändamål — original text och översättning sida vid sida.
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-2 items-center">
            <div className="flex flex-wrap gap-1.5">
              {STATUS_FILTERS.map((f) => (
                <button
                  key={f.value}
                  onClick={() => handleFilterChange(f.value)}
                  className={`px-3 py-1.5 text-xs rounded-full border font-medium transition-colors ${
                    statusFilter === f.value
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-background hover:bg-muted border-input text-muted-foreground'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <Button variant="outline" size="sm" onClick={fetchPage} disabled={loading}>
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
            {loading ? 'Laddar...' : `${total} stiftelser`}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="py-3 px-4 text-left font-semibold">Stiftelse</th>
                  <th className="py-3 px-4 text-left font-semibold">Ort / koder</th>
                  <th className="py-3 px-4 text-left font-semibold">Verksamhetsområde</th>
                  <th className="py-3 px-4 text-left font-semibold">Status</th>
                  <th className="py-3 px-4" />
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-muted-foreground text-sm">
                      {loading ? 'Hämtar data...' : 'Inga resultat hittades.'}
                    </td>
                  </tr>
                ) : (
                  items.map((item) => <ExpandableRow key={item.id} item={item} />)
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Sida {page} av {totalPages} ({total} stiftelser)
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            Föregående
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Nästa
            <ArrowRight className="h-4 w-4 ml-1.5" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default TranslationsPage;
