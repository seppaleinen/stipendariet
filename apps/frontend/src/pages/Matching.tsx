import { Helmet } from "react-helmet-async";
import { useState, useEffect } from "react";
import { Sparkles, MapPin, ArrowLeft, RefreshCw, Settings2 } from "lucide-react";
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
import { Switch } from "@stipendariet/ui";
import { Label } from "@stipendariet/ui";
import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { findMatchingFoundationsByProfile, MatchedFoundation } from "@/lib/api";
import { cleanTextForPreview } from "@/lib/utils";
import { useProfile } from "@/contexts/ProfileContext";
import { SITE_URL } from "@/lib/page-metadata";

const ITEMS_PER_PAGE = 20;
const MIN_SIMILARITY_THRESHOLD = 0.25; // 25% minimum match

export default function Matching() {
    const [results, setResults] = useState<MatchedFoundation[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [useGeoFilter, setUseGeoFilter] = useState(true);
    // Explicitly track if a search has been initiated for the CURRENT active profile
    // We can use a simple boolean, but safer to maybe track "lastSearchedProfileId"
    const [lastSearchedProfileId, setLastSearchedProfileId] = useState<number | null>(null);
    
    const { isAuthenticated } = useAuth();
    const { activeProfile, isLoading: isProfileLoading } = useProfile();

    const hasProfileData = !!(activeProfile && (
        (activeProfile.lifeSituations && activeProfile.lifeSituations.length > 0) ||
        (activeProfile.healthConditions && activeProfile.healthConditions.length > 0) ||
        (activeProfile.occupations && activeProfile.occupations.length > 0) ||
        (activeProfile.supportPurposes && activeProfile.supportPurposes.length > 0) ||
        activeProfile.healthDetails
    ));

    // Auto-search if profile changes and has data
    useEffect(() => {
        if (isAuthenticated && activeProfile && hasProfileData && lastSearchedProfileId !== activeProfile.id) {
            findMatches();
        } else if (!activeProfile) {
            setResults([]);
            setLastSearchedProfileId(null);
        }
    }, [isAuthenticated, activeProfile?.id, hasProfileData]);

    const findMatches = async () => {
        if (!activeProfile?.id) return;
        
        setLoading(true);
        setError(null);
        
        try {
            const data = await findMatchingFoundationsByProfile(
                activeProfile.id,
                useGeoFilter,
                MIN_SIMILARITY_THRESHOLD,
                100 // limit
            );
            
            // Sort by similarity score descending
            data.sort((a, b) => b.similarity_score - a.similarity_score);
            setResults(data);
            setLastSearchedProfileId(activeProfile.id);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Kunde inte hitta matchningar");
        } finally {
            setLoading(false);
        }
    };

    // Show loading state while checking auth/profile
    if (isAuthenticated && isProfileLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]" role="status" aria-live="polite">
                <div className="text-muted-foreground">
                    <span className="sr-only">Laddar profilinformation, vänligen vänta</span>
                    Laddar...
                </div>
            </div>
        );
    }

    // Show auth prompt if not logged in
    if (!isAuthenticated) {
        return (
            <div className="max-w-2xl mx-auto text-center py-12 space-y-6">
                <Sparkles className="h-16 w-16 mx-auto text-primary" aria-hidden="true" />
                <h1 className="text-3xl font-bold">Hitta matchande stiftelser</h1>
                <p className="text-muted-foreground text-lg">
                    Logga in och fyll i din profil för att hitta stiftelser som matchar din situation.
                </p>
                <div className="flex gap-4 justify-center">
                    <Button asChild>
                        <Link to="/auth">Logga in</Link>
                    </Button>
                    <Button asChild variant="outline">
                        <Link to="/grants">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Tillbaka till stipendier
                        </Link>
                    </Button>
                </div>
            </div>
        );
    }

    // Show profile setup prompt if no profile or no data
    if (!activeProfile || !hasProfileData) {
        return (
            <div className="max-w-2xl mx-auto text-center py-12 space-y-6">
                <Settings2 className="h-16 w-16 mx-auto text-muted-foreground" aria-hidden="true" />
                <h1 className="text-3xl font-bold">Fyll i profilen för {activeProfile?.name || "att börja"}</h1>
                <p className="text-muted-foreground text-lg">
                    För att hitta matchande stiftelser behöver du fylla i information om situationen för {activeProfile?.name || "den valda profilen"}.
                </p>
                <div className="flex gap-4 justify-center">
                    <Button asChild>
                        <Link to="/profile-setup">Gå till profilsidan</Link>
                    </Button>
                    <Button asChild variant="outline">
                        <Link to="/grants">
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Tillbaka till stipendier
                        </Link>
                    </Button>
                </div>
            </div>
        );
    }

    const hasSearched = lastSearchedProfileId === activeProfile.id;

    return (
        <>
            <Helmet>
                <title>Matcha dina behov med rätt stipendier | StipendieAssistenten</title>
                <meta name="description" content="Låt vår AI hjälpa dig hitta stipendier som matchar dina och din familjs behov. Personliga förslag baserat på din profil." />
                <link rel="canonical" href={`${SITE_URL}/matching`} />
                <meta property="og:title" content="Matcha dina behov med rätt stipendier | StipendieAssistenten" />
                <meta property="og:description" content="Låt vår AI hjälpa dig hitta stipendier som matchar dina och din familjs behov." />
                <meta property="og:type" content="website" />
                <meta property="og:url" content={`${SITE_URL}/matching`} />
                <meta name="twitter:card" content="summary_large_image" />
                <meta name="twitter:site" content="@StipendieAss" />
            </Helmet>
            <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-2">
                        <Sparkles className="h-8 w-8 text-primary" aria-hidden="true" />
                        Matchande stiftelser
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Stiftelser som matchar <strong>{activeProfile.name}</strong>, rankade efter relevans
                    </p>
                </div>
                <Button asChild variant="outline">
                    <Link to="/grants">
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Alla stipendier
                    </Link>
                </Button>
            </div>

            {/* Controls */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 p-4 bg-muted/50 rounded-lg">
                <div className="flex items-center space-x-2">
                    <Switch
                        id="geo-filter"
                        checked={useGeoFilter}
                        onCheckedChange={setUseGeoFilter}
                    />
                    <Label htmlFor="geo-filter" className="flex items-center gap-1">
                        <MapPin className="h-4 w-4" />
                        Filtrera på geografiskt område
                    </Label>
                </div>
                <div className="flex-1" />
                <Button onClick={findMatches} disabled={loading} className="gap-2">
                    {loading ? (
                        <>
                            <RefreshCw className="h-4 w-4 animate-spin" />
                            Söker...
                        </>
                    ) : (
                        <>
                            <Sparkles className="h-4 w-4" />
                            {hasSearched ? "Sök igen" : "Hitta matchningar"}
                        </>
                    )}
                </Button>
            </div>

            {/* Error */}
            {error && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-lg" role="alert">
                    {error}
                </div>
            )}

            {/* Results */}
            {hasSearched && !loading && results.length === 0 && !error && (
                <div className="text-center py-12 text-muted-foreground" role="status" aria-live="polite">
                    <p className="text-lg mb-4">Inga matchande stiftelser hittades för {activeProfile.name}.</p>
                    <p className="text-sm">
                        Prova att {useGeoFilter ? "stänga av geografisk filtrering eller " : ""}
                        uppdatera profilen för att få fler resultat.
                    </p>
                    <Button asChild variant="outline" className="mt-4">
                        <Link to="/profile-setup">Redigera profil</Link>
                    </Button>
                </div>
            )}

            {results.length > 0 && (
                <>
                    <div className="text-sm text-muted-foreground">
                        {results.length} matchande stiftelser hittades
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {results.map((match) => (
                            <Card
                                key={match.foundation.id}
                                className="flex flex-col hover:shadow-lg transition-shadow border-primary/20"
                            >
                                <CardHeader>
                                    <div className="flex items-start justify-between mb-2">
                                        <Badge
                                            variant={match.similarity_score >= 0.5 ? "default" : "secondary"}
                                            className="font-semibold"
                                        >
                                            {Math.round(match.similarity_score * 100)}% match
                                        </Badge>
                                        {match.foundation.category && (
                                            <Badge variant="outline">{match.foundation.category}</Badge>
                                        )}
                                    </div>
                                    <CardTitle className="line-clamp-2">{match.foundation.name}</CardTitle>
                                </CardHeader>

                                <CardContent className="flex-1">
                                    <CardDescription className="line-clamp-4">
                                        {cleanTextForPreview(match.foundation.translated_purpose || match.foundation.summary) || "Ingen beskrivning"}
                                    </CardDescription>
                                </CardContent>

                                <CardFooter>
                                    <Button asChild className="w-full">
                                        <Link to={`/grants/foundation-${match.foundation.id}`}>Läs mer</Link>
                                    </Button>
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
