import { useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Box } from '@mui/material';
import Sidebar from './components/layout/Sidebar';
import ToastNotification from './components/common/ToastNotification';
import ProtectedRoute from './components/auth/ProtectedRoute';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CompaniesList from './pages/companies/CompaniesList';
import CompanyDetails from './pages/companies/CompanyDetails';
import CompanyForm from './pages/companies/CompanyForm';
import ProjectsList from './pages/projects/ProjectsList';
import ProjectForm from './pages/projects/ProjectForm';
import ARContentList from './pages/ar-content/ARContentList';
import ARContentForm from './pages/ar-content/ARContentForm';
import ARContentDetail from './pages/ar-content/ARContentDetail';
import Analytics from './pages/Analytics';
import Storage from './pages/Storage';
import Notifications from './pages/Notifications';
import Settings from './pages/Settings';
import YandexDiskCallback from './pages/oauth/YandexDiskCallback';

// Layout component for protected routes
const ProtectedLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <Box sx={{ display: 'flex', width: '100%' }}>
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          mt: 8,
          ml: { xs: 0, sm: 30 }, // 30 = drawerWidth / 8 (240px / 8 = 30)
          width: { xs: '100%', sm: 'calc(100% - 240px)' },
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

function App() {
  // Initialize keyboard shortcuts (Ctrl+T, Ctrl+B for theme toggle)
  useKeyboardShortcuts();
  
  const location = useLocation();
  const navigate = useNavigate();
  
  console.log('App component rendered, current location:', location.pathname);

  // Track location changes
  useEffect(() => {
    console.log('Location changed to:', location.pathname);
  }, [location]);

  return (
    <>
      <ToastNotification />
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        
        {/* OAuth Callback Routes (public - accessed from popup) */}
        <Route path="/oauth/yandex/callback" element={<YandexDiskCallback />} />
        
        {/* Protected Routes - Specific routes first */}
        <Route path="/companies" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <CompaniesList />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/companies/new" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <CompanyForm />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/companies/:id" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <CompanyDetails />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/projects" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ProjectsList />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/companies/:companyId/projects" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ProjectsList />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/companies/:companyId/projects/new" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ProjectForm />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/ar-content" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ARContentList />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/ar-content/new" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ARContentForm />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/projects/:projectId/content" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ARContentList />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/projects/:projectId/content/new" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ARContentForm />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/ar-content/:arContentId" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ARContentDetail />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/analytics" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <Analytics />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/storage" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <Storage />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/notifications" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <Notifications />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        <Route path="/settings" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <Settings />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        {/* Protected Routes - Dashboard (index route) last */}
        <Route path="/" element={
          <ProtectedRoute>
            <ProtectedLayout>
              <Dashboard />
            </ProtectedLayout>
          </ProtectedRoute>
        } />
        
        {/* Redirect unknown routes to dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default App;