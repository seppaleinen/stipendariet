import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { usePremiumStatus, PlanType } from "@/hooks/usePremiumStatus";
import { renderHook, act } from "@testing-library/react";

// Mock the AuthContext
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  getAuthToken: vi.fn(),
}));

import { useAuth, getAuthToken } from "@/contexts/AuthContext";

describe("usePremiumStatus", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns free status when not authenticated", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    const { result } = renderHook(() => usePremiumStatus());

    // Wait for effects to run
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current).toEqual({
      isPremium: false,
      planType: "free" as PlanType,
      creditsRemaining: null,
      subscriptionEnd: null,
      isLoading: false,
      error: null,
      refresh: expect.any(Function),
    });
  });

  it("returns free status when no auth token", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (getAuthToken as vi.Mock).mockReturnValue(null);

    const { result } = renderHook(() => usePremiumStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isPremium).toBe(false);
    expect(result.current.planType).toBe("free");
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("returns subscription status when plan_type is subscription", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (getAuthToken as vi.Mock).mockReturnValue("test-token");
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        plan_type: "subscription",
        credits_remaining: null,
        subscription_end: "2026-12-31",
      }),
    });

    const { result } = renderHook(() => usePremiumStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isPremium).toBe(true);
    expect(result.current.planType).toBe("subscription");
    expect(result.current.creditsRemaining).toBe(null);
    expect(result.current.subscriptionEnd).toBe("2026-12-31");
    expect(result.current.error).toBe(null);
  });

  it("returns credits status when plan_type is credits with remaining > 0", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (getAuthToken as vi.Mock).mockReturnValue("test-token");
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        plan_type: "credits",
        credits_remaining: 5,
        subscription_end: null,
      }),
    });

    const { result } = renderHook(() => usePremiumStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isPremium).toBe(true);
    expect(result.current.planType).toBe("credits");
    expect(result.current.creditsRemaining).toBe(5);
  });

  it("returns free status when plan_type is credits with 0 remaining", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (getAuthToken as vi.Mock).mockReturnValue("test-token");
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        plan_type: "credits",
        credits_remaining: 0,
        subscription_end: null,
      }),
    });

    const { result } = renderHook(() => usePremiumStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isPremium).toBe(false);
    expect(result.current.planType).toBe("credits");
    expect(result.current.creditsRemaining).toBe(0);
  });

  it("handles 404 response (endpoint not found) - defaults to free", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (getAuthToken as vi.Mock).mockReturnValue("test-token");
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    });

    const { result } = renderHook(() => usePremiumStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isPremium).toBe(false);
    expect(result.current.planType).toBe("free");
    expect(result.current.error).toBe(null);
  });

  it("handles fetch error - defaults to free with error message", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (getAuthToken as vi.Mock).mockReturnValue("test-token");
    mockFetch.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => usePremiumStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isPremium).toBe(false);
    expect(result.current.planType).toBe("free");
    expect(result.current.error).toBe("Kunde inte hämta prenumerationsstatus");
  });

  it("handles non-404 error response - defaults to free with error message", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (getAuthToken as vi.Mock).mockReturnValue("test-token");
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });

    const { result } = renderHook(() => usePremiumStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isPremium).toBe(false);
    expect(result.current.error).toBe("Kunde inte hämta prenumerationsstatus");
  });

  it("refresh function re-fetches premium status", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (getAuthToken as vi.Mock).mockReturnValue("test-token");
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        plan_type: "subscription",
        credits_remaining: 10,
        subscription_end: "2027-01-01",
      }),
    });

    const { result } = renderHook(() => usePremiumStatus());

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.isPremium).toBe(true);

    // Call refresh
    await act(async () => {
      await result.current.refresh();
    });

    // Should have called fetch again
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(result.current.creditsRemaining).toBe(10);
  });

  it("sets isLoading to true during fetch", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (getAuthToken as vi.Mock).mockReturnValue("test-token");

    let resolveFetch: () => void;
    const fetchPromise = new Promise<void>((resolve) => {
      resolveFetch = resolve;
    });
    mockFetch.mockReturnValue(
      Promise.resolve({
        ok: true,
        json: async () => ({ plan_type: "subscription" }),
      }) as any,
    );

    const { result } = renderHook(() => usePremiumStatus());

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    // Resolve the fetch
    resolveFetch!();

    // After resolution, should no longer be loading
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });
    expect(result.current.isLoading).toBe(false);
  });

  it("returns isLoading when authLoading is true", async () => {
    (useAuth as vi.Mock).mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    const { result } = renderHook(() => usePremiumStatus());
    expect(result.current.isLoading).toBe(true);
  });
});
