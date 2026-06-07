import { HelmetProvider } from "react-helmet-async";
import { Toaster, SonnerToaster as Sonner, TooltipProvider } from "@stipendariet/ui";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProfileProvider } from "@/contexts/ProfileContext";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Auth from "./pages/Auth";
import Grants from "./pages/Grants";
import Matching from "./pages/Matching";
import GrantDetail from "./pages/GrantDetail";
import Applications from "./pages/Applications";
import Generate from "./pages/Generate";
import FamilySetup from "./pages/FamilySetup";
import ProfileSetup from "./pages/ProfileSetup";
import NotFound from "./pages/NotFound";
import SEOHead from "./components/SEOHead";

const queryClient = new QueryClient();

const App = () => (
  <HelmetProvider>
    <SEOHead />
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ProfileProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <BrowserRouter>
              <Layout>
                <Routes>
                  {/* Public routes */}
                  <Route path="/" element={<Home />} />
                  <Route path="/auth" element={<Auth />} />
                  <Route path="/grants" element={<Grants />} />
                  <Route path="/matching" element={<Matching />} />
                  <Route path="/grants/:id" element={<GrantDetail />} />

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
            </BrowserRouter>
          </TooltipProvider>
        </ProfileProvider>
      </AuthProvider>
    </QueryClientProvider>
  </HelmetProvider>
);

export default App;
