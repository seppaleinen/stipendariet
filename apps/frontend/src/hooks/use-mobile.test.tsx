import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useIsMobile } from "@/hooks/use-mobile";
import { renderHook } from "@testing-library/react";

const createMatchMediaMock = (matches: boolean) => (query: string) => ({
  matches,
  media: query,
  onchange: null,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  addListener: vi.fn(),
  removeListener: vi.fn(),
  dispatchEvent: vi.fn(),
});

describe("useIsMobile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "matchMedia").mockImplementation(createMatchMediaMock(false));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns false when window width >= 768px", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 1024,
    });

    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });

  it("returns true when window width < 768px", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 600,
    });

    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });

  it("should set up event listener on mount", () => {
    const addEventListenerSpy = vi.fn();
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 1024,
    });
    vi.spyOn(window, "matchMedia").mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: addEventListenerSpy,
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    renderHook(() => useIsMobile());
    expect(addEventListenerSpy).toHaveBeenCalledWith("change", expect.any(Function));
  });

  it("should clean up event listener on unmount", () => {
    const removeEventListenerSpy = vi.fn();
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 1024,
    });
    vi.spyOn(window, "matchMedia").mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: removeEventListenerSpy,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const { unmount } = renderHook(() => useIsMobile());
    unmount();
    expect(removeEventListenerSpy).toHaveBeenCalledWith("change", expect.any(Function));
  });

  it("returns boolean type (not undefined or null)", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 600,
    });

    const { result } = renderHook(() => useIsMobile());
    expect(typeof result.current).toBe("boolean");
    expect(result.current).not.toBeUndefined();
    expect(result.current).not.toBe(null);
  });
});
