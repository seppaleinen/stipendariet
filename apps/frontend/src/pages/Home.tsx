import { Helmet } from "react-helmet-async";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Search, User, Sparkles, MapPin } from "lucide-react";
import { Button } from "@stipendariet/ui";
import { Input } from "@stipendariet/ui";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@stipendariet/ui";
import { Badge } from "@stipendariet/ui";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@stipendariet/ui";
import { SITE_URL, DEFAULT_OG_IMAGE } from "@/lib/page-metadata";
import FAQSchema, { FAQSection } from "@/components/FAQSchema";
import { SWEDISH_REGIONS } from "@/data/swedish-regions";

// Example profile fixtures (static, cached vectors for demo)
const EXAMPLE_PROFILES = [
  {
    id: "student-malmo",
    name: "Student in Malmö",
    description: "Computer science student seeking education grants and housing support",
    county: "SE-K",
    matches: 12,
    tags: ["utbildning", "boende", "student"],
  },
  {
    id: "parent-stockholm",
    name: "Ensamstående förälder, Stockholm",
    description: "Ensam vårdnadshavare med barn som söker familjestöd och vårdbidrag",
    county: "SE-AB",
    matches: 8,
    tags: ["familj", "vård", "stockholm"],
  },
  {
    id: "retiree-goteborg",
    name: "Pensionär, Göteborg",
    description: "Pensionär söker kulturstipendier och resebidrag för äldre",
    county: "SE-O",
    matches: 5,
    tags: ["kultur", "resor", "pensionär"],
  },
  {
    id: "artist-uppsala",
    name: "Konstnär, Uppsala",
    description: "Visuell konstnär söker ateljéstöd och utställningsbidrag",
    county: "SE-C",
    matches: 7,
    tags: ["konst", "ateljé", "utställning"],
  }
];

export default function Home() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [countyFilter, setCountyFilter] = useState<string>("");

  const handleMatchClick = () => {
    if (searchQuery.trim() && !countyFilter) {
      // Scroll to county selector if no county selected
      const countySelector = document.querySelector('[data-testid="county-selector"]');
      countySelector?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    const params = new URLSearchParams();
    if (searchQuery.trim()) params.set('search', searchQuery);
    if (countyFilter && countyFilter !== 'all') params.set('county', countyFilter);

    navigate(`/matching?${params.toString()}`, { replace: true });
  };

  const handleExampleProfileClick = (profile: typeof EXAMPLE_PROFILES[0]) => {
    const params = new URLSearchParams();
    params.set('search', profile.description);
    if (profile.county && profile.county !== 'SE') {
      params.set('county', profile.county);
    }
    navigate(`/matching?${params.toString()}`, { replace: true });
  };

  return (
    <>
      <Helmet>
        <title>StipendieAssistenten - Hitta stipendier som matchar dig</title>
        <meta name="description" content="Beskriv din situation och hitta stipendier som passar dina behov. Gratis och snabbt." />
        <link rel="canonical" href={SITE_URL} />
        <meta property="og:title" content="StipendieAssistenten - Hitta stipendier som matchar dig" />
        <meta property="og:description" content="Beskriv din situation och hitta stipendier som passar dina behov." />
        <meta property="og:type" content="website" />
        <meta property="og:url" content={SITE_URL} />
        <meta property="og:image" content={DEFAULT_OG_IMAGE} />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
        <meta property="og:image:alt" content="StipendieAssistenten - Hitta stipendier som matchar dig" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:site" content="@StipendieAss" />
      </Helmet>

      <FAQSchema topic="general" />
      <div className="container mx-auto px-4 py-12 space-y-12">
        {/* Hero - Value proposition and matching entry point */}
        <section className="text-center space-y-6">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            Hitta stipendier som matchar dig
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Beskriv din situation och hitta stipendier som passar dina behov. Gratis, snabbt och personligt.
          </p>
        </section>

        {/* Match entry point - Primary CTA */}
        <section className="max-w-4xl mx-auto space-y-4">
          <div className="relative">
            <label htmlFor="self-desc-input" className="sr-only">Beskriv din situation</label>
            <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <Input
              id="self-desc-input"
              placeholder="Jag är en ensamstående förälder med två barn som söker..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-32"
              onKeyPress={(e) => e.key === 'Enter' && handleMatchClick()}
            />
            <Button
              onClick={handleMatchClick}
              className="absolute right-2 top-2 h-8 px-4"
              disabled={!searchQuery.trim()}
            >
              Matcha
            </Button>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 items-center justify-center">
            <span className="text-sm text-muted-foreground whitespace-nowrap">
              Eller välj län för geografisk filtrering:
            </span>
            <Select value={countyFilter} onValueChange={setCountyFilter} data-testid="county-selector">
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="Alla län" />
              </SelectTrigger>
              <SelectContent>
                {SWEDISH_REGIONS.map((county) => (
                  <SelectItem key={county.code} value={county.code}>
                    {county.name}
                  </SelectItem>
                ))}
                <SelectItem value="">Alla län</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </section>

        {/* Scroller - example profiles with pre-cached match counts */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold text-center">Exempel på profiler</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {EXAMPLE_PROFILES.map((profile) => (
              <Card
                key={profile.id}
                className="hover:shadow-lg transition-shadow cursor-pointer group"
                onClick={() => handleExampleProfileClick(profile)}
              >
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">{profile.name}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {profile.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Matchningar:</span>
                      <Badge variant="secondary">{profile.matches}</Badge>
                    </div>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {profile.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* FAQ Section */}
        <FAQSection topic="general" />
      </div>
    </>
  );
}