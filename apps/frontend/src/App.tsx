import { Toaster, SonnerToaster as Sonner, TooltipProvider } from "@stipendariet/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { Routes, Route, useParams } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProfileProvider } from "@/contexts/ProfileContext";
import { SSRDataProvider } from "@/contexts/SSRDataContext";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Auth from "./pages/Auth";
import Grants from "./pages/Grants";
import Matching from "./pages/Matching";
import GrantDetail from "./pages/GrantDetail";
import Applications from "./pages/Applications";
import Generate from "./pages/Generate";
import ProfileSetup from "./pages/ProfileSetup";
import NotFound from "./pages/NotFound";
import { queryClient } from "./query-client";
import type { SSRData } from "@/contexts/SSRDataContext";

/**
 * App receives an optional `ssrData` prop that is populated by the SSR entry
 * (scripts/prerender.js) with pre-fetched page data. On the client, it is undefined
 * and the existing useEffect/useState flows handle data fetching.
 *
 * NOTE: HelmetProvider is NOT mounted here. It lives in entry-client.tsx and
 * entry-server.tsx so that the SSR pipeline can pass a shared context object
 * to it for head extraction.
 */
const App = ({ ssrData }: { ssrData?: SSRData } = {}) => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <ProfileProvider>
        <SSRDataProvider value={ssrData ?? {}}>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <Layout>
              <Routes>
                {/* Public routes */}
                <Route path="/" element={<Home />} />
                <Route path="/auth" element={<Auth />} />
                <Route path="/grants" element={<Grants />} />
                <Route path="/grants/:id" element={<GrantDetail />} />
                <Route path="/matching" element={<Matching />} />
                <Route
                  path="/matching/generate/:id"
                  element={
                    <ProtectedRoute>
                      <Matching generateMode={true} matchId={parseInt(useParams().id || '0')} />
                    </ProtectedRoute>
                  }
                />

                {/* Protected routes - require login */}
                <Route path="/applications" element={
                  <ProtectedRoute>
                    <Applications />
                  </ProtectedRoute>
                } />
                <Route path="/generate" element={
                  <ProtectedRoute>
                    <Generate />
                  </ProtectedRoute>
                } />
                <Route path="/generate/:id" element={
                  <ProtectedRoute>
                    <Generate />
                  </ProtectedRoute>
                } />
                <Route path="/profile-setup" element={
                  <ProtectedRoute>
                    <ProfileSetup />
                  </ProtectedRoute>
                } />
                <Route path="/family-setup" element={
                  <ProtectedRoute>
                    <ProfileSetup />
                  </ProtectedRoute>
                } />

                <Route path="*" element={<NotFound />} />
              </Routes>
            </Layout>
          </TooltipProvider>
        </SSRDataProvider>
      </ProfileProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
