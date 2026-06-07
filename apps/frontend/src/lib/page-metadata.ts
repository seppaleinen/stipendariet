// SEO metadata configuration for all pages
// Used with react-helmet-async for dynamic <title>, <meta>, and <link> tags

export type PageMetadata = {
  title: string;
  description: string;
  ogImage?: string;
  canonicalUrl?: string;
  noindex?: boolean;
};

export const SITE_URL = "https://stipendieassistenten.labb.site";
export const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`;

export const PAGE_METADATA: Record<string, PageMetadata> = {
  "/": {
    title: "StipendieAssistenten - Hitta och ansök om stipendier",
    description:
      "Din guide till att hitta och ansöka om stipendier och bidrag för din familj. Sök bland hundratals stipendier med kraftfulla filter.",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/grants": {
    title: "Stipendier och Bidrag - Sök bland hundratals stipendier | StipendieAssistenten",
    description:
      "Utforska och sök bland hundratals stipendier och bidrag. Filter och sortering för att hitta rätt stipendium för din familj.",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/matching": {
    title: "Matcha dina behov med rätt stipendier | StipendieAssistenten",
    description:
      "Låt vår AI hjälpa dig hitta stipendier som matchar dina och din familjs behov. Personliga förslag baserat på din profil.",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/auth": {
    title: "Logga in - StipendieAssistenten",
    description: "Logga in för att spara stipendier och ansöka om bidrag.",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/applications": {
    title: "Mina Ansökningar - StipendieAssistenten",
    description: "Håll koll på alla dina stipendieansökningar och få påminnelser.",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/generate": {
    title: "AI-assisterad Stipendieansökan | StipendieAssistenten",
    description:
      "Låt vår AI hjälpa dig skriva personliga och övertygande stipendieansökningar.",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/profile-setup": {
    title: "Skapa Profil - StipendieAssistenten",
    description: "Skapa din personliga profil för personliga stipendieförslag.",
    ogImage: DEFAULT_OG_IMAGE,
  },
  "/family-setup": {
    title: "Familjeprofil - StipendieAssistenten",
    description: "Skapa och hantera din familjeprofil för stipendieförslag.",
    ogImage: DEFAULT_OG_IMAGE,
  },
};

// Dynamic metadata for grant detail pages (filled at runtime)
export const getGrantMetadata = (grant: {
  title: string;
  provider: string;
  category: string;
  amount?: string;
  description?: string;
  purpose?: string;
  translatedPurpose?: string;
}): PageMetadata => {
  const description =
    grant.translatedPurpose || grant.purpose || grant.description || "";
  const truncated =
    description.length > 155 ? description.slice(0, 152) + "..." : description;

  return {
    title: `${grant.title} - ${grant.provider} | StipendieAssistenten`,
    description: truncated,
    ogImage: DEFAULT_OG_IMAGE,
    canonicalUrl: `${SITE_URL}/grants`,
  };
};
