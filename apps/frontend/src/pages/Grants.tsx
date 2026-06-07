import { Helmet } from "react-helmet-async";
import { useState, useEffect, useCallback } from "react";
import { Search, Bookmark, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  getGrants,
  getSavedGrants,
  saveGrant,
  removeSavedGrant,
} from "@/lib/api";
import { Grant } from "@/types/grants";
import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { SITE_URL } from "@/lib/page-metadata";

const ITEMS_PER_PAGE = 50;

export default function Grants() {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [skip, setSkip] = useState(0);
  const [savedGrantIds, setSavedGrantIds] = useState<Set<string>>(new Set());
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set());
  const [categories, setCategories] = useState<string[]>(["all"]);
  const { isAuthenticated } = useAuth();

  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load grants when filters change
  useEffect(() => {
    loadGrants(true);
  }, [debouncedSearch, categoryFilter]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchSavedGrants();
    } else {
      setSavedGrantIds(new Set());
    }
  }, [isAuthenticated]);

  const loadGrants = async (reset: boolean = false) => {
    const newSkip = reset ? 0 : skip;
    if (reset) {
      setLoading(true);
      setSkip(0);
    } else {
      setLoadingMore(true);
    }

    try {
      const response = await getGrants({
        search: debouncedSearch || undefined,
        category: categoryFilter !== "all" ? categoryFilter : undefined,
        skip: newSkip,
        limit: ITEMS_PER_PAGE,
      });

      if (reset) {
        setGrants(response.grants);
      } else {
        setGrants((prev) => [...prev, ...response.grants]);
      }
      setTotalCount(response.total);
      setHasMore(response.has_more);
      setSkip(newSkip + response.grants.length);

      // Extract categories from first page load
      if (reset && response.grants.length > 0) {
        const uniqueCategories = Array.from(
          new Set(response.grants.map((g) => g.category).filter(Boolean))
        );
        setCategories(["all", ...uniqueCategories]);
      }
    } catch (error) {
      console.error("Error loading grants:", error);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const loadMore = () => {
    if (!loadingMore && hasMore) {
      loadGrants(false);
    }
  };

  const fetchSavedGrants = async () => {
    const ids = await getSavedGrants();
    setSavedGrantIds(new Set(ids));
  };

  const toggleSave = async (grantId: string, shouldSave: boolean) => {
    if (savingIds.has(grantId)) return;
    if (!isAuthenticated) {
      alert("Logga in för att spara stipendier.");
      return;
    }

    setSavingIds(new Set(savingIds).add(grantId));
    try {
      if (shouldSave) {
        await saveGrant(grantId);
        const next = new Set(savedGrantIds);
        next.add(grantId);
        setSavedGrantIds(next);
      } else {
        await removeSavedGrant(grantId);
        const next = new Set(savedGrantIds);
        next.delete(grantId);
        setSavedGrantIds(next);
      }
    } catch (error) {
      console.error("Error toggling saved grant", error);
    } finally {
      const nextSaving = new Set(savingIds);
      nextSaving.delete(grantId);
      setSavingIds(nextSaving);
    }
  };

  // Infinite scroll
  useEffect(() => {
    const handleScroll = () => {
      if (
        window.innerHeight + document.documentElement.scrollTop >=
        document.documentElement.offsetHeight - 200 &&
        !loadingMore &&
        hasMore &&
        !loading
      ) {
        loadMore();
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [loadingMore, hasMore, loading]);

  return (
    <>
      <Helmet>
        <title>Stipendier och Bidrag - Sök bland hundratals stipendier | StipendieAssistenten</title>
        <meta name="description" content="Utforska och sök bland hundratals stipendier och bidrag. Filter och sortering för att hitta rätt stipendium för din familj." />
        <link rel="canonical" href={`${SITE_URL}/grants`} />
        <meta property="og:title" content="Stipendier och Bidrag | StipendieAssistenten" />
        <meta property="og:description" content="Utforska och sök bland hundratals stipendier och bidrag." />
        <meta property="og:type" content="website" />
        <meta property="og:url" content={`${SITE_URL}/grants`} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:site" content="@StipendieAss" />
      </Helmet>
      <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Stipendier och Bidrag</h1>
          <Button asChild className="gap-2">
            <Link to="/matching">
              <Sparkles className="h-4 w-4" />
              Hitta matchande
            </Link>
          </Button>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <label htmlFor="search-grants" className="sr-only">Sök stipendier</label>
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <Input
              id="search-grants"
              placeholder="Sök stipendier..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-full md:w-48">
              <SelectValue placeholder="Kategori" />
            </SelectTrigger>
            <SelectContent>
              {categories.map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {cat === "all" ? "Alla Kategorier" : cat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="text-center py-12 text-muted-foreground" role="status" aria-live="polite">
          <span className="sr-only">Laddar stipendier, vänligen vänta</span>
          Laddar stipendier...
        </div>
      ) : grants.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground" role="status" aria-live="polite">
          Inga stipendier hittades. Prova att ändra dina sökkriterier.
        </div>
      ) : (
        <>
          <div className="text-sm text-muted-foreground" role="status" aria-live="polite">
            {totalCount.toLocaleString("sv-SE")} stipendier hittades ({grants.length} visas)
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {grants.map((grant) => (
              <Card
                key={grant.id}
                className="flex flex-col hover:shadow-lg transition-shadow"
              >
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <Badge variant="secondary">{grant.category}</Badge>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        disabled={savingIds.has(grant.id)}
                        onClick={() =>
                          toggleSave(grant.id, !savedGrantIds.has(grant.id))
                        }
                        aria-label={savedGrantIds.has(grant.id) ? `Ta bort ${grant.title} från sparade` : `Spara ${grant.title}`}
                      >
                        {savedGrantIds.has(grant.id) ? (
                          <Bookmark className="h-4 w-4 fill-current" aria-hidden="true" />
                        ) : (
                          <Bookmark className="h-4 w-4" aria-hidden="true" />
                        )}
                      </Button>
                    </div>
                  </div>
                  <CardTitle className="line-clamp-2">{grant.title}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {grant.summary}
                  </CardDescription>
                </CardHeader>

                <CardContent className="flex-1">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Utgivare:</span>
                      <span className="font-medium">{grant.provider}</span>
                    </div>
                    {grant.amount && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Belopp:</span>
                        <span className="font-medium">{grant.amount}</span>
                      </div>
                    )}
                    {grant.deadline && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Deadline:</span>
                        <span className="font-medium">{grant.deadline}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-2 mt-4">
                    {grant.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </CardContent>

                <CardFooter>
                  <Button asChild className="w-full">
                    <Link to={`/grants/${grant.id}`}>Läs mer</Link>
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>

          {/* Load more */}
          {hasMore && (
            <div className="flex justify-center pt-4">
              <Button
                onClick={loadMore}
                disabled={loadingMore}
                variant="outline"
              >
                {loadingMore ? "Laddar fler..." : "Ladda fler"}
              </Button>
            </div>
          )}
        </>
      )}
      </div>
    </>
  );
}
