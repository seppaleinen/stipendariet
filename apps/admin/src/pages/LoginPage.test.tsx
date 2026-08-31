import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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

// -- Mutable mock for useAuth --
const mockLogin = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    user: null,
    logout: vi.fn(),
    isAuthenticated: false,
    isLoading: false,
  }),
}));

const renderPage = () => render(<LoginPage />);

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate = vi.fn();
    mockLocationState = null;
  });

  // TC-L1: renders login form with all expected elements
  it('renders login form with title, description, fields, and submit button', () => {
    renderPage();

    expect(screen.getByRole('heading', { name: 'Admin Login' })).toBeInTheDocument();
    expect(screen.getByText('Enter your credentials to access the admin panel')).toBeInTheDocument();

    const emailInput = screen.getByLabelText('Email');
    expect(emailInput).toHaveAttribute('type', 'email');

    const passwordInput = screen.getByLabelText('Password');
    expect(passwordInput).toHaveAttribute('type', 'password');

    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });

  // TC-L2: validation errors for empty submission
  it('shows validation errors when submitting empty form', async () => {
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(
      await screen.findByText('Please enter a valid email address'),
    ).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  // TC-L3: email format error
  it('shows email format error for invalid email', async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'not-an-email' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'somepassword' },
    });
    // Fire submit event directly on the form to bypass HTML5 type="email"
    // constraint validation, which would otherwise block the submit and
    // prevent react-hook-form's zod validation from running.
    fireEvent.submit(screen.getByRole('button', { name: 'Sign in' }).closest('form')!);

    expect(
      await screen.findByText('Please enter a valid email address'),
    ).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  // TC-L4: calls login with email and password
  it('calls login with email and password on valid submission', async () => {
    mockLogin.mockResolvedValue(true);
    renderPage();

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'admin@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'secret123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('admin@example.com', 'secret123');
    });
  });

  // TC-L5: navigates to '/' on successful login (no location state)
  it('navigates to / on successful login when no redirect state', async () => {
    mockLogin.mockResolvedValue(true);
    renderPage();

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'admin@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'secret123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  // TC-L6: navigates to location.state.from.pathname
  it('navigates to location.state.from.pathname on successful login', async () => {
    mockLocationState = { from: { pathname: '/queue' } };
    mockLogin.mockResolvedValue(true);
    renderPage();

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'admin@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'secret123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/queue', { replace: true });
    });
  });

  // TC-L7: shows error on login failure
  it('shows error message when login fails', async () => {
    mockLogin.mockResolvedValue(false);
    renderPage();

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'admin@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrongpass' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(
      await screen.findByText(
        'Inloggningen misslyckades. Kontrollera dina uppgifter och försök igen.',
      ),
    ).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // TC-L8: disables submit button and shows "Signing in..." while pending
  it('disables submit button and shows signing in text while login is pending', async () => {
    let resolveLogin: (value: boolean) => void;
    mockLogin.mockImplementation(
      () => new Promise<boolean>((resolve) => { resolveLogin = resolve; }),
    );
    renderPage();

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'admin@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'secret123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    // Button should show "Signing in..." and be disabled
    await waitFor(() => {
      const btn = screen.getByRole('button', { name: 'Signing in...' });
      expect(btn).toBeDisabled();
    });

    // Resolve the promise
    resolveLogin!(true);

    // Button should revert
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Sign in' })).not.toBeDisabled();
    });
  });

  // TC-L9: clears previous error on new submission attempt
  it('clears previous error on new submission attempt', async () => {
    // First attempt: failure
    mockLogin.mockResolvedValueOnce(false);
    renderPage();

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'admin@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrongpass' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(
      await screen.findByText(
        'Inloggningen misslyckades. Kontrollera dina uppgifter och försök igen.',
      ),
    ).toBeInTheDocument();

    // Second attempt: success
    mockLogin.mockResolvedValueOnce(true);
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(
        screen.queryByText(
          'Inloggningen misslyckades. Kontrollera dina uppgifter och försök igen.',
        ),
      ).not.toBeInTheDocument();
    });
  });
});
