import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import ProtectedRoute from "./ProtectedRoute";

// Controllable useAuth mock
const mockUseAuth = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

// Router mock with a spyable Navigate and controllable pathname.
// Overrides the global setup mock so we can assert redirect targets.
let mockPathname = "/";
const navigateCalls: Array<{ to: string; replace?: boolean }> = [];
vi.mock("react-router-dom", () => ({
  useLocation: () => ({ pathname: mockPathname }),
  Navigate: ({ to, replace }: { to: string; replace?: boolean }) => {
    navigateCalls.push({ to, replace });
    return (
      <div
        data-testid="navigate-redirect"
        data-to={to}
        data-replace={String(replace)}
      />
    );
  },
}));

function renderProtected(children: React.ReactNode = <div>Secret content</div>) {
  return render(<ProtectedRoute>{children}</ProtectedRoute>);
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname = "/";
    navigateCalls.length = 0;
  });

  it("shows a loading spinner while auth state is loading", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    renderProtected();

    // Loader2 icon renders an svg with the animate-spin class
    const spinner = document.querySelector(".animate-spin");
    expect(spinner).toBeInTheDocument();
    expect(screen.queryByText("Secret content")).not.toBeInTheDocument();
    expect(navigateCalls).toHaveLength(0);
  });

  it("redirects unauthenticated users to /auth with return URL", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    renderProtected();

    expect(navigateCalls).toHaveLength(1);
    expect(navigateCalls[0].to).toBe("/auth?redirect=%2F");
    expect(navigateCalls[0].replace).toBe(true);
    expect(screen.queryByText("Secret content")).not.toBeInTheDocument();
  });

  it("encodes special characters in the current path", () => {
    mockPathname = "/grants?q=stipendium&sort=asc";
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    renderProtected();

    expect(navigateCalls[0].to).toBe(
      `/auth?redirect=${encodeURIComponent("/grants?q=stipendium&sort=asc")}`
    );
  });

  it("renders children when authenticated", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    renderProtected();

    expect(screen.getByText("Secret content")).toBeInTheDocument();
    expect(navigateCalls).toHaveLength(0);
  });

  it("loading state takes precedence over redirect", () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    renderProtected();

    // While loading, no redirect decision is made even if unauthenticated
    expect(navigateCalls).toHaveLength(0);
    expect(screen.queryByText("Secret content")).not.toBeInTheDocument();
  });
});
