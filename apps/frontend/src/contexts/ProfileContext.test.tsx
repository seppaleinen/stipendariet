import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";
import { ProfileProvider, useProfile, Profile } from "./ProfileContext";
import * as AuthContext from "./AuthContext";
import * as Api from "@/lib/api";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
  writable: true,
});

// Mock react-router-dom
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({}),
  useLocation: () => ({ pathname: "/" }),
  Outlet: () => null,
  Routes: () => null,
  Route: () => null,
  Link: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock react-helmet-async
vi.mock("react-helmet-async", () => ({
  HelmetProvider: ({ children }: { children: React.ReactNode }) => children,
  Helmet: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
const mockIntersectionObserver = vi.fn();
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
});
global.IntersectionObserver = mockIntersectionObserver;

// Mock AuthContext
const mockUseAuth = vi.fn();
vi.spyOn(AuthContext, "useAuth").mockImplementation(mockUseAuth);

// Mock API functions
const mockListProfiles = vi.fn();
const mockGetProfileById = vi.fn();
const mockCreateProfile = vi.fn();
const mockUpdateProfileById = vi.fn();
vi.spyOn(Api, "listProfiles").mockImplementation(mockListProfiles);
vi.spyOn(Api, "getProfileById").mockImplementation(mockGetProfileById);
vi.spyOn(Api, "createProfile").mockImplementation(mockCreateProfile);
vi.spyOn(Api, "updateProfileById").mockImplementation(mockUpdateProfileById);

// Helper to render with ProfileProvider
function renderWithProfileProvider(
  ui: React.ReactNode,
  isAuthenticated = true,
  profiles: Profile[] = []
) {
  mockUseAuth.mockReturnValue({ isAuthenticated, user: { id: "1", email: "test@example.com" } });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <ProfileProvider>{children}</ProfileProvider>
  );

  return render(ui, { wrapper });
}

