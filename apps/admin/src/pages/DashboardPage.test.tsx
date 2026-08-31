import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DashboardPage from './DashboardPage';

// -- Mutable module-scope variables for react-router-dom mock --
let mockNavigate: ReturnType<typeof vi.fn>;

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: '/', state: null }),
  Link: ({ children, to }: any) => <a href={to}>{children}</a>,
  Navigate: () => null,
  Outlet: () => null,
}));

// -- Mutable mock for useAuth --
const mockLogout = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    login: vi.fn(),
    user: { id: '1', email: 'anna@example.com', name: 'Anna Svensson', role: 'admin' },
    logout: mockLogout,
    isAuthenticated: true,
    isLoading: false,
  }),
}));

const renderPage = () => render(<DashboardPage />);

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate = vi.fn();
  });

  // TC-D1: renders dashboard heading and description
  it('renders dashboard heading and description', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: 'Admin Dashboard' })).toBeInTheDocument();
    expect(
      screen.getByText('Manage scholarships and review pending applications'),
    ).toBeInTheDocument();
  });

  // TC-D2: displays welcome message with user name
  it('displays welcome message with user name', () => {
    renderPage();

    expect(screen.getByText('Welcome, Anna Svensson')).toBeInTheDocument();
  });

  // TC-D3: renders three navigation card titles
  it('renders three navigation card titles', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: 'Scholarship Queue' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Review Processed Items' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Statistics' })).toBeInTheDocument();
  });

  // TC-D4: renders card descriptions
  it('renders card descriptions', () => {
    renderPage();

    expect(screen.getByText('Items pending review')).toBeInTheDocument();
    expect(screen.getByText('Recently processed scholarship data')).toBeInTheDocument();
    expect(screen.getByText('Overall platform metrics')).toBeInTheDocument();
  });

  // TC-D5: renders View Queue button
  it('renders View Queue button', () => {
    renderPage();

    expect(screen.getByRole('button', { name: 'View Queue' })).toBeInTheDocument();
  });

  // TC-D6: renders 2 "Coming soon" labels
  it('renders two Coming soon labels', () => {
    renderPage();

    const comingSoon = screen.getAllByText('Coming soon');
    expect(comingSoon).toHaveLength(2);
  });

  // TC-D7: View Queue button navigates to /queue
  it('navigates to /queue when View Queue is clicked', () => {
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'View Queue' }));
    expect(mockNavigate).toHaveBeenCalledWith('/queue');
  });

  // TC-D8: Logout button calls logout and navigates to /login
  it('calls logout and navigates to /login on logout click', () => {
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Logout' }));
    expect(mockLogout).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  // TC-D9: renders logout button
  it('renders logout button', () => {
    renderPage();

    expect(screen.getByRole('button', { name: 'Logout' })).toBeInTheDocument();
  });
});
