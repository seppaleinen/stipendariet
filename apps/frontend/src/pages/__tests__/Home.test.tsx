import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import Home from "../Home";

// Link renders as a real anchor so href assertions are valid (overrides test-setup.ts).
vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
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
  it("renders the hero heading", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Välkommen till StipendieAssistenten"
    );
  });

  it("renders hero section with a subtitle", () => {
    render(<Home />);
    expect(
      screen.getByText(/Din guide till att hitta och ansöka om stipendier/)
    ).toBeInTheDocument();
  });

  it("renders the Skapa profil CTA button linking to /profile-setup", () => {
    render(<Home />);
    const profileLink = screen.getByRole("link", { name: /Skapa profil/ });
    expect(profileLink).toHaveAttribute("href", "/profile-setup");
  });

  it("renders the Utforska Stipendier CTA button linking to /grants", () => {
    render(<Home />);
    const grantsLink = screen.getByRole("link", { name: /Utforska Stipendier/ });
    expect(grantsLink).toHaveAttribute("href", "/grants");
  });

  it("renders all four feature cards", () => {
    render(<Home />);
    expect(screen.getByText("Personlig Profil")).toBeInTheDocument();
    expect(screen.getByText("Hitta Stipendier")).toBeInTheDocument();
    expect(screen.getByText("Spåra Ansökningar")).toBeInTheDocument();
    expect(screen.getByText("AI-Assisterad Ansökan")).toBeInTheDocument();
  });

  it("feature card links point to the correct routes", () => {
    render(<Home />);
    // Personlig Profil → /profile-setup
    expect(
      screen.getByRole("link", { name: /Kom igång/i })
    ).toHaveAttribute("href", "/profile-setup");

    // Hitta Stipendier → /grants
    expect(
      screen.getByRole("link", { name: /Börja söka/i })
    ).toHaveAttribute("href", "/grants");

    // Spåra Ansökningar → /applications
    expect(
      screen.getByRole("link", { name: /Se ansökningar/i })
    ).toHaveAttribute("href", "/applications");

    // AI-Assisterad Ansökan → /generate
    expect(
      screen.getByRole("link", { name: /Prova nu/i })
    ).toHaveAttribute("href", "/generate");
  });
});
