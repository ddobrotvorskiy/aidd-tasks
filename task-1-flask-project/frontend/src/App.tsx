import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider } from './contexts/AuthContext';
import EmployeeDetailPage from './pages/EmployeeDetailPage';
import EmployeeListPage from './pages/EmployeeListPage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import RegisterPage from './pages/RegisterPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

const App: React.FC = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/employees" element={<EmployeeListPage />} />
            <Route path="/employees/:id" element={<EmployeeDetailPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>

          {/* Default redirect */}
          <Route path="*" element={<Navigate to="/employees" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
