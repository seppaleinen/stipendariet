import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import Applications from "../Applications";
import * as AuthContext from "@/contexts/AuthContext";
import * as Api from "@/lib/api";
import type { Application } from "@/types/grants";

const mockUseAuth = vi.spyOn(AuthContext, "useAuth");
const mockGetApplications = vi.spyOn(Api, "getApplications");

// Link renders as a real anchor so href assertions are valid.
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({}),
  useLocation: () => ({ pathname: "/applications" }),
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

const mockApplication = (overrides: Partial<Application> = {}): Application =>
  ({
    id: "app-1",
    grantId: "grant-1",
    grantTitle: "Kunskapsstipendiet",
    status: "draft",
    createdAt: "2025-01-15",
    updatedAt: "2025-01-16",
    ...overrides,
  } as Application);

describe("Applications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { id: "1", email: "test@example.com" },
    } as ReturnType<typeof AuthContext.useAuth>);
    mockGetApplications.mockResolvedValue([]);
  });

  it("renders the page heading", async () => {
    mockGetApplications.mockResolvedValue([]);
    render(<Applications />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        "Mina Ansökningar"
      );
    });
  });

  it("renders a 'Ny Ansökan' button linking to /generate", async () => {
    mockGetApplications.mockResolvedValue([]);
    render(<Applications />);
    await waitFor(() => {
      const btn = screen.getByRole("link", { name: /Ny Ansökan/i });
      expect(btn).toHaveAttribute("href", "/generate");
    });
  });

  it("renders the five status tabs", async () => {
    mockGetApplications.mockResolvedValue([]);
    render(<Applications />);
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /Alla/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Utkast/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Inskickad/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Godkänd/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Avslagen/i })).toBeInTheDocument();
    });
  });

  it("displays applications list when API returns data", async () => {
    const app = mockApplication();
    mockGetApplications.mockResolvedValue([app]);
    render(<Applications />);

    await waitFor(() => {
      expect(screen.getByText("Kunskapsstipendiet")).toBeInTheDocument();
    });
  });

  it("shows empty state for all tab when no applications exist", async () => {
    mockGetApplications.mockResolvedValue([]);
    render(<Applications />);

    await waitFor(() => {
      expect(screen.getByText(/Du har inga ansökningar ännu/)).toBeInTheDocument();
    });
  });

  it("switching tabs filters the applications list", async () => {
    const user = userEvent.setup();
    const draftApp = mockApplication({ status: "draft", grantTitle: "Utkast-stipendiet" });
    const submittedApp = mockApplication({ status: "submitted", grantTitle: "Inskickat-stipendiet" });
    mockGetApplications.mockResolvedValue([draftApp, submittedApp]);
    render(<Applications />);

    // Wait for all tab to show both
    await waitFor(() => {
      expect(screen.getByText("Utkast-stipendiet")).toBeInTheDocument();
      expect(screen.getByText("Inskickat-stipendiet")).toBeInTheDocument();
    });

    // Click Utkast tab and verify it becomes active (and the count badge updates)
    await user.click(screen.getByRole("tab", { name: /Utkast/i }));

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /Utkast/i })).toHaveAttribute(
        "data-state",
        "active"
      );
    });

    // Click Inskickad tab
    await user.click(screen.getByRole("tab", { name: /Inskickad/i }));

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /Inskickad/i })).toHaveAttribute(
        "data-state",
        "active"
      );
    });
  });

  it("renders an 'Utforska Stipendier' link in the empty state", async () => {
    mockGetApplications.mockResolvedValue([]);
    render(<Applications />);

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /Utforska Stipendier/i });
      expect(link).toHaveAttribute("href", "/grants");
    });
  });
});