describe("ProfileContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
  });

  describe("ProfileProvider initialization", () => {
    it("loads profiles when authenticated", async () => {
      const mockProfiles: Profile[] = [
        { id: 1, name: "Profile 1", isDefault: true },
        { id: 2, name: "Profile 2" },
      ];

      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockListProfiles.mockResolvedValue(mockProfiles);

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true, mockProfiles);
      });

      expect(mockListProfiles).toHaveBeenCalled();
      expect(profileState.profiles).toEqual(mockProfiles);
    });

    it("clears profiles when not authenticated", async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false, user: null });

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, false);
      });

      expect(profileState.profiles).toEqual([]);
      expect(profileState.activeProfile).toBeNull();
    });

    it("restores active profile from localStorage", async () => {
      const mockProfiles: Profile[] = [
        { id: 1, name: "Profile 1" },
        { id: 2, name: "Profile 2", isDefault: true },
      ];

      localStorageMock.getItem.mockReturnValue("2"); // saved profile id
      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockListProfiles.mockResolvedValue(mockProfiles);

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true, mockProfiles);
      });

      expect(profileState.activeProfile).toEqual(mockProfiles[1]);
    });

    it("falls back to default profile when no saved profile", async () => {
      const mockProfiles: Profile[] = [
        { id: 1, name: "Profile 1" },
        { id: 2, name: "Profile 2", isDefault: true },
      ];

      localStorageMock.getItem.mockReturnValue(null); // no saved profile
      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockListProfiles.mockResolvedValue(mockProfiles);

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true, mockProfiles);
      });

      expect(profileState.activeProfile).toEqual(mockProfiles[1]); // default
    });

    it("falls back to first profile when no default", async () => {
      const mockProfiles: Profile[] = [
        { id: 1, name: "Profile 1" },
        { id: 2, name: "Profile 2" },
      ];

      localStorageMock.getItem.mockReturnValue(null);
      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockListProfiles.mockResolvedValue(mockProfiles);

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true, mockProfiles);
      });

      expect(profileState.activeProfile).toEqual(mockProfiles[0]); // first
    });

    it("handles API error gracefully", async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockListProfiles.mockRejectedValue(new Error("API error"));

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true);
      });

      expect(profileState.profiles).toEqual([]);
    });
  });

  describe("setActiveProfile()", () => {
    it("sets active profile and saves to localStorage", async () => {
      const mockProfiles: Profile[] = [
        { id: 1, name: "Profile 1" },
        { id: 2, name: "Profile 2" },
      ];

      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockListProfiles.mockResolvedValue(mockProfiles);

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true, mockProfiles);
      });

      await act(async () => {
        profileState.setActiveProfile(mockProfiles[1]);
      });

      expect(profileState.activeProfile).toEqual(mockProfiles[1]);
      expect(localStorageMock.setItem).toHaveBeenCalledWith("activeProfileId", "2");
    });

    it("does not save to localStorage if profile has no id", async () => {
      const mockProfiles: Profile[] = [{ id: undefined, name: "No ID Profile" }];

      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockListProfiles.mockResolvedValue(mockProfiles);

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true, mockProfiles);
      });

      await act(async () => {
        profileState.setActiveProfile(mockProfiles[0]);
      });

      expect(profileState.activeProfile).toEqual(mockProfiles[0]);
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });
  });

  describe("refreshProfiles()", () => {
    it("loads profiles and selects default", async () => {
      const mockProfiles: Profile[] = [
        { id: 1, name: "Profile 1" },
        { id: 2, name: "Profile 2", isDefault: true },
      ];

      localStorageMock.getItem.mockReturnValue(null);
      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockListProfiles.mockResolvedValue(mockProfiles);

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true, mockProfiles);
      });

      // Clear previous calls
      vi.clearAllMocks();

      await act(async () => {
        await profileState.refreshProfiles();
      });

      expect(mockListProfiles).toHaveBeenCalled();
      expect(profileState.profiles).toEqual(mockProfiles);
      expect(profileState.activeProfile).toEqual(mockProfiles[1]);
    });

    it("handles error during refresh", async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockListProfiles.mockRejectedValue(new Error("Refresh failed"));

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true);
      });

      await act(async () => {
        await profileState.refreshProfiles();
      });

      expect(profileState.isLoading).toBe(false);
    });
  });

  describe("createProfile()", () => {
    it("creates profile, refreshes list", async () => {
      const newProfile: Profile = { name: "New Profile", isDefault: false };
      const createdProfile: Profile = { id: 3, ...newProfile };

      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockCreateProfile.mockResolvedValue(createdProfile);
      mockListProfiles.mockResolvedValue([createdProfile]);

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true);
      });

      await act(async () => {
        const result = await profileState.createProfile(newProfile);
        expect(result).toEqual(createdProfile);
      });

      expect(mockCreateProfile).toHaveBeenCalledWith(newProfile);
      expect(mockListProfiles).toHaveBeenCalled();
    });

    it("throws error on creation failure", async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockCreateProfile.mockRejectedValue(new Error("Creation failed"));

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true);
      });

      await expect(async () => {
        await profileState.createProfile({ name: "New" });
      }).rejects.toThrow("Creation failed");
    });
  });

  describe("updateProfile()", () => {
    it("updates profile and refreshes list", async () => {
      const updates: Profile = { name: "Updated Profile" };
      const updatedProfile: Profile = { id: 1, ...updates };

      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockUpdateProfileById.mockResolvedValue(updatedProfile);
      mockListProfiles.mockResolvedValue([updatedProfile]);

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true);
      });

      await act(async () => {
        const result = await profileState.updateProfile(1, updates);
        expect(result).toEqual(updatedProfile);
      });

      expect(mockUpdateProfileById).toHaveBeenCalledWith(1, updates);
      expect(mockListProfiles).toHaveBeenCalled();
    });

    it("throws error on update failure", async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: "1", email: "test@example.com" } });
      mockUpdateProfileById.mockRejectedValue(new Error("Update failed"));

      let profileState: any;
      const TestComponent = () => {
        profileState = useProfile();
        return null;
      };

      await act(async () => {
        renderWithProfileProvider(<TestComponent />, true);
      });

      await expect(async () => {
        await profileState.updateProfile(1, { name: "Update" });
      }).rejects.toThrow("Update failed");
    });
  });

  describe("useProfile() error handling", () => {
    it("throws error when used outside Provider", () => {
      const TestComponent = () => {
        expect(() => useProfile()).toThrow("useProfile must be used within a ProfileProvider");
        return null;
      };

      render(<TestComponent />);
    });
  });
});
