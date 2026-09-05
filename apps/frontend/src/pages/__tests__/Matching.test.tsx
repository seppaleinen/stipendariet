import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import Matching from "../Matching";
import * as AuthContext from "@/contexts/AuthContext";

const mockUseAuth = vi.spyOn(AuthContext, "useAuth");

// Link renders as a real anchor so href assertions are valid.
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({}),
  useLocation: () => ({ pathname: "/matching" }),
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
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

const grant = (overrides: Partial<Record<string, unknown>> = {}) => ({
  id: "gr-1",
  title: "Kunskapsfonden",
  summary: "Ett stipendium för studerande.",
  provider: "Stiftelsen Kunskap",
  amount: "10 000 kr",
  deadline: "2026-10-01",
  category: "Utbildning",
  ...overrides,
});

const mockFetch = vi.fn();

const stubMatchingResponse = (grants: unknown[], categories: string[] = []) => {
  mockFetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ grants, categories }),
  });
};

describe("Matching", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("fetch", mockFetch);
    stubMatchingResponse([]);
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
    });
  });

  describe("rendering", () => {
    it("renders the page heading", async () => {
      render(<Matching />);
      expect(
        screen.getByRole("heading", { name: "Matcha stipendier" })
      ).toBeInTheDocument();
    });

    it("fetches matching results on mount", async () => {
      render(<Matching />);
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("/foundations/matching"),
          expect.objectContaining({ method: "POST" })
        );
      });
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body).toMatchObject({ limit: 50 });
      // "all" county means no county filter is sent
      expect(body.county).toBeUndefined();
    });

    it("shows the empty state when no grants match", async () => {
      render(<Matching />);
      await waitFor(() => {
        expect(
          screen.getByText(/Inga stipendier hittades/)
        ).toBeInTheDocument();
      });
    });
  });

  describe("filters", () => {
    it("renders search input with category and county selects", () => {
      render(<Matching />);
      expect(
        screen.getByPlaceholderText("Sök stipendier...")
      ).toBeInTheDocument();
      // Selected values render in the Radix triggers without opening the lists.
      expect(screen.getByText("Alla Kategorier")).toBeInTheDocument();
      expect(screen.getByText("Alla län")).toBeInTheDocument();
    });
  });

  describe("results", () => {
    beforeEach(() => {
      stubMatchingResponse(
        [
          grant(),
          grant({
            id: "gr-2",
            title: "Hälsofonden",
            provider: "Hälsofonden AB",
            amount: undefined,
            deadline: undefined,
            category: "Hälsa",
          }),
        ],
        ["Utbildning", "Hälsa"]
      );
    });

    it("renders result cards with title, provider, amount, deadline and count", async () => {
      render(<Matching />);
      expect(await screen.findByText("Kunskapsfonden")).toBeInTheDocument();
      expect(screen.getByText("Hälsofonden")).toBeInTheDocument();
      expect(screen.getByText("2 stipendier hittades")).toBeInTheDocument();
      expect(screen.getAllByText("Utgivare:")).toHaveLength(2);
      expect(screen.getByText("Stiftelsen Kunskap")).toBeInTheDocument();
      expect(screen.getByText("Belopp:")).toBeInTheDocument();
      expect(screen.getByText("10 000 kr")).toBeInTheDocument();
      expect(screen.getByText("Deadline:")).toBeInTheDocument();
      expect(screen.getByText("2026-10-01")).toBeInTheDocument();
      expect(screen.getByText("Utbildning")).toBeInTheDocument();
    });

    it("renders a Läs mer link to the grant detail page", async () => {
      render(<Matching />);
      await screen.findByText("Kunskapsfonden");
      const links = screen.getAllByRole("link", { name: "Läs mer" });
      expect(links[0]).toHaveAttribute("href", "/grants/gr-1");
      expect(links[1]).toHaveAttribute("href", "/grants/gr-2");
    });
  });

  describe("auth gating", () => {
    beforeEach(() => {
      stubMatchingResponse([grant()]);
    });

    it("opens the login prompt when saving while logged out", async () => {
      render(<Matching />);
      await screen.findByText("Kunskapsfonden");

      fireEvent.click(screen.getByRole("button", { name: "Spara Kunskapsfonden" }));
      expect(
        screen.getByText("Logga in för att spara")
      ).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Avbryt" }));
      await waitFor(() => {
        expect(
          screen.queryByText("Logga in för att spara")
        ).not.toBeInTheDocument();
      });
    });

    it("disables the generate button for logged-out users", async () => {
      render(<Matching />);
      await screen.findByText("Kunskapsfonden");
      const generate = screen.getByRole("button", {
        name: /Generera ansökan/,
      });
      expect(generate).toBeDisabled();
      expect(generate).toHaveAttribute(
        "title",
        "Logga in för att generera ansökan"
      );
    });

    it("enables the generate button for authenticated users", async () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: { id: "1", email: "test@example.com" },
      });
      render(<Matching />);
      await screen.findByText("Kunskapsfonden");
      const generate = screen.getByRole("button", {
        name: /Generera ansökan/,
      });
      expect(generate).toBeEnabled();
    });
  });
});