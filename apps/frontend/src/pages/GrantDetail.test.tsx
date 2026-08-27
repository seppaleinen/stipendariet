import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import GrantDetail from "./GrantDetail";
import { getGrant } from "@/lib/api";

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
});