import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AdminLayout from './AdminLayout';

// -- Mutable module-scope variables for react-router-dom mock --
let mockPathname = '/';
let mockNavigate: ReturnType<typeof vi.fn>;

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: mockPathname, state: null }),
  // Override the global test-setup Link mock to render real <a> elements so
  // we can inspect href and active-route CSS classes.
  Link: ({ children, to, className }: any) => (
    <a href={to} className={className}>{children}</a>
  ),
  Navigate: () => null,
  Outlet: () => null,
}));

// -- Mutable mock for useAuth using a module-scope variable --
const mockLogout = vi.fn();
let mockUser: { id: string; email: string; name: string; role: string } = {
  id: '1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'admin',
};

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    login: vi.fn(),
    user: mockUser,
    logout: mockLogout,
    isAuthenticated: true,
    isLoading: false,
  }),
}));

const renderLayout = (children?: React.ReactNode) =>
  render(<AdminLayout>{children ?? <div data-testid="child-content">Hello</div>}</AdminLayout>);

describe('AdminLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname = '/';
    mockNavigate = vi.fn();
    // Reset to default user
    mockUser = { id: '1', email: 'test@example.com', name: 'Test User', role: 'admin' };
  });

  // TC-A1: renders all 5 sidebar nav items
  it('renders all 5 sidebar nav items', () => {
    renderLayout();

    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Queue' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Jobs' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Berikningsresultat' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Översättningar' })).toBeInTheDocument();
  });

  // TC-A2: renders brand link "Stipendie Admin"
  it('renders brand link Stipendie Admin', () => {
    renderLayout();

    const brandLink = screen.getByRole('link', { name: 'Stipendie Admin' });
    expect(brandLink).toBeInTheDocument();
    expect(brandLink).toHaveAttribute('href', '/');
  });

  // TC-A3: renders header "Admin Panel"
  it('renders header Admin Panel', () => {
    renderLayout();

    expect(screen.getByRole('heading', { name: 'Admin Panel' })).toBeInTheDocument();
  });

  // TC-A4: displays "Welcome back, Test User" with user name
  it('displays Welcome back with user name', () => {
    renderLayout();

    expect(screen.getByText('Welcome back, Test User')).toBeInTheDocument();
  });

  // TC-A5: displays fallback "Welcome back, Admin" when name missing
  it('displays fallback Welcome back, Admin when name missing', () => {
    mockUser = { id: '1', email: 'test@example.com', name: '', role: 'admin' };

    renderLayout();

    expect(screen.getByText('Welcome back, Admin')).toBeInTheDocument();
  });

  // TC-A6: displays user info in sidebar footer (name + email)
  it('displays user name and email in sidebar footer', () => {
    renderLayout();

    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });

  // TC-A7: falls back to "Admin User" in sidebar footer when name missing
  it('falls back to Admin User in sidebar footer when name missing', () => {
    mockUser = { id: '1', email: 'test@example.com', name: '', role: 'admin' };

    renderLayout();

    expect(screen.getByText('Admin User')).toBeInTheDocument();
  });

  // TC-A8: highlights active route
  it('highlights active route with bg-primary class', () => {
    mockPathname = '/jobs';

    renderLayout();

    const jobsLink = screen.getByRole('link', { name: 'Jobs' });
    expect(jobsLink.className).toContain('bg-primary');
    expect(jobsLink.className).toContain('text-primary-foreground');
  });

  // TC-A9: does not highlight inactive routes
  it('does not highlight inactive routes', () => {
    mockPathname = '/jobs';

    renderLayout();

    const dashboardLink = screen.getByRole('link', { name: 'Dashboard' });
    expect(dashboardLink.className).not.toContain('bg-primary');
  });

  // TC-A10: renders children
  it('renders children', () => {
    renderLayout(<div data-testid="custom-child">Custom Child</div>);

    expect(screen.getByTestId('custom-child')).toBeInTheDocument();
    expect(screen.getByText('Custom Child')).toBeInTheDocument();
  });

  // TC-A11: renders mobile hamburger toggle button
  it('renders mobile hamburger toggle button', () => {
    renderLayout();

    // The hamburger button doesn't have an accessible name, so query by its
    // role+hidden attribute or by the presence of the Menu icon. We look for
    // the button that controls the sidebar.
    const buttons = screen.getAllByRole('button');
    // At least one button should exist (the mobile toggle)
    expect(buttons.length).toBeGreaterThanOrEqual(1);
  });
});
