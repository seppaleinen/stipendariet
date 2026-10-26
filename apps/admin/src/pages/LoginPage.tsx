import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@stipendariet/ui';
import { Button } from '@stipendariet/ui';
import { useAuth } from '@/hooks/useAuth';
import { useNavigate, useLocation } from 'react-router-dom';

const LoginPage: React.FC = () => {
  const { exchange, isExchanging, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/';

  // Track whether the page has already attempted an exchange in this mount
  const [hasAttempted, setHasAttempted] = useState(false);
  const [exchangeFailed, setExchangeFailed] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate(redirectTo, { replace: true });
      return;
    }

    // If the provider is already exchanging, wait for it to finish
    if (isExchanging) return;

    // If already attempted (e.g. provider already tried and failed), show fallback
    if (hasAttempted) {
      setExchangeFailed(true);
      return;
    }

    let active = true;
    setHasAttempted(true);

    (async () => {
      const success = await exchange();
      if (!active) return;
      setExchangeFailed(!success);
      if (success) {
        navigate(redirectTo, { replace: true });
      }
    })();

    return () => { active = false; };
  }, [isAuthenticated, isExchanging, exchange, navigate, redirectTo]);

  // Determine what to render based on auth state
  if (isAuthenticated) {
    // About to navigate away — render nothing so router can replace
    return null;
  }

  if (isExchanging || !hasAttempted) {
    // Initial mount or provider/exchange in flight — show spinner
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted p-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" role="status" aria-label="Loading" data-testid="loading-spinner"></div>
      </div>
    );
  }

  if (exchangeFailed) {
    // Exchange failed — show "Continue with Authentik" fallback
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-muted p-4">
        <Card className="w-full max-w-md text-center">
          <CardHeader>
            <CardTitle>Admin Access</CardTitle>
          </CardHeader>
          <CardDescription>
            Your account is authenticated via Authentik. Please continue below.
          </CardDescription>
          <CardContent className="pt-4">
            <Button
              onClick={() => window.location.reload()}
              className="w-full"
            >
              Continue with Authentik
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Fallback — should not reach here
  return null;
};

export default LoginPage;