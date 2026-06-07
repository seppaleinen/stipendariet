import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ToastProvider } from "@/components/ui/toaster";
import { AuthProvider, useAuth } from '@/hooks/useAuth';
import ProtectedRoute from '@/components/ProtectedRoute';
import AdminLayout from '@/components/AdminLayout';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import QueuePage from '@/pages/QueuePage';
import ReviewPage from '@/pages/ReviewPage';
import JobsPage from '@/pages/JobsPage';
import EnrichmentResultsPage from '@/pages/EnrichmentResultsPage';

const App: React.FC = () => {
  return (
    <ToastProvider>
      <AuthProvider>
        <div className="App">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <DashboardPage />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/queue"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <QueuePage />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/jobs"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <JobsPage />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/review/:id"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <ReviewPage />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/enrichment-results"
              element={
                <ProtectedRoute>
                  <AdminLayout>
                    <EnrichmentResultsPage />
                  </AdminLayout>
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </AuthProvider>
    </ToastProvider>
  );
};

export default App;