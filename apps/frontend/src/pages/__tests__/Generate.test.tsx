import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import "@testing-library/jest-dom/vitest";
import Generate from "../Generate";
import * as AuthContext from "@/contexts/AuthContext";
import * as ProfileContext from "@/contexts/ProfileContext";
import * as Api from "@/lib/api";
import type { Grant } from "@/types/grants";

const mockUseAuth = vi.spyOn(AuthContext, "useAuth");
const mockUseProfile = vi.spyOn(ProfileContext, "useProfile");
const mockGetGrant = vi.spyOn(Api, "getGrant");
const mockGenerateApplicationWithAI = vi.spyOn(Api, "generateApplicationWithAI");

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
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
  };
});

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const mockGrant: Grant = {
  id: "grant-1",
  title: "Kunskapsstipendiet",
  summary: "Ett stipendium för studerande.",
  provider: "Utbildningsfonden",
  category: "Utbildning",
  tags: [],
};

const mockProfile = {
  id: 1,
  name: "Test Profile",
  isDefault: true,
};

// Render Generate inside a real MemoryRouter so useParams() returns an optional id.
function renderAt(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/generate" element={<Generate />} />
        <Route path="/generate/:id" element={<Generate />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Generate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { id: "1", email: "test@example.com" },
    } as ReturnType<typeof AuthContext.useAuth>);

    mockUseProfile.mockReturnValue({
      activeProfile: mockProfile,
      isLoading: false,
      profiles: [mockProfile],
    } as ReturnType<typeof ProfileContext.useProfile>);

    mockGetGrant.mockResolvedValue(null);
    mockGenerateApplicationWithAI.mockResolvedValue({
      generated_text: "Detta är en genererad ansökan.",
      credits_remaining: 9,
    });
  });

  it("renders the page heading", async () => {
    renderAt("/generate");
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        "Skapa Ansökan"
      );
    });
  });

  it("shows the foundation info when a grant ID is provided", async () => {
    mockGetGrant.mockResolvedValue(mockGrant);
    renderAt("/generate/grant-1");

    await waitFor(() => {
      expect(screen.getByText("Kunskapsstipendiet")).toBeInTheDocument();
    });
  });

  it("renders the generate button", async () => {
    renderAt("/generate");
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Generera Ansökan/i })
      ).toBeInTheDocument();
    });
  });

  it("generate button is enabled when a profile is active", async () => {
    renderAt("/generate");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Generera Ansökan/i })).not.toBeDisabled();
    });
  });

  it("shows profile prompt when no profile is active", async () => {
    mockUseProfile.mockReturnValue({
      activeProfile: null,
      isLoading: false,
      profiles: [],
    } as ReturnType<typeof ProfileContext.useProfile>);

    renderAt("/generate");
    await waitFor(() => {
      expect(screen.getByText("Ingen profil hittades")).toBeInTheDocument();
      const link = screen.getByRole("link", { name: /Skapa din profil/i });
      expect(link).toHaveAttribute("href", "/profile-setup");
    });
  });

  it("clicking Generate calls the API and shows the generated text", async () => {
    renderAt("/generate");

    const generateBtn = await screen.findByRole("button", { name: /Generera Ansökan/i });

    await act(async () => {
      fireEvent.click(generateBtn);
    });

    await waitFor(() => {
      expect(mockGenerateApplicationWithAI).toHaveBeenCalled();
      expect(screen.getByText("Detta är en genererad ansökan.")).toBeInTheDocument();
    });
  });

  it("shows the generated content textarea after generation", async () => {
    renderAt("/generate");

    const generateBtn = await screen.findByRole("button", { name: /Generera Ansökan/i });

    await act(async () => {
      fireEvent.click(generateBtn);
    });

    await waitFor(() => {
      const textarea = screen.getByRole("textbox");
      expect(textarea).toHaveValue("Detta är en genererad ansökan.");
    });
  });

  it("shows credits remaining after generation", async () => {
    renderAt("/generate");

    const generateBtn = await screen.findByRole("button", { name: /Generera Ansökan/i });

    await act(async () => {
      fireEvent.click(generateBtn);
    });

    await waitFor(() => {
      expect(screen.getByText(/Återstående krediter: 9/)).toBeInTheDocument();
    });
  });
});
