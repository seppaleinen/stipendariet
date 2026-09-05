import { Helmet } from "react-helmet-async";
import { useState, useEffect } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { Search, Bookmark, Sparkles, Loader2 } from "lucide-react";
import { Input } from "@stipendariet/ui";
import { Button } from "@stipendariet/ui";
import { Badge } from "@stipendariet/ui";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@stipendariet/ui";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@stipendariet/ui";
import { useAuth } from "@/contexts/AuthContext";

const ITEMS_PER_PAGE = 50;

export interface MatchingProps {
  saveMode?: boolean;
  generateMode?: boolean;
  matchId?: number;
}

export default function Matching({ saveMode, generateMode, matchId }: MatchingProps) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [grants, setGrants] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [countyFilter, setCountyFilter] = useState<string>("all");
  const [categories, setCategories] = useState<string[]>(["all"]);
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showAuthRedirect, setShowAuthRedirect] = useState(false);
  const [redirectAfterAuth, setRedirectAfterAuth] = useState(location.pathname);
  const [savedGrantIds, setSavedGrantIds] = useState<Set<string>>(new Set());

  const fetchMatchingGrants = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/foundations/matching`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          needs: searchQuery || undefined,
          category: categoryFilter !== "all" ? categoryFilter : undefined,
          county: countyFilter !== "all" ? countyFilter : undefined,
          limit: ITEMS_PER_PAGE,
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setGrants(data.grants);
      setCategories(["all", ...data.categories]);
    } catch (error) {
      console.error("Error loading matching grants:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatchingGrants();
  }, [searchQuery, categoryFilter, countyFilter]);

  const toggleSave = async (grantId: string, shouldSave: boolean) => {
    if (!isAuthenticated) {
      setRedirectAfterAuth(location.pathname);
      setShowAuthRedirect(true);
      return;
    }
    if (isSaving) return;
    setIsSaving(true);
    try {
      if (shouldSave) {
        // In a real app, we would call saveGrant API here
        console.log(`Saving grant ${grantId}`);
      } else {
        console.log(`Unsaving grant ${grantId}`);
      }
    } catch (error) {
      console.error("Error toggling saved grant", error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleGenerate = async (grantId: string) => {
    if (!isAuthenticated) {
      setRedirectAfterAuth(`/matching/generate/${grantId}`);
      setShowAuthRedirect(true);
      return;
    }
    if (isGenerating) return;
    setIsGenerating(true);
    try {
      // In a real app, we would call generateApplication API here
      console.log(`Generating application for grant ${grantId}`);
    } catch (error) {
      console.error("Error generating application", error);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAuthRedirect = () => {
    window.location.href = `/auth?redirect=${encodeURIComponent(redirectAfterAuth)}`;
  };

  const handleCloseAuthRedirect = () => {
    setShowAuthRedirect(false);
  };

  return (
    <>
      {showAuthRedirect && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 max-w-sm">
            <h3 className="text-lg font-semibold mb-2">Logga in för att spara</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Du måste logga in för att spara stipendier eller generera ansökningar.
            </p>
            <div className="flex gap-2">
              <Button onClick={handleAuthRedirect} className="flex-1">
                Logga in
              </Button>
              <Button variant="outline" onClick={handleCloseAuthRedirect}>
                Avbryt
              </Button>
            </div>
          </div>
        </div>
      )}
      
      <div className="container mx-auto py-8 px-4 space-y-6">
        <div className="flex flex-col gap-4">
          <h1 className="text-3xl font-bold">Matcha stipendier</h1>
          <p className="text-muted-foreground">
            Hitta stipendier som matchar din profil eller sök manuellt.
          </p>
        </div>
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
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
          <Select value={countyFilter} onValueChange={setCountyFilter}>
            <SelectTrigger className="w-full md:w-32">
              <SelectValue placeholder="Län" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Alla län</SelectItem>
              <SelectItem value="SE-K">Skåne</SelectItem>
              <SelectItem value="SE-AB">Stockholms län</SelectItem>
              <SelectItem value="SE-O">Västra Götaland</SelectItem>
              <SelectItem value="SE-C">Östergötlands län</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {loading ? (
          <div className="text-center py-12">Hittar matchningar...</div>
        ) : grants.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            Inga stipendier hittades. Prova att ändra dina sökkriterier.
          </div>
        ) : (
          <>
            <div className="text-sm text-muted-foreground">
              {grants.length} stipendier hittades
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
                          disabled={isSaving}
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
                  </CardContent>
                  <CardFooter>
                    <Button asChild className="flex-1">
                      <Link to={`/grants/${grant.id}`}>Läs mer</Link>
                    </Button>
                    {generateMode ? (
                      <Button
                        variant="outline"
                        onClick={() => handleGenerate(grant.id)}
                        disabled={isGenerating}
                      >
                        {isGenerating ? "Genererar..." : "Generera ansökan"}
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        onClick={() => handleGenerate(grant.id)}
                        disabled={isGenerating || !isAuthenticated}
                        title={!isAuthenticated ? "Logga in för att generera ansökan" : "Generera AI-assisterad ansökan"}
                      >
                        {isGenerating ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Genererar...
                          </>
                        ) : (
                          <>
                            <Sparkles className="h-4 w-4 mr-2" />
                            Generera ansökan
                          </>
                        )}
                      </Button>
                    )}
                  </CardFooter>
                </Card>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  );
}