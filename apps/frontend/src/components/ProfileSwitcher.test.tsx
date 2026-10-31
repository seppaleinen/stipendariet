import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { ProfileSwitcher } from "./ProfileSwitcher";
import type { Profile } from "@stipendariet/types";

// Controllable useProfile mock
const mockUseProfile = vi.fn();
vi.mock("@/contexts/ProfileContext", () => ({
  useProfile: () => mockUseProfile(),
}));

// Navigate spy we can assert on (global setup mock returns a fresh fn each call)
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

const profileA: Profile = { id: 1, name: "Pappa" };
const profileB: Profile = { id: 2, name: "Mamma" };
const newProfile: Profile = { id: 3, name: "Klient A" };

const profileState = (overrides: Record<string, unknown> = {}) => ({
  profiles: [profileA, profileB],
  activeProfile: null as Profile | null,
  isLoading: false,
  setActiveProfile: vi.fn(),
  refreshProfiles: vi.fn().mockResolvedValue(undefined),
  createProfile: vi.fn().mockResolvedValue(newProfile),
  updateProfile: vi.fn(),
  ...overrides,
});

async function openPopover() {
  fireEvent.click(screen.getByRole("combobox"));
  await screen.findByText("Dina profiler");
}

describe("ProfileSwitcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("trigger button", () => {
    it('shows placeholder text when no active profile', () => {
      mockUseProfile.mockReturnValue(profileState());
      render(<ProfileSwitcher />);

      expect(screen.getByRole("combobox")).toHaveTextContent(
        "Välj profil..."
      );
    });

    it("shows active profile name when set", () => {
      mockUseProfile.mockReturnValue(
        profileState({ activeProfile: profileA })
      );
      render(<ProfileSwitcher />);

      expect(screen.getByRole("combobox")).toHaveTextContent("Pappa");
    });
  });

  describe("profile list", () => {
    it("lists all profiles when opened", async () => {
      mockUseProfile.mockReturnValue(profileState());
      render(<ProfileSwitcher />);

      await openPopover();

      expect(screen.getByText("Pappa")).toBeInTheDocument();
      expect(screen.getByText("Mamma")).toBeInTheDocument();
    });

    it("calls setActiveProfile and closes popover on selection", async () => {
      const setActiveProfile = vi.fn();
      mockUseProfile.mockReturnValue(profileState({ setActiveProfile }));
      render(<ProfileSwitcher />);

      await openPopover();
      fireEvent.click(screen.getByText("Mamma"));

      expect(setActiveProfile).toHaveBeenCalledTimes(1);
      expect(setActiveProfile).toHaveBeenCalledWith(profileB);
      // Popover closes -> list no longer rendered
      await waitFor(() => {
        expect(screen.queryByText("Dina profiler")).not.toBeInTheDocument();
      });
    });
  });

  describe("create profile dialog", () => {
    it("opens dialog from the Ny profil action", async () => {
      mockUseProfile.mockReturnValue(profileState());
      render(<ProfileSwitcher />);

      await openPopover();
      fireEvent.click(screen.getByText("Ny profil"));

      expect(
        await screen.findByText("Skapa ny profil")
      ).toBeInTheDocument();
    });

    it("does not call createProfile with an empty name", async () => {
      const createProfile = vi.fn();
      mockUseProfile.mockReturnValue(profileState({ createProfile }));
      render(<ProfileSwitcher />);

      await openPopover();
      fireEvent.click(screen.getByText("Ny profil"));
      await screen.findByText("Skapa ny profil");

      fireEvent.click(screen.getByRole("button", { name: "Skapa profil" }));

      expect(createProfile).not.toHaveBeenCalled();
    });

    it("creates profile, activates it, closes dialog and navigates to setup", async () => {
      const createProfile = vi.fn().mockResolvedValue(newProfile);
      const setActiveProfile = vi.fn();
      mockUseProfile.mockReturnValue(
        profileState({ createProfile, setActiveProfile })
      );
      render(<ProfileSwitcher />);

      await openPopover();
      fireEvent.click(screen.getByText("Ny profil"));
      await screen.findByText("Skapa ny profil");

      const input = screen.getByLabelText("Namn");
      fireEvent.change(input, { target: { value: "Klient A" } });
      fireEvent.click(screen.getByRole("button", { name: "Skapa profil" }));

      await waitFor(() => {
        expect(createProfile).toHaveBeenCalledWith({ name: "Klient A" });
      });
      await waitFor(() => {
        expect(setActiveProfile).toHaveBeenCalledWith(newProfile);
      });
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith("/profile-setup");
      });
      await waitFor(() => {
        expect(
          screen.queryByText("Skapa ny profil")
        ).not.toBeInTheDocument();
      });
    });

    it("creates a profile on Enter key press", async () => {
      const createProfile = vi.fn().mockResolvedValue(newProfile);
      mockUseProfile.mockReturnValue(profileState({ createProfile }));
      render(<ProfileSwitcher />);

      await openPopover();
      fireEvent.click(screen.getByText("Ny profil"));
      await screen.findByText("Skapa ny profil");

      const input = screen.getByLabelText("Namn");
      fireEvent.change(input, { target: { value: "Klient B" } });
      fireEvent.keyDown(input, { key: "Enter" });

      await waitFor(() => {
        expect(createProfile).toHaveBeenCalledWith({ name: "Klient B" });
      });
    });

    it("keeps dialog open and does not navigate when creation fails", async () => {
      const consoleError = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});
      const createProfile = vi.fn().mockRejectedValue(new Error("API down"));
      mockUseProfile.mockReturnValue(profileState({ createProfile }));
      render(<ProfileSwitcher />);

      try {
        await openPopover();
        fireEvent.click(screen.getByText("Ny profil"));
        await screen.findByText("Skapa ny profil");

        const input = screen.getByLabelText("Namn");
        fireEvent.change(input, { target: { value: "Klient C" } });
        fireEvent.click(screen.getByRole("button", { name: "Skapa profil" }));

        await waitFor(() => {
          expect(createProfile).toHaveBeenCalled();
        });
        await waitFor(() => {
          expect(mockNavigate).not.toHaveBeenCalled();
        });
        // Dialog stays open so the user can retry
        expect(screen.getByText("Skapa ny profil")).toBeInTheDocument();
      } finally {
        consoleError.mockRestore();
      }
    });

    it("disables submit button while creation is pending", async () => {
      let resolveCreate: (p: Profile) => void;
      const createProfile = vi.fn(
        () =>
          new Promise<Profile>((resolve) => {
            resolveCreate = resolve;
          })
      );
      mockUseProfile.mockReturnValue(profileState({ createProfile }));
      render(<ProfileSwitcher />);

      await openPopover();
      fireEvent.click(screen.getByText("Ny profil"));
      await screen.findByText("Skapa ny profil");

      const input = screen.getByLabelText("Namn");
      fireEvent.change(input, { target: { value: "Klient D" } });
      fireEvent.click(screen.getByRole("button", { name: "Skapa profil" }));

      expect(screen.getByText("Skapar...")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Skapar..." })
      ).toBeDisabled();

      resolveCreate!(newProfile);
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith("/profile-setup");
      });
    });
  });
});
