import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getGrants,
  getGrant,
  getSavedGrants,
  saveGrant,
  removeSavedGrant,
  getApplications,
  createApplication,
  updateApplication,
  deleteApplication,
  getProfile,
  saveProfile,
  generateApplicationWithAI,
  findMatchingFoundations,
  findMatchingFoundationsByProfile,
} from "./api";
import * as AuthContext from "@/contexts/AuthContext";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Helper: wraps a partial Response-like object with required defaults for the api-client
function mockFetchResponse(overrides: Record<string, any> = {}): any {
  return {
    ok: true,
    status: 200,
    headers: { get: () => "application/json" } as unknown as Headers,
    json: async () => ({}),
    text: async () => "",
    ...overrides,
  };
}

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

// Mock AuthContext getAuthToken
const mockGetAuthToken = vi.fn();
vi.spyOn(AuthContext, "getAuthToken").mockImplementation(mockGetAuthToken);

describe("API Functions Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockClear();
    mockGetAuthToken.mockClear();
  });

  describe("getGrants()", () => {
    it("fetches grants and maps from backend", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      const mockResponse = {
        grants: [
          { id: 1, name: "Test Grant", description: "Test description", category: "Education" },
        ],
        total: 1,
        has_more: false,
      };

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => mockResponse,
      }));

      const result = await getGrants({ limit: 10 });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/grants"),
        expect.any(Object)
      );
      expect(result.grants).toHaveLength(1);
      expect(result.grants[0].title).toBe("Test Grant");
      expect(result.grants[0].category).toBe("Education");
      expect(result.total).toBe(1);
    });

    it("handles pagination parameters", async () => {
      mockGetAuthToken.mockReturnValue("test-token");

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => ({ grants: [], total: 0, has_more: false }),
      }));

      await getGrants({ category: "Education", search: "test", skip: 10, limit: 20 });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("category=Education"),
        expect.any(Object)
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("search=test"),
        expect.any(Object)
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("skip=10"),
        expect.any(Object)
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("limit=20"),
        expect.any(Object)
      );
    });

    it("throws on error", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockRejectedValue(new Error("Network error"));

      await expect(getGrants()).rejects.toThrow();
    });

    it("throws on 401 response", async () => {
      mockGetAuthToken.mockReturnValue("expired-token");
      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: false,
        status: 401,
        json: async () => ({}),
      }));

      await expect(getGrants()).rejects.toThrow();
    });

    it("throws on invalid response format", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => ({ error: "bad format" }),
      }));
    
      await expect(getGrants()).rejects.toThrow();
    });

    it("throws on malformed JSON", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => {
          throw new Error("Unexpected token < in JSON at position 0");
        },
      }));
    
      await expect(getGrants()).rejects.toThrow("Unexpected token < in JSON at position 0");
    });

    it("throws on network timeout", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockRejectedValue(new Error("Network timeout"));
    
      await expect(getGrants()).rejects.toThrow("Network timeout");
    });
  });

  describe("getGrant()", () => {
    it("fetches single grant and maps from backend", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      const mockGrant = { id: 1, name: "Single Grant", description: "Details" };

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => mockGrant,
      }));

      const result = await getGrant("1");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/grants/1"),
        expect.any(Object)
      );
      expect(result).toBeDefined();
      expect(result?.title).toBe("Single Grant");
    });

    it("returns undefined on 404", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: false,
        status: 404,
        json: async () => ({}),
      }));

      const result = await getGrant("nonexistent");

      expect(result).toBeUndefined();
    });

    it("throws on error", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockRejectedValue(new Error("Error"));

      await expect(getGrant("1")).rejects.toThrow();
    });
  });

  describe("getSavedGrants()", () => {
    it("returns saved grant IDs", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => ({ saved_grants: ["grant-1", "grant-2"] }),
      }));

      const result = await getSavedGrants();

      expect(result).toEqual(["grant-1", "grant-2"]);
    });

    it("throws on 401", async () => {
      mockGetAuthToken.mockReturnValue("expired-token");
      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: false,
        status: 401,
      }));

      await expect(getSavedGrants()).rejects.toThrow();
    });

    it("throws on invalid response format", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => ({ error: "bad format" }),
      }));

      await expect(getSavedGrants()).rejects.toThrow();
    });

    it("throws on error", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockRejectedValue(new Error("Error"));

      await expect(getSavedGrants()).rejects.toThrow();
    });
  });

  describe("saveGrant()", () => {
    it("saves a grant with POST request", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: true }));

      await expect(saveGrant("grant-123")).resolves.toBeUndefined();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/profile/saved-grants"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
          body: JSON.stringify({ grant_id: "grant-123" }),
        })
      );
    });

    it("throws on error", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 400 }));

      await expect(saveGrant("grant-123")).rejects.toThrow();
    });
  });

  describe("removeSavedGrant()", () => {
    it("removes a saved grant with DELETE request", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: true }));

      await expect(removeSavedGrant("grant-123")).resolves.toBeUndefined();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/profile/saved-grants/grant-123"),
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });

    it("throws on error", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 404 }));

      await expect(removeSavedGrant("grant-123")).rejects.toThrow();
    });
  });

  describe("getApplications()", () => {
    it("returns applications mapped from backend", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      const mockApps = [
        { id: 1, grant_id: "g1", grant_name: "Grant A", status: "submitted" },
      ];

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => mockApps,
      }));

      const result = await getApplications();

      expect(result).toHaveLength(1);
      expect(result[0].grantTitle).toBe("Grant A");
      expect(result[0].status).toBe("submitted");
    });

    it("throws on 401", async () => {
      mockGetAuthToken.mockReturnValue("expired");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 401 }));

      await expect(getApplications()).rejects.toThrow();
    });

    it("throws on invalid response format", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => ({ data: [] }),
      }));

      await expect(getApplications()).rejects.toThrow();
    });
  });

  describe("createApplication()", () => {
    it("creates application with POST", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      const mockApp = { id: 1, status: "draft" };

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => mockApp,
      }));

      const result = await createApplication({ grantId: "g1", content: "My application" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/applications"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ grant_id: "g1", content: "My application" }),
        })
      );
      expect(result.id).toBe("1");
    });

    it("throws on error", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 400 }));

      await expect(createApplication({ grantId: "g1" })).rejects.toThrow();
    });
  });

  describe("updateApplication()", () => {
    it("updates application with PATCH", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      const mockApp = { id: 1, status: "submitted" };

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => mockApp,
      }));

      const result = await updateApplication("1", { status: "submitted" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/applications/1"),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ content: undefined, status: "submitted" }),
        })
      );
      expect(result.status).toBe("submitted");
    });

    it("throws on error", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 404 }));

      await expect(updateApplication("1", {})).rejects.toThrow();
    });
  });

  describe("deleteApplication()", () => {
    it("deletes application with DELETE", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: true }));

      await expect(deleteApplication("1")).resolves.toBeUndefined();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/applications/1"),
        expect.objectContaining({ method: "DELETE" })
      );
    });

    it("throws on error", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 404 }));

      await expect(deleteApplication("1")).rejects.toThrow();
    });
  });

  describe("getProfile()", () => {
    it("returns null on 404", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 404 }));

      const result = await getProfile();
      expect(result).toBeNull();
    });

    it("returns null on 401", async () =>{
      mockGetAuthToken.mockReturnValue("expired");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 401 }));

      const result = await getProfile();
      expect(result).toBeNull();
    });

    it("returns mapped profile on success", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => ({ id: 1, name: "Profile" }),
      }));

      const result = await getProfile();
      expect(result?.name).toBe("Profile");
    });

    it("throws on error", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockRejectedValue(new Error("Error"));

      await expect(getProfile()).rejects.toThrow();
    });
  });

  describe("saveProfile()", () => {
    it("saves profile with PUT", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      const mockProfile = { id: 1, name: "Saved" };

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => mockProfile,
      }));

      const result = await saveProfile({ name: "Saved" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/profile/family"),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({
            name: "Saved",
            is_default: undefined,
            lifeSituations: [],
            healthConditions: [],
            occupations: [],
            supportPurposes: [],
          }),
        })
      );
      expect(result.name).toBe("Saved");
    });

    it("throws on error", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 400 }));

      await expect(saveProfile({ name: "Test" })).rejects.toThrow();
    });
  });

  describe("generateApplicationWithAI()", () => {
    it("generates application via foundation-sync generate-application", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      const mockResponse = { response: "AI generated content", model_used: "phi3:14b" };

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => mockResponse,
      }));

      const result = await generateApplicationWithAI("grant-1", "Context");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/foundation-sync/generate-application"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ prompt: "Context" }),
        })
      );
      expect(result.generated_text).toBe("AI generated content");
      expect(result.credits_remaining).toBeNull();
    });

    it("throws on error", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 429 }));

      await expect(generateApplicationWithAI("grant-1")).rejects.toThrow();
    });
  });

  describe("findMatchingFoundations()", () =>{
    it("finds matching foundations", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      const mockResponse = [
        { foundation: { id: 1, name: "Foundation A" }, similarity_score: 0.8 },
      ];

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => mockResponse,
      }));

      const result = await findMatchingFoundations("Student", 0.3, 10);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/foundations/matching"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ needs: "Student", threshold: 0.3, limit: 10 }),
        })
      );
      expect(result).toHaveLength(1);
      expect(result[0].foundation.name).toBe("Foundation A");
    });

    it("throws on error", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 500 }));

      await expect(findMatchingFoundations("Student")).rejects.toThrow();
    });
  });

  describe("findMatchingFoundationsByProfile()", () =>{
    it("finds matching foundations by profile", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      const mockResponse = [
        { foundation: { id: 2, name: "Foundation B" }, similarity_score: 0.7 },
      ];

      mockFetch.mockResolvedValue(mockFetchResponse({
        ok: true,
        json: async () => mockResponse,
      }));

      const result = await findMatchingFoundationsByProfile(1, true, 0.25, 20);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/foundations/matching-by-profile"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            profile_id: 1,
            use_geographic_filter: true,
            use_description: false,
            threshold: 0.25,
            limit: 20,
          }),
        })
      );
      expect(result).toHaveLength(1);
      expect(result[0].foundation.name).toBe("Foundation B");
    });

    it("throws on error with detail message", async () =>{
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 400, json: async () => ({ detail: "Invalid profile ID" }) }));

      await expect(findMatchingFoundationsByProfile(999)).rejects.toThrow("Invalid profile ID");
    });

    it("throws on error without detail", async () => {
      mockGetAuthToken.mockReturnValue("test-token");
      mockFetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 500 }));

      await expect(findMatchingFoundationsByProfile(1)).rejects.toThrow();
    });
  });
});
