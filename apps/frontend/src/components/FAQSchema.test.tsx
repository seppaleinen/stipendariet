import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import FAQSchema, { FAQSection, FAQ_CONTENT } from "./FAQSchema";
import type { FAQTopic } from "./FAQSchema";

// Mock react-helmet-async (global in test-setup.ts renders children inline)
vi.mock("react-helmet-async", () => ({
  HelmetProvider: ({ children }: { children: React.ReactNode }) => children,
  Helmet: ({ children }: { children: React.ReactNode }) => children,
}));

function getJsonLdScripts(): HTMLScriptElement[] {
  return Array.from(
    document.querySelectorAll('script[type="application/ld+json"]')
  ) as HTMLScriptElement[];
}

function parseJsonLd(script: HTMLScriptElement) {
  return JSON.parse(script.textContent ?? "");
}

function getFaqsForTopic(topic: FAQTopic) {
  return FAQ_CONTENT[topic];
}

// ─── FAQSchema: JSON-LD tests ───────────────────────────────────────────────

describe("FAQSchema", () => {
  it('emits JSON-LD with "FAQPage" type', () => {
    render(<FAQSchema topic="general" />);
    const schema = getJsonLdScripts()
      .map(parseJsonLd)
      .find((s) => s["@type"] === "FAQPage");
    expect(schema).toBeDefined();
  });

  it("general topic emits 4 Q&As", () => {
    render(<FAQSchema topic="general" />);
    const schema = getJsonLdScripts()
      .map(parseJsonLd)
      .find((s) => s["@type"] === "FAQPage");
    expect(schema?.mainEntity).toHaveLength(4);
  });

  it("search topic emits 3 Q&As about searching", () => {
    render(<FAQSchema topic="search" />);
    const schema = getJsonLdScripts()
      .map(parseJsonLd)
      .find((s) => s["@type"] === "FAQPage");
    expect(schema?.mainEntity).toHaveLength(3);
  });

  it("applying topic emits 3 Q&As about applications", () => {
    render(<FAQSchema topic="applying" />);
    const schema = getJsonLdScripts()
      .map(parseJsonLd)
      .find((s) => s["@type"] === "FAQPage");
    expect(schema?.mainEntity).toHaveLength(3);
  });

  it("default topic is general (4 Q&As)", () => {
    render(<FAQSchema />);
    const schema = getJsonLdScripts()
      .map(parseJsonLd)
      .find((s) => s["@type"] === "FAQPage");
    expect(schema?.mainEntity).toHaveLength(4);
  });

  it("JSON-LD questions match the visible markup questions (general)", () => {
    render(<FAQSchema topic="general" />);
    const schema = getJsonLdScripts()
      .map(parseJsonLd)
      .find((s) => s["@type"] === "FAQPage");
    const jsonQuestions = schema?.mainEntity.map(
      (e: { name: string }) => e.name
    ) ?? [];

    const contentQuestions = getFaqsForTopic("general").map((f) => f.q);
    expect(jsonQuestions).toEqual(contentQuestions);
  });

  it("JSON-LD questions match the visible markup questions (search)", () => {
    render(<FAQSchema topic="search" />);
    const schema = getJsonLdScripts()
      .map(parseJsonLd)
      .find((s) => s["@type"] === "FAQPage");
    const jsonQuestions = schema?.mainEntity.map(
      (e: { name: string }) => e.name
    ) ?? [];

    const contentQuestions = getFaqsForTopic("search").map((f) => f.q);
    expect(jsonQuestions).toEqual(contentQuestions);
  });

  it("JSON-LD questions match the visible markup questions (applying)", () => {
    render(<FAQSchema topic="applying" />);
    const schema = getJsonLdScripts()
      .map(parseJsonLd)
      .find((s) => s["@type"] === "FAQPage");
    const jsonQuestions = schema?.mainEntity.map(
      (e: { name: string }) => e.name
    ) ?? [];

    const contentQuestions = getFaqsForTopic("applying").map((f) => f.q);
    expect(jsonQuestions).toEqual(contentQuestions);
  });
});

// ─── FAQSection: Visible markup tests ───────────────────────────────────────

describe("FAQSection", () => {
  it('renders "Vanliga frågor" heading', () => {
    render(<FAQSection topic="general" />);
    expect(
      screen.getByRole("heading", { level: 2, name: /Vanliga frågor/i })
    ).toBeInTheDocument();
  });

  it("section is a11y-labeled with aria-labelledby", () => {
    render(<FAQSection topic="general" />);
    const section = document.querySelector("section");
    expect(section).toHaveAttribute("aria-labelledby", "faq-heading");
  });

  it("general topic renders 4 <details> elements", () => {
    render(<FAQSection topic="general" />);
    const details = Array.from(document.querySelectorAll("details"));
    expect(details).toHaveLength(4);
  });

  it("search topic renders 3 <details> elements", () => {
    render(<FAQSection topic="search" />);
    const details = Array.from(document.querySelectorAll("details"));
    expect(details).toHaveLength(3);
  });

  it("applying topic renders 3 <details> elements", () => {
    render(<FAQSection topic="applying" />);
    const details = Array.from(document.querySelectorAll("details"));
    expect(details).toHaveLength(3);
  });

  it("default topic is general", () => {
    render(<FAQSection />);
    const details = Array.from(document.querySelectorAll("details"));
    expect(details).toHaveLength(4);
  });

  it("renders the correct questions for general topic", () => {
    render(<FAQSection topic="general" />);
    const expected = getFaqsForTopic("general").map((f) => f.q);
    expected.forEach((q) => {
      expect(screen.getByText(q)).toBeInTheDocument();
    });
  });

  it("renders the correct questions for search topic", () => {
    render(<FAQSection topic="search" />);
    const expected = getFaqsForTopic("search").map((f) => f.q);
    expected.forEach((q) => {
      expect(screen.getByText(q)).toBeInTheDocument();
    });
  });

  it("renders the correct questions for applying topic", () => {
    render(<FAQSection topic="applying" />);
    const expected = getFaqsForTopic("applying").map((f) => f.q);
    expected.forEach((q) => {
      expect(screen.getByText(q)).toBeInTheDocument();
    });
  });

  it("each <details> has a name attribute for native accordion behavior", () => {
    render(<FAQSection topic="general" />);
    const details = Array.from(document.querySelectorAll("details"));
    details.forEach((d) => {
      expect(d.getAttribute("name")).toMatch(/^faq-/);
    });
  });

  it("answers are visible inside <details> elements", () => {
    render(<FAQSection topic="search" />);
    const details = Array.from(document.querySelectorAll("details"));
    expect(details.length).toBe(3);
    const firstDetails = details[0];
    const answerParagraph = firstDetails.querySelector("p");
    expect(answerParagraph).toBeInTheDocument();
    const faqContent = FAQ_CONTENT.search[0];
    expect(answerParagraph).toHaveTextContent(faqContent.a);
  });
});
