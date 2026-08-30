import { Helmet } from "react-helmet-async";

// Organization structured data (JSON-LD) for Knowledge Graph / entity optimization
const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "StipendieAssistenten",
  description:
    "Din guide till att hitta och ansöka om stipendier och bidrag för din familj.",
  url: "https://stipendieassistenten.labb.site",
  slogan: "Hitta och ansök om stipendier",
  // External profiles — Google Knowledge Graph uses these to link the entity
  // to its presence across the web. Replace URLs as real profiles come online.
  sameAs: [
    "https://x.com/StipendieAss",
    "https://www.facebook.com/stipendieassistenten",
    "https://www.instagram.com/stipendieassistenten",
    "https://www.linkedin.com/company/stipendieassistenten",
    "https://github.com/seppaleinen/stipendariet",
    "https://www.youtube.com/@StipendieAssistenten",
  ],
  foundingDate: "2024",
  areaServed: {
    "@type": "Country",
    name: "Sverige",
    alternateName: "SE",
  },
  knowsAbout: [
    "Swedish scholarships",
    "utbildningsstipendier",
    "familjestöd",
    "bidrag för privatpersoner",
    "stipendieansökan",
  ],
  knowsLanguage: [
    { "@type": "Language", name: "Swedish", alternateName: "sv" },
    { "@type": "Language", name: "English", alternateName: "en" },
  ],
};

// WebSite structured data with SearchAction for search engine optimization
const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "StipendieAssistenten",
  url: "https://stipendieassistenten.labb.site",
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: "https://stipendieassistenten.labb.site/grants?q={search_term_string}",
    },
    "query-input": "required name=search_term_string",
  },
};

export default function SEOHead() {
  return (
    <>
      <Helmet>
        <script type="application/ld+json">
          {JSON.stringify(organizationSchema)}
        </script>
        <script type="application/ld+json">
          {JSON.stringify(websiteSchema)}
        </script>
      </Helmet>
    </>
  );
}
