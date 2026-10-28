import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import { ProfileSetupForm } from "../components/ProfileSetupForm";
import * as ProfileContext from "@/contexts/ProfileContext";
import type { Profile } from "@/lib/api";

vi.mock("react-helmet-async", () => ({
  HelmetProvider: ({ children }: { children: React.ReactNode }) => children,
  Helmet: ({ children }: { children: React.ReactNode }) => children,
}));

const mockUseProfile = vi.fn();
vi.spyOn(ProfileContext, "useProfile").mockImplementation(mockUseProfile);

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const activeProfile: Profile = {
  id: 1,
  name: "Test Profile",
  isDefault: true,
};

const profileState = (overrides: Record<string, unknown> = {}) => ({
  activeProfile,
  profiles: [activeProfile],
  isLoading: false,
  setActiveProfile: vi.fn(),
  refreshProfiles: vi.fn().mockResolvedValue(undefined),
  createProfile: vi.fn().mockResolvedValue({ id: 2, name: "New" }),
  updateProfile: vi.fn().mockResolvedValue({ ...activeProfile }),
  ...overrides,
});

describe("ProfileSetupForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the form title and all five tabs", () => {
    mockUseProfile.mockReturnValue(profileState());
    render(<ProfileSetupForm />);

    expect(
      screen.getByRole("heading", { name: /Profil: Test Profile/i })
    ).toBeInTheDocument();

    expect(screen.getByRole("tab", { name: /Geografi/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Livssituation/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Hälsa/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Yrke/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Ändamål/i })).toBeInTheDocument();
  });

  it("switches active tab when a tab trigger is clicked", async () => {
    const user = userEvent.setup();
    mockUseProfile.mockReturnValue(profileState());
    render(<ProfileSetupForm />);

    const geographyTab = screen.getByRole("tab", { name: /Geografi/i });
    expect(geographyTab).toHaveAttribute("data-state", "active");

    const healthTab = screen.getByRole("tab", { name: /Hälsa/i });
    await user.click(healthTab);

    await waitFor(() => {
      expect(healthTab).toHaveAttribute("data-state", "active");
    });

    expect(geographyTab).not.toHaveAttribute("data-state", "active");
  });

  it("renders loading state while profile is loading and no active profile", () => {
    mockUseProfile.mockReturnValue(
      profileState({ activeProfile: null, isLoading: true })
    );
    const { container } = render(<ProfileSetupForm />);

    const spinner = container.querySelector(".animate-spin");
    expect(spinner).toBeInTheDocument();
  });

  it("renders empty state when no active profile is selected", () => {
    mockUseProfile.mockReturnValue(
      profileState({ activeProfile: null, isLoading: false })
    );
    render(<ProfileSetupForm />);

    expect(
      screen.getByText(/Ingen profil vald/i)
    ).toBeInTheDocument();
  });
});