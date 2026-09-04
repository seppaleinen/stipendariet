import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import Layout from "./Layout";

// Controllable useAuth mock
const mockUseAuth = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

// Stub out ProfileSwitcher — it has its own dedicated test file
vi.mock("@/components/ProfileSwitcher", () => ({
  ProfileSwitcher: () => <div data-testid="profile-switcher" />,
}));

// Router mock with a real anchor Link so aria-current / href are assertable.
// Overrides the global setup mock which renders Link children without an <a>.
let mockPathname = "/";
vi.mock("react-router-dom", () => ({
  useLocation: () => ({ pathname: mockPathname }),
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

const authState = (overrides: Record<string, unknown> = {}) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  logout: vi.fn().mockResolvedValue(undefined),
  ...overrides,
});

const desktopNav = () =>
  screen.getByRole("navigation", { name: "Huvudnavigering" });
const mobileNav = () =>
  screen.getByRole("navigation", { name: "Mobilnavigering" });

describe("Layout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname = "/";
  });

  it("renders brand and skip link", () => {
    mockUseAuth.mockReturnValue(authState());
    render(
      <Layout>
        <div>Page content</div>
      </Layout>
    );

    expect(screen.getByText("StipendieAssistenten")).toBeInTheDocument();
    expect(
      screen.getByText("Hoppa till huvudinnehåll")
    ).toBeInTheDocument();
    expect(screen.getByText("Page content")).toBeInTheDocument();
  });

  describe("unauthenticated", () => {
    it("shows only public navigation items", () => {
      mockUseAuth.mockReturnValue(authState());
      render(<Layout>content</Layout>);

      const nav = within(desktopNav());
      expect(nav.getByText("Hem")).toBeInTheDocument();
      expect(nav.getByText("Stipendier")).toBeInTheDocument();
      expect(nav.queryByText("Familj")).not.toBeInTheDocument();
      expect(nav.queryByText("Ansökningar")).not.toBeInTheDocument();
      expect(nav.queryByText("Skapa Ansökan")).not.toBeInTheDocument();
    });

    it("shows login button and mobile login link", () => {
      mockUseAuth.mockReturnValue(authState());
      render(<Layout>content</Layout>);

      // Desktop header login link + mobile bottom nav login link
      const loginLinks = screen.getAllByRole("link", { name: /Logga in/ });
      expect(loginLinks.length).toBeGreaterThanOrEqual(2);
      for (const link of loginLinks) {
        expect(link).toHaveAttribute("href", "/auth");
      }
    });

    it("does not show profile switcher or avatar menu", () => {
      mockUseAuth.mockReturnValue(authState());
      render(<Layout>content</Layout>);

      expect(
        screen.queryByTestId("profile-switcher")
      ).not.toBeInTheDocument();
    });

    it("mobile nav uses a 3-column grid when logged out", () => {
      mockUseAuth.mockReturnValue(authState());
      render(<Layout>content</Layout>);

      const grid = mobileNav().querySelector("div");
      expect(grid?.className).toContain("grid-cols-3");
    });
  });

  describe("authenticated", () => {
    const authedUser = { name: "Test User", email: "test@example.com" };

    it("shows public and protected navigation items", () => {
      mockUseAuth.mockReturnValue(
        authState({ user: authedUser, isAuthenticated: true })
      );
      render(<Layout>content</Layout>);

      const nav = within(desktopNav());
      expect(nav.getByText("Hem")).toBeInTheDocument();
      expect(nav.getByText("Stipendier")).toBeInTheDocument();
      expect(nav.getByText("Familj")).toBeInTheDocument();
      expect(nav.getByText("Ansökningar")).toBeInTheDocument();
      // "Skapa Ansökan" is no longer in the desktop top nav — it lives in
      // the mobile "+" overflow sheet (it was removed to keep desktop nav
      // consistent with the mobile-first design and avoid a 5-item top bar).
      expect(nav.queryByText("Skapa Ansökan")).not.toBeInTheDocument();
    });

    it("mobile nav exposes 'Skapa Ansökan' through a '+' overflow sheet", () => {
      mockUseAuth.mockReturnValue(
        authState({ user: authedUser, isAuthenticated: true })
      );
      render(<Layout>content</Layout>);

      // The "+" overflow button is inside the mobile nav.
      const overflowButton = within(mobileNav()).getByRole("button", {
        name: /Fler alternativ/,
      });
      fireEvent.click(overflowButton);

      const createLink = screen.getByRole("link", { name: /Skapa Ansökan/ });
      expect(createLink).toHaveAttribute("href", "/generate");
    });

    it("renders ProfileSwitcher and avatar with user initials", () => {
      mockUseAuth.mockReturnValue(
        authState({ user: authedUser, isAuthenticated: true })
      );
      render(<Layout>content</Layout>);

      expect(screen.getByTestId("profile-switcher")).toBeInTheDocument();
      // getInitials("Test User") -> "TU"
      expect(screen.getByText("TU")).toBeInTheDocument();
    });

    it("falls back to email initial when user has no name", () => {
      mockUseAuth.mockReturnValue(
        authState({
          user: { name: undefined, email: "test@example.com" },
          isAuthenticated: true,
        })
      );
      render(<Layout>content</Layout>);

      expect(screen.getByText("T")).toBeInTheDocument();
    });

    it("marks the active nav item with aria-current", () => {
      mockPathname = "/grants";
      mockUseAuth.mockReturnValue(
        authState({ user: authedUser, isAuthenticated: true })
      );
      render(<Layout>content</Layout>);

      const activeLink = within(desktopNav()).getByRole("link", {
        name: /Stipendier/,
      });
      expect(activeLink).toHaveAttribute("aria-current", "page");

      const inactiveLink = within(desktopNav()).getByRole("link", {
        name: /Hem/,
      });
      expect(inactiveLink).not.toHaveAttribute("aria-current");
    });

    it("mobile nav uses a 5-column grid when logged in", () => {
      mockUseAuth.mockReturnValue(
        authState({ user: authedUser, isAuthenticated: true })
      );
      render(<Layout>content</Layout>);

      const grid = mobileNav().querySelector("div");
      expect(grid?.className).toContain("grid-cols-5");
    });

    it("logs out from the avatar dropdown menu", async () => {
      const logout = vi.fn().mockResolvedValue(undefined);
      mockUseAuth.mockReturnValue(
        authState({ user: authedUser, isAuthenticated: true, logout })
      );
      render(<Layout>content</Layout>);

      // Open the avatar dropdown via the avatar trigger button.
      // Use name=/TU/ to disambiguate from the mobile "+" overflow button.
      const avatarTrigger = screen.getByRole("button", { name: /TU/ });
      fireEvent.pointerDown(avatarTrigger, {
        button: 0,
        ctrlKey: false,
      });

      const logoutItem = await screen.findByText("Logga ut");
      fireEvent.click(logoutItem);

      await waitFor(() => {
        expect(logout).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe("loading state", () => {
    it("shows loading indicator instead of auth controls", () => {
      mockUseAuth.mockReturnValue(
        authState({ isLoading: true })
      );
      render(<Layout>content</Layout>);

      expect(
        screen.getByText("Laddar användarinformation...")
      ).toBeInTheDocument();
      // No login control in the header while loading
      // (the mobile bottom nav legitimately keeps its login link when logged out)
      expect(
        within(screen.getByRole("banner")).queryByText("Logga in")
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("profile-switcher")
      ).not.toBeInTheDocument();
    });
  });
});
