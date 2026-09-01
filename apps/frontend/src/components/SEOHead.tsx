import { Helmet } from "react-helmet-async";
import { useLocation } from "react-router-dom";

const SITE_URL = "https://stipendieassistenten.labb.site";

// Organization structured data (JSON-LD) for Knowledge Graph / entity optimization
const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "StipendieAssistenten",
  description:
    "Din guide till att hitta och ansöka om stipendier och bidrag för din familj.",
  url: SITE_URL,
  slogan: "Hitta och ansök om stipendier",
  // External profiles — Google Knowledge Graph uses these to link the entity
  // to its presence across the web. Only verified URLs are included.
  sameAs: ["https://github.com/seppaleinen/stipendariet"],
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
  contactPoint: {
    "@type": "ContactPoint",
    contactType: "customer support",
    url: `${SITE_URL}/profile-setup`,
    availableLanguage: ["Swedish", "English"],
  },
};

// WebSite structured data with SearchAction for search engine optimization
const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "StipendieAssistenten",
  url: SITE_URL,
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: `${SITE_URL}/grants?q={search_term_string}`,
    },
    "query-input": "required name=search_term_string",
  },
};

export default function SEOHead() {
  const { pathname } = useLocation();

  // Suppress Organization + WebSite schemas on grant detail pages to prevent
  // duplicate-schema validation warnings when ScholarshipProgram is also emitted
  if (pathname.match(/^\/grants\/[^/]+$/)) {
    return null;
  }

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
