import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import LoginPage from './LoginPage';

// -- Mutable module-scope variables for react-router-dom mock --
let mockNavigate: ReturnType<typeof vi.fn>;
let mockLocationState: { from?: { pathname?: string } } | null = null;

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: '/', state: mockLocationState }),
  Link: ({ children, to }: any) => <a href={to}>{children}</a>,
  Navigate: () => null,
  Outlet: () => null,
}));

// -- Mutable mock for useAuth — reflects new exchange-based auth shape --
let mockIsLoading = false;
let mockIsExchanging = false;
const mockExchange = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    exchange: mockExchange,
    user: null,
    isAuthenticated: false,
    isLoading: mockIsLoading,
    isExchanging: mockIsExchanging,
    refreshToken: vi.fn(),
    logout: vi.fn(),
  }),
}));

const renderPage = () => render(<LoginPage />);

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate = vi.fn();
    mockLocationState = null;
    mockIsLoading = false;
    mockIsExchanging = false;
    mockExchange.mockReset();
  });

  // TC-L1: on mount, if not authenticated and not exchanging, calls exchange()
  it('calls exchange on mount when not authenticated and not already exchanging', async () => {
    renderPage();
    await waitFor(() => {
      expect(mockExchange).toHaveBeenCalledTimes(1);
    });
  });

  // TC-L2: spinner renders initially on mount (hasAttempted starts false, effect sets it true)
  it('renders spinner initially on mount', async () => {
    mockIsExchanging = true;
    mockExchange.mockImplementation(() => new Promise(() => {}));
    renderPage();
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  // TC-L3: exchange success → navigates away
  it('navigates to intended route on exchange success', async () => {
    mockExchange.mockResolvedValue(true);
    renderPage();
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  // TC-L4: exchange failure → "Continue with Authentik" card renders
  it('renders "Continue with Authentik" card on exchange failure', async () => {
    mockExchange.mockResolvedValue(false);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Admin Access')).toBeInTheDocument();
      expect(screen.getByText('Continue with Authentik')).toBeInTheDocument();
    });
  });

  // TC-L5: navigation uses location.state.from if present
  it('navigates to location.state.from on exchange success when redirect state present', async () => {
    mockLocationState = { from: { pathname: '/queue' } };
    mockExchange.mockResolvedValue(true);
    renderPage();
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/queue', { replace: true });
    });
  });

  // TC-L6: spinner renders initially before exchange completes
  it('renders spinner initially on mount (hasAttempted starts false)', async () => {
    // Initial mount shows spinner because hasAttempted is false
    mockIsExchanging = true;
    mockExchange.mockImplementation(() => new Promise(() => {}));
    renderPage();
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
  });
});