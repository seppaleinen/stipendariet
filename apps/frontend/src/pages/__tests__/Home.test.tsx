import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import Home from "../Home";

const { mockNavigate } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
}));

// Link renders as a real anchor so href assertions are valid (overrides test-setup.ts).
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
  useParams: () => ({}),
  useLocation: () => ({ pathname: "/" }),
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

describe("Home", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  describe("hero", () => {
    it("renders the matching-first hero heading", () => {
      render(<Home />);
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        "Hitta stipendier som matchar dig"
      );
    });

    it("renders a value proposition subtitle", () => {
      render(<Home />);
      expect(
        screen.getByText(
          /Beskriv din situation och hitta stipendier som passar dina behov/
        )
      ).toBeInTheDocument();
    });
  });

  describe("match entry point", () => {
    it("renders the self-description input and a disabled Matcha button", () => {
      render(<Home />);
      const input = screen.getByLabelText("Beskriv din situation");
      expect(input).toHaveAttribute(
        "placeholder",
        expect.stringContaining("ensamstående förälder")
      );
      expect(screen.getByRole("button", { name: "Matcha" })).toBeDisabled();
    });

    it("keeps Matcha disabled with whitespace-only input", () => {
      render(<Home />);
      fireEvent.change(screen.getByLabelText("Beskriv din situation"), {
        target: { value: "   " },
      });
      expect(screen.getByRole("button", { name: "Matcha" })).toBeDisabled();
    });

    it("scrolls to the county selector (does not navigate) when no county is chosen", () => {
      render(<Home />);
      fireEvent.change(screen.getByLabelText("Beskriv din situation"), {
        target: { value: "matte" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Matcha" }));
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("navigates to /matching with search and county when both are set", async () => {
      render(<Home />);
      fireEvent.change(screen.getByLabelText("Beskriv din situation"), {
        target: { value: "matte" },
      });
      // Select a county via the Radix Select (items render into a portal when opened).
      fireEvent.click(screen.getByRole("combobox"));
      fireEvent.click(await screen.findByText("Skåne län"));
      fireEvent.click(screen.getByRole("button", { name: "Matcha" }));
      expect(mockNavigate).toHaveBeenCalledWith("/matching?search=matte&county=12", {
        replace: true,
      });
    });

    it("shows the county filter hint", () => {
      render(<Home />);
      expect(
        screen.getByText(/Eller välj län för geografisk filtrering:/)
      ).toBeInTheDocument();
    });
  });

  describe("example profiles", () => {
    it("renders the example profiles section heading", () => {
      render(<Home />);
      expect(
        screen.getByRole("heading", { name: "Exempel på profiler" })
      ).toBeInTheDocument();
    });

    it("renders example profile cards with match counts and tags", () => {
      render(<Home />);
      expect(screen.getByText("Student in Malmö")).toBeInTheDocument();
      expect(screen.getByText("Ensamstående förälder, Stockholm")).toBeInTheDocument();
      expect(screen.getByText("Pensionär, Göteborg")).toBeInTheDocument();
      expect(screen.getByText("Konstnär, Uppsala")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument();
      expect(screen.getByText("utbildning")).toBeInTheDocument();
    });

    it("navigates to /matching with the profile search when a card is clicked", () => {
      render(<Home />);
      fireEvent.click(screen.getByText("Student in Malmö"));
      expect(mockNavigate).toHaveBeenCalledWith(
        "/matching?search=Computer+science+student+seeking+education+grants+and+housing+support&county=SE-K",
        { replace: true }
      );
    });
  });

  describe("FAQ", () => {
    it("renders the FAQ section", () => {
      render(<Home />);
      expect(
        screen.getByRole("heading", { name: "Vanliga frågor" })
      ).toBeInTheDocument();
    });
  });
});