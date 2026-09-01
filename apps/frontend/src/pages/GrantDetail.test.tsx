import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import GrantDetail from "./GrantDetail";
import { getGrant, getSavedGrants } from "@/lib/api";

const mockUseAuth = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getGrant: vi.fn(),
  getSavedGrants: vi.fn(),
  saveGrant: vi.fn(),
  removeSavedGrant: vi.fn(),
}));

// Override the global react-router-dom mock (in test-setup.ts) so this page
// receives an id from useParams and Link renders as a real anchor.
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({ id: "foundation-7994" }),
  Link: ({
    to,
    children,
    ...rest
  }: {
    to: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
}));

// Stub SSRDataContext so the component attempts an API call instead of reading SSR state.
vi.mock("@/contexts/SSRDataContext", () => ({
  useSSRData: () => ({ grant: null }),
}));

describe("GrantDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: false });
  });

  it("renders the not-found state for an unknown id instead of crashing", async () => {
    // getGrant returns undefined on a 404 (backend 404 is correct behavior) —
    // the component must degrade to the "Stipendium hittades inte" state.
    vi.mocked(getGrant).mockResolvedValue(undefined);

    render(<GrantDetail />);

    expect(
      await screen.findByText("Stipendium hittades inte")
    ).toBeInTheDocument();
    const backLink = screen.getByRole("link", {
      name: "Tillbaka till stipendier",
    });
    expect(backLink).toHaveAttribute("href", "/grants");

    // No loading spinner and no detail content (no crash = no white screen).
    expect(screen.queryByText("Laddar...")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
  });

  it("renders grant details when the API returns a grant", async () => {
    vi.mocked(getGrant).mockResolvedValue({
      id: "foundation-7994",
      title: "Kunskapsstipendiet",
      provider: "Utbildningsfonden",
      category: "Utbildning",
      summary: "Ett stipendium för studerande.",
      description: "Stödjer universitetsstuderande.",
      purpose: "Stöd för studerande.",
      tags: ["utbildning"],
      isRecurring: false,
    } as any);
    vi.mocked(getSavedGrants).mockResolvedValue([]);

    render(<GrantDetail />);

    await screen.findByRole("heading", { level: 1 });
    expect(
      screen.getByRole("heading", { level: 1 })
    ).toHaveTextContent("Kunskapsstipendiet");
    expect(screen.getByText("Utbildningsfonden")).toBeInTheDocument();
  });

  it("renders a 'Starta Ansökan' link visible on the detail page", async () => {
    vi.mocked(getGrant).mockResolvedValue({
      id: "foundation-7994",
      title: "Kunskapsstipendiet",
      provider: "Utbildningsfonden",
      category: "Utbildning",
      summary: "Ett stipendium för studerande.",
      description: "",
      purpose: "",
      tags: [],
      isRecurring: false,
    } as any);
    vi.mocked(getSavedGrants).mockResolvedValue([]);

    render(<GrantDetail />);

    await screen.findByRole("heading", { level: 1 });

    const startLink = screen.getByRole("link", { name: /Starta Ansökan/i });
    expect(startLink).toHaveAttribute("href", "/generate/foundation-7994");
  });

  it("renders the FAQSection with 'Vanliga frågor' heading", async () => {
    vi.mocked(getGrant).mockResolvedValue({
      id: "foundation-7994",
      title: "Kunskapsstipendiet",
      provider: "Utbildningsfonden",
      category: "Utbildning",
      summary: "Ett stipendium för studerande.",
      description: "Stödjer universitetsstuderande.",
      purpose: "Stöd för studerande.",
      tags: ["utbildning"],
      isRecurring: false,
    } as any);
    vi.mocked(getSavedGrants).mockResolvedValue([]);

    render(<GrantDetail />);

    await screen.findByRole("heading", { level: 1 });

    expect(
      screen.getByRole("heading", { level: 2, name: /Vanliga frågor/i })
    ).toBeInTheDocument();
  });

  it("emits BreadcrumbList JSON-LD with 3 items", async () => {
    vi.mocked(getGrant).mockResolvedValue({
      id: "foundation-7994",
      title: "Kunskapsstipendiet",
      provider: "Utbildningsfonden",
      category: "Utbildning",
      summary: "Ett stipendium för studerande.",
      description: "Stödjer universitetsstuderande.",
      purpose: "Stöd för studerande.",
      tags: ["utbildning"],
      isRecurring: false,
    } as any);
    vi.mocked(getSavedGrants).mockResolvedValue([]);

    render(<GrantDetail />);

    await screen.findByRole("heading", { level: 1 });

    const scripts = Array.from(
      document.querySelectorAll('script[type="application/ld+json"]')
    ) as HTMLScriptElement[];
    const breadcrumb = scripts
      .map((s) => JSON.parse(s.textContent ?? ""))
      .find((parsed) => parsed["@type"] === "BreadcrumbList");

    expect(breadcrumb).toBeDefined();
    expect(breadcrumb.itemListElement).toHaveLength(3);
    expect(breadcrumb.itemListElement[0].name).toBe("Hem");
    expect(breadcrumb.itemListElement[1].name).toBe("Hitta stipendier");
    expect(breadcrumb.itemListElement[2].name).toBe("Kunskapsstipendiet");
  });

  it("emits ScholarshipProgram JSON-LD with entity fields for LLM citation probability", async () => {
    vi.mocked(getGrant).mockResolvedValue({
      id: "foundation-7994",
      title: "Kunskapsstipendiet",
      provider: "Utbildningsfonden",
      category: "Utbildning",
      summary: "Ett stipendium för studerande.",
      description: "Stödjer universitetsstuderande.",
      purpose: "Stöd för studerande i Uppsala.",
      tags: ["utbildning", "studenter", "uppsala"],
      deadline: "2026-06-01",
      applicationStart: "2026-01-01",
      applicationDeadline: "2026-05-15",
      isRecurring: false,
    } as any);
    vi.mocked(getSavedGrants).mockResolvedValue([]);

    render(<GrantDetail />);

    await screen.findByRole("heading", { level: 1 });

    const scripts = Array.from(
      document.querySelectorAll('script[type="application/ld+json"]')
    ) as HTMLScriptElement[];
    const scholarship = scripts
      .map((s) => JSON.parse(s.textContent ?? ""))
      .find((parsed) => parsed["@type"] === "ScholarshipProgram");

    expect(scholarship).toBeDefined();
    expect(scholarship.name).toBe("Kunskapsstipendiet");
    expect(scholarship.about).toBe("Stöd för studerande i Uppsala.");
    expect(scholarship.keywords).toBe("utbildning, studenter, uppsala");
    expect(scholarship.inLanguage).toBe("sv-SE");
    expect(scholarship.applicationStartDate).toBe("2026-01-01");
    expect(scholarship.applicationDeadline).toBe("2026-05-15");
    expect(scholarship.expirationDate).toBe("2026-06-01");
  });

  // GEO Flaw #1 — ScholarshipProgram description should prefer enrichedDescription
  // over translatedPurpose/purpose/description (issue #2)
  it("uses enrichedDescription in ScholarshipProgram JSON-LD when present", async () => {
    const enriched =
      "Detta stipendium stödjer universitetsstuderande i Uppsala som är i behov av "
      + "ekonomiskt stöd. Bidraget kan användas för kurslitteratur, resor och "
      + "levnadskostnader under studieperioden. Sökande bör bifoga studieintyg, "
      + "motivering samt en tydlig beskrivning av hur bidraget ska användas.";
    vi.mocked(getGrant).mockResolvedValue({
      id: "foundation-7994",
      title: "Kunskapsstipendiet",
      provider: "Utbildningsfonden",
      category: "Utbildning",
      summary: "Ett stipendium för studerande.",
      description: "Fallback-beskrivning som INTE ska användas.",
      purpose: "Stöd för studerande.",
      translatedPurpose: "Modern svenska — INTE heller denna.",
      enrichedDescription: enriched,
      tags: ["utbildning"],
      isRecurring: false,
    } as any);
    vi.mocked(getSavedGrants).mockResolvedValue([]);

    render(<GrantDetail />);

    await screen.findByRole("heading", { level: 1 });

    const scripts = Array.from(
      document.querySelectorAll('script[type="application/ld+json"]')
    ) as HTMLScriptElement[];
    const scholarship = scripts
      .map((s) => JSON.parse(s.textContent ?? ""))
      .find((parsed) => parsed["@type"] === "ScholarshipProgram");

    expect(scholarship).toBeDefined();
    expect(scholarship.description).toBe(enriched);
    expect(scholarship.description).not.toContain("Fallback-beskrivning");
    expect(scholarship.description).not.toContain("Modern svenska");

    // The <meta name="description"> tag should likewise prefer enrichedDescription
    const metaDescription = document
      .querySelector('meta[name="description"]')
      ?.getAttribute("content");
    expect(metaDescription).toBe(enriched);

    // The og:description should likewise prefer enrichedDescription
    const ogDescription = document
      .querySelector('meta[property="og:description"]')
      ?.getAttribute("content");
    expect(ogDescription).toBe(enriched);
  });

  it("emits applying topic FAQPage JSON-LD with 3 Q&A pairs", async () => {
    vi.mocked(getGrant).mockResolvedValue({
      id: "foundation-7994",
      title: "Kunskapsstipendiet",
      provider: "Utbildningsfonden",
      category: "Utbildning",
      summary: "Ett stipendium för studerande.",
      description: "Stödjer universitetsstuderande.",
      purpose: "Stöd för studerande.",
      tags: ["utbildning"],
      isRecurring: false,
    } as any);
    vi.mocked(getSavedGrants).mockResolvedValue([]);

    render(<GrantDetail />);

    await screen.findByRole("heading", { level: 1 });

    const scripts = Array.from(
      document.querySelectorAll('script[type="application/ld+json"]')
    ) as HTMLScriptElement[];
    const faqSchema = scripts
      .map((s) => JSON.parse(s.textContent ?? ""))
      .find((parsed) => parsed["@type"] === "FAQPage");

    expect(faqSchema).toBeDefined();
    expect(faqSchema.mainEntity).toHaveLength(3);
    expect(faqSchema.mainEntity[0].name).toBe(
      "Hur ansöker jag om detta stipendium?"
    );
  });
});