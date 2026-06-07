import { describe, it, expect } from "vitest";
import { cn, formatFoundationText, formatParagraph, cleanTextForPreview } from "@/lib/utils";

describe("cn (tailwind-merge utility)", () => {
  it("merges class names correctly", () => {
    expect(cn("text-red-500", "bg-blue-500")).toBe("text-red-500 bg-blue-500");
  });

  it("handles conditional classes", () => {
    const isActive = true;
    expect(cn("base-class", isActive && "active-class")).toBe("base-class active-class");
  });

  it("handles falsy conditional classes", () => {
    const isActive = false;
    expect(cn("base-class", isActive && "active-class")).toBe("base-class");
  });

  it("handles clsx array format", () => {
    expect(cn(["class-a", "class-b"])).toBe("class-a class-b");
  });

  it("handles object format", () => {
    expect(cn({ "class-a": true, "class-b": false })).toBe("class-a");
  });

  it("merges conflicting classes correctly", () => {
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("returns empty string for no input", () => {
    expect(cn()).toBe("");
  });

  it("returns empty string for falsy input", () => {
    expect(cn("", null, undefined, false)).toBe("");
  });
});

describe("formatFoundationText", () => {
  it("returns empty array for null input", () => {
    expect(formatFoundationText(null)).toEqual([]);
  });

  it("returns empty array for undefined input", () => {
    expect(formatFoundationText(undefined)).toEqual([]);
  });

  it("returns empty array for empty string", () => {
    expect(formatFoundationText("")).toEqual([]);
  });

  it("splits text on double newlines into paragraphs", () => {
    const text = "First paragraph\n\nSecond paragraph\n\nThird paragraph";
    expect(formatFoundationText(text)).toEqual([
      "First paragraph",
      "Second paragraph",
      "Third paragraph",
    ]);
  });

  it("normalizes Windows line breaks", () => {
    const text = "First\r\n\r\nSecond";
    expect(formatFoundationText(text)).toEqual(["First", "Second"]);
  });

  it("unescapes forward slashes", () => {
    const text = "Path: C:\\/Program Files";
    expect(formatFoundationText(text)).toEqual(["Path: C:/Program Files"]);
  });

  it("unescapes quotes", () => {
    const text = 'He said \\"Hello\\"';
    expect(formatFoundationText(text)).toEqual(['He said "Hello"']);
  });

  it("filters out whitespace-only paragraphs", () => {
    const text = "First\n\n   \n\nSecond";
    expect(formatFoundationText(text)).toEqual(["First", "Second"]);
  });

  it("handles text without double newlines", () => {
    const text = "Single paragraph";
    expect(formatFoundationText(text)).toEqual(["Single paragraph"]);
  });
});

describe("formatParagraph", () => {
  it("splits text on single newlines", () => {
    const text = "Line 1\nLine 2\nLine 3";
    expect(formatParagraph(text)).toEqual(["Line 1", "Line 2", "Line 3"]);
  });

  it("filters out empty lines", () => {
    const text = "Line 1\n\nLine 2";
    expect(formatParagraph(text)).toEqual(["Line 1", "Line 2"]);
  });

  it("returns array for single line", () => {
    expect(formatParagraph("Single line")).toEqual(["Single line"]);
  });

  it("handles text with trailing newline", () => {
    const text = "Line 1\nLine 2\n";
    expect(formatParagraph(text)).toEqual(["Line 1", "Line 2"]);
  });
});

describe("cleanTextForPreview", () => {
  it("returns empty string for null input", () => {
    expect(cleanTextForPreview(null)).toBe("");
  });

  it("returns empty string for undefined input", () => {
    expect(cleanTextForPreview(undefined)).toBe("");
  });

  it("normalizes all newlines to spaces", () => {
    const text = "Line 1\n\nLine 2\nLine 3";
    expect(cleanTextForPreview(text)).toBe("Line 1 Line 2 Line 3");
  });

  it("unescapes forward slashes", () => {
    const text = "Path: C:\\/Program Files";
    expect(cleanTextForPreview(text)).toBe("Path: C:/Program Files");
  });

  it("unescapes quotes", () => {
    const text = 'He said \\"Hello\\"';
    expect(cleanTextForPreview(text)).toBe('He said "Hello"');
  });

  it("collapses multiple spaces to single space", () => {
    const text = "Multiple    spaces";
    expect(cleanTextForPreview(text)).toBe("Multiple spaces");
  });

  it("trims whitespace from ends", () => {
    const text = "  trimmed  ";
    expect(cleanTextForPreview(text)).toBe("trimmed");
  });

  it("handles empty string", () => {
    expect(cleanTextForPreview("")).toBe("");
  });

  it("handles complex text", () => {
    const text = "First\r\n\r\nSecond\nThird\n\nFourth";
    expect(cleanTextForPreview(text)).toBe("First Second Third Fourth");
  });
});
