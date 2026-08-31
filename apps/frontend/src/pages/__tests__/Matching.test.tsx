import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import Matching from "../Matching";
import * as AuthContext from "@/contexts/AuthContext";
import * as ProfileContext from "@/contexts/ProfileContext";
import * as Api from "@/lib/api";
import type { MatchedFoundation } from "@/lib/api";

const mockUseAuth = vi.spyOn(AuthContext, "useAuth");
const mockUseProfile = vi.spyOn(ProfileContext, "useProfile");
const mockFindMatchingFoundationsByProfile = vi.spyOn(
  Api,
  "findMatchingFoundationsByProfile"
);

// Link renders as a real anchor so href assertions are valid.
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({}),
  useLocation: () => ({ pathname: "/matching" }),
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

const mockProfile = {
  id: 1,
  name: "Test Profile",
  isDefault: true,
  countyCode: "01",
  municipalityCode: "0114",
  lifeSituations: ["Studerande"],
  healthConditions: [],
  occupations: [],
  supportPurposes: [],
  selfDescription: "Jag studerar på universitetet.",
};

const mockMatch = (overrides: Partial<MatchedFoundation> = {}): MatchedFoundation =>
  ({
    foundation: {
      foundation_id: "f-1",
      name: "Kunskapsfonden",
      summary: "Ett stipendium för studerande.",
      category: "Utbildning",
      translated_purpose: "Syftet är att stödja studerande.",
      parsedServiceArea: null,
    },
    similarity_score: 0.75,
    ...overrides,
  } as unknown as MatchedFoundation);

describe("Matching", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFindMatchingFoundationsByProfile.mockResolvedValue([]);
  });

  describe("unauthenticated", () => {
    it("shows an auth prompt", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false } as ReturnType<typeof AuthContext.useAuth>);
      mockUseProfile.mockReturnValue({
        activeProfile: null,
        isLoading: false,
      } as ReturnType<typeof ProfileContext.useProfile>);

      render(<Matching />);

      expect(
        screen.getByText(/Logga in och fyll i din profil/i)
      ).toBeInTheDocument();
      const loginLink = screen.getByRole("link", { name: /Logga in/i });
      expect(loginLink).toHaveAttribute("href", "/auth");
    });
  });

  describe("authenticated without profile", () => {
    it("shows a prompt to create a profile", () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: { id: "1", email: "test@example.com" },
      } as ReturnType<typeof AuthContext.useAuth>);
      mockUseProfile.mockReturnValue({
        activeProfile: null,
        isLoading: false,
      } as ReturnType<typeof ProfileContext.useProfile>);

      render(<Matching />);

      expect(
        screen.getByText(/Fyll i profilen för att börja/i)
      ).toBeInTheDocument();
      const profileLink = screen.getByRole("link", { name: /Gå till profilsidan/i });
      expect(profileLink).toHaveAttribute("href", "/profile-setup");
    });
  });

  describe("authenticated with profile (full matching view)", () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: { id: "1", email: "test@example.com" },
      } as ReturnType<typeof AuthContext.useAuth>);
      mockUseProfile.mockReturnValue({
        activeProfile: mockProfile as ProfileContext.Profile,
        isLoading: false,
        updateProfile: vi.fn().mockResolvedValue(undefined),
      } as unknown as ReturnType<typeof ProfileContext.useProfile>);
    });

    it("renders the matching page heading", async () => {
      render(<Matching />);
      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
          "Matchande stiftelser"
        );
      });
    });

    it("renders matching results when the API returns data", async () => {
      mockFindMatchingFoundationsByProfile.mockResolvedValue([
        mockMatch(),
        mockMatch({
          foundation: {
            ...mockMatch().foundation,
            foundation_id: "f-2",
            name: "Hälsofonden",
          },
          similarity_score: 0.55,
        }),
      ]);

      render(<Matching />);

      await waitFor(() => {
        expect(screen.getByText("Kunskapsfonden")).toBeInTheDocument();
        expect(screen.getByText("Hälsofonden")).toBeInTheDocument();
      });
    });

    it("renders similarity badges on result cards", async () => {
      mockFindMatchingFoundationsByProfile.mockResolvedValue([
        mockMatch({ similarity_score: 0.82 }),
      ]);

      render(<Matching />);

      await waitFor(() => {
        expect(screen.getByText("82% match")).toBeInTheDocument();
      });
    });

    it("renders result cards with a link to the grant detail page", async () => {
      mockFindMatchingFoundationsByProfile.mockResolvedValue([mockMatch()]);

      render(<Matching />);

      await waitFor(() => {
        const detailLink = screen.getByRole("link", { name: /Läs mer/i });
        expect(detailLink).toHaveAttribute("href", "/grants/foundation-f-1");
      });
    });

    it("geo filter toggle is present and functional", async () => {
      render(<Matching />);

      await waitFor(() => {
        const toggle = screen.getByRole("switch", { name: /Filtrera på geografiskt område/i });
        expect(toggle).toBeInTheDocument();
        expect(toggle).toHaveAttribute("aria-checked", "true"); // default: useGeoFilter = true
      });

      // Toggle it off
      fireEvent.click(screen.getByLabelText(/Filtrera på geografiskt område/i));

      await waitFor(() => {
        const toggle = screen.getByRole("switch", { name: /Filtrera på geografiskt område/i });
        expect(toggle).toHaveAttribute("aria-checked", "false");
      });
    });

    it("renders an 'Alla stipendier' back link", async () => {
      render(<Matching />);

      await waitFor(() => {
        const link = screen.getByRole("link", { name: /Alla stipendier/i });
        expect(link).toHaveAttribute("href", "/grants");
      });
    });
  });
});
