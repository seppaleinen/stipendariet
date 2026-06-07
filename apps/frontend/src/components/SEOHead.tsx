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
  sameAs: [],
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
