import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { Button } from "@stipendariet/ui";
import { SITE_URL, DEFAULT_OG_IMAGE } from "@/lib/page-metadata";
import FAQSchema, { FAQSection } from "@/components/FAQSchema";
import {
  GrantSearchBar,
  GrantsResults,
  useGrantsList,
  useSavedGrants,
} from "@/features/grants";

export default function Grants() {
  const list = useGrantsList();
  const saved = useSavedGrants();

  return (
    <>
      <Helmet>
        <title>Stipendier och Bidrag - Sök bland hundratals stipendier | StipendieAssistenten</title>
        <meta name="description" content="Utforska och sök bland hundratals stipendier och bidrag. Filter och sortering för att hitta rätt stipendium för din familj." />
        <link rel="canonical" href={`${SITE_URL}/grants`} />
        <link rel="alternate" hrefLang="sv-SE" href={`${SITE_URL}/grants`} />
        <link rel="alternate" hrefLang="x-default" href={`${SITE_URL}/grants`} />
        <meta property="og:title" content="Stipendier och Bidrag | StipendieAssistenten" />
        <meta property="og:description" content="Utforska och sök bland hundratals stipendier och bidrag." />
        <meta property="og:type" content="website" />
        <meta property="og:url" content={`${SITE_URL}/grants`} />
        <meta property="og:image" content={DEFAULT_OG_IMAGE} />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
            <meta property="og:image:alt" content="Stipendier och Bidrag | StipendieAssistenten" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:site" content="@StipendieAss" />
        <script type="application/ld+json">
            {JSON.stringify({
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                itemListElement: [
                    { "@type": "ListItem", position: 1, name: "Hem", item: SITE_URL },
                    { "@type": "ListItem", position: 2, name: "Hitta stipendier", item: `${SITE_URL}/grants` },
                ],
            })}
        </script>
      </Helmet>
      <FAQSchema topic="search" />
      {/* Breadcrumb */}
      <nav aria-label="Brödsmula">
        <ol className="flex items-center gap-2 text-sm text-muted-foreground">
          <li><Link to="/">Hem</Link></li>
          <li aria-hidden="true">›</li>
          <li aria-current="page">Hitta stipendier</li>
        </ol>
      </nav>
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

          <GrantSearchBar
            searchQuery={list.searchQuery}
            onSearchChange={list.setSearchQuery}
            categoryFilter={list.categoryFilter}
            onCategoryChange={list.setCategoryFilter}
            categories={list.categories}
          />

          <GrantsResults
            grants={list.grants}
            totalCount={list.totalCount}
            loading={list.loading}
            loadingMore={list.loadingMore}
            hasMore={list.hasMore}
            savedGrantIds={saved.savedGrantIds}
            savingIds={saved.savingIds}
            onSaveToggle={saved.toggleSave}
            loadMore={list.loadMore}
          />
        </div>

        {/* FAQ Section */}
        <FAQSection topic="search" />
      </div>
    </>
  );
}