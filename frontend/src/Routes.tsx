// Routes.tsx
import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { AppLayout } from '@/components/(layout)/AppLayout';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Dashboard from '@/pages/Dashboard';
import Companies from '@/pages/companies/Companies';
import Projects from '@/pages/projects/Projects';
import ARContentDetailPage from '@/pages/ar-content/ARContentDetailPage';
import Login from '@/pages/Login';
import AnalyticsDashboard from '@/pages/Analytics/AnalyticsDashboard';
import RealTimeDashboard from '@/pages/Analytics/RealTimeDashboard';

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/companies" element={<Companies />} />
                <Route path="/projects" element={<Projects />} />
                <Route path="/ar-content/:id" element={<ARContentDetailPage />} />
                <Route path="/analytics" element={<AnalyticsDashboard />} />
                <Route path="/analytics/real-time" element={<RealTimeDashboard />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

export default AppRoutes;