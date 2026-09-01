import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import Grants from "../Grants";
import * as AuthContext from "@/contexts/AuthContext";
import * as Api from "@/lib/api";
import type { Grant } from "@/types/grants";

const mockUseAuth = vi.spyOn(AuthContext, "useAuth");

// Mock SSR data so the page does not attempt an API call on mount.
vi.mock("@/contexts/SSRDataContext", () => ({
  useSSRData: () => ({ grants: null }),
}));

const mockGetGrants = vi.spyOn(Api, "getGrants");
const mockGetSavedGrants = vi.spyOn(Api, "getSavedGrants");
const mockSaveGrant = vi.spyOn(Api, "saveGrant");
const mockRemoveSavedGrant = vi.spyOn(Api, "removeSavedGrant");

// Link renders as a real anchor so href assertions are valid.
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({}),
  useLocation: () => ({ pathname: "/grants" }),
  Outlet: () => null,
  Routes: () => null,
  Route: () => null,
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

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const mockGrant = (overrides: Partial<Grant> = {}): Grant =>
  ({
    id: "grant-1",
    title: "Kunskapsstipendiet",
    summary: "Ett stipendium för studerande.",
    provider: "Utbildningsfonden",
    category: "Utbildning",
    tags: ["studier", "ungdomar"],
    amount: "5 000 kr",
    deadline: "2025-06-01",
    ...overrides,
  } as Grant);

const grantsResponse = (grants: Grant[]) => ({
  grants,
  total: grants.length,
  skip: 0,
  limit: 50,
  has_more: false,
});

describe("Grants", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: false } as ReturnType<typeof AuthContext.useAuth>);
    mockGetSavedGrants.mockResolvedValue([]);
  });

  it("renders the page heading", async () => {
    mockGetGrants.mockResolvedValue(grantsResponse([]));
    render(<Grants />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        "Stipendier och Bidrag"
      );
    });
  });

  it("renders a grants list when the API returns data", async () => {
    const grant = mockGrant();
    mockGetGrants.mockResolvedValue(grantsResponse([grant]));
    render(<Grants />);

    await waitFor(() => {
      expect(screen.getByText("Kunskapsstipendiet")).toBeInTheDocument();
    });
    expect(screen.getByText("Utbildningsfonden")).toBeInTheDocument();
    expect(screen.getByText("5 000 kr")).toBeInTheDocument();
  });

  it("renders the search input", async () => {
    mockGetGrants.mockResolvedValue(grantsResponse([]));
    render(<Grants />);
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Sök stipendier...")
      ).toBeInTheDocument();
    });
  });

  it("search input accepts typed text", async () => {
    mockGetGrants.mockResolvedValue(grantsResponse([]));
    render(<Grants />);

    const searchInput = await screen.findByPlaceholderText("Sök stipendier...");
    fireEvent.change(searchInput, { target: { value: "stipendium" } });

    await waitFor(() => {
      expect(searchInput).toHaveValue("stipendium");
    });
  });

  it("category filter select is present", async () => {
    mockGetGrants.mockResolvedValue(grantsResponse([]));
    render(<Grants />);
    await waitFor(() => {
      // The Radix Select trigger renders the current value ("Alla Kategorier" by default)
      expect(screen.getByText("Alla Kategorier")).toBeInTheDocument();
    });
  });

  it("renders grant cards with a link to the detail page", async () => {
    const grant = mockGrant({ id: "grant-42" });
    mockGetGrants.mockResolvedValue(grantsResponse([grant]));
    render(<Grants />);

    await waitFor(() => {
      const detailLink = screen.getByRole("link", { name: /Läs mer/i });
      expect(detailLink).toHaveAttribute("href", "/grants/grant-42");
    });
  });

  it("shows empty state when no grants are returned", async () => {
    mockGetGrants.mockResolvedValue(grantsResponse([]));
    render(<Grants />);

    await waitFor(() => {
      expect(
        screen.getByText(/Inga stipendier hittades/)
      ).toBeInTheDocument();
    });
  });

  it("shows a 'Hitta matchande' button linking to /matching", async () => {
    mockGetGrants.mockResolvedValue(grantsResponse([]));
    render(<Grants />);

    await waitFor(() => {
      const matchLink = screen.getByRole("link", { name: /Hitta matchande/i });
      expect(matchLink).toHaveAttribute("href", "/matching");
    });
  });

  it("renders a visible breadcrumb with links to home and current page", async () => {
    mockGetGrants.mockResolvedValue(grantsResponse([]));
    render(<Grants />);

    const breadcrumb = await waitFor(() => {
      const el = document.querySelector('nav[aria-label="Brödsmula"]');
      expect(el).toBeInTheDocument();
      expect(el).toHaveTextContent("Hem");
      expect(el).toHaveTextContent("Hitta stipendier");
      return el;
    });

    const homeLink = screen.getByRole("link", { name: "Hem" });
    expect(homeLink).toHaveAttribute("href", "/");
    const currentPage = breadcrumb?.querySelector('[aria-current="page"]');
    expect(currentPage).toHaveTextContent("Hitta stipendier");
  });

  it("injects BreadcrumbList JSON-LD in the document head", async () => {
    mockGetGrants.mockResolvedValue(grantsResponse([]));
    render(<Grants />);

    await waitFor(() => {
      const scripts = document.querySelectorAll('script[type="application/ld+json"]');
      const breadcrumbScripts = Array.from(scripts).filter((s) => {
        try {
          const data = JSON.parse(s.textContent || "");
          return data["@type"] === "BreadcrumbList";
        } catch {
          return false;
        }
      });
      expect(breadcrumbScripts).toHaveLength(1);
      const schema = JSON.parse(breadcrumbScripts[0].textContent || "");
      expect(schema.itemListElement).toHaveLength(2);
      expect(schema.itemListElement[0]).toMatchObject({
        "@type": "ListItem",
        position: 1,
        name: "Hem",
      });
      expect(schema.itemListElement[1]).toMatchObject({
        "@type": "ListItem",
        position: 2,
        name: "Hitta stipendier",
      });
    });
  });
});
