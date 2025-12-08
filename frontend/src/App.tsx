import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import ErrorBoundary from './components/error/ErrorBoundary';
import Sidebar from './components/layout/Sidebar';
import ToastNotification from './components/common/ToastNotification';
import ProtectedRoute from './components/auth/ProtectedRoute';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CompaniesList from './pages/companies/CompaniesList';
import CompanyDetails from './pages/companies/CompanyDetails';
import CompanyFormWizard from './pages/companies/CompanyFormWizard';
import ProjectsList from './pages/projects/ProjectsList';
import ProjectFormWizard from './pages/projects/ProjectFormWizard';
import ARContentList from './pages/ar-content/ARContentList';
import ARContentForm from './pages/ar-content/ARContentForm';
import ARContentDetails from './pages/ar-content/ARContentDetails';
import Analytics from './pages/Analytics';
import Storage from './pages/Storage';
import Notifications from './pages/Notifications';
import Settings from './pages/Settings';

function App() {
  // Initialize keyboard shortcuts (Ctrl+T, Ctrl+B for theme toggle)
  useKeyboardShortcuts();

  return (
    <>
      <ToastNotification />
      <ErrorBoundary>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          
          {/* Protected Routes */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
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
                    <Routes>
                    <Route path="/" element={<Dashboard />} />
                    
                    {/* Companies */}
                    <Route path="/companies" element={<CompaniesList />} />
                    <Route path="/companies/new" element={<CompanyFormWizard />} />
                    <Route path="/companies/:id" element={<CompanyDetails />} />
                    <Route path="/companies/:id/edit" element={<CompanyFormWizard />} />
                    
                    {/* Projects */}
                    <Route path="/companies/:companyId/projects" element={<ProjectsList />} />
                    <Route path="/companies/:companyId/projects/new" element={<ProjectFormWizard />} />
                    
                    {/* AR Content */}
                    <Route path="/ar-content" element={<ARContentList />} />
                    <Route path="/ar-content/new" element={<ARContentForm />} />
                    <Route path="/ar-content/:id" element={<ARContentDetails />} />
                    
                    {/* Other pages */}
                    <Route path="/analytics" element={<Analytics />} />
                    <Route path="/storage" element={<Storage />} />
                    <Route path="/notifications" element={<Notifications />} />
                    <Route path="/settings" element={<Settings />} />
                    
                    {/* Redirect unknown routes */}
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Box>
              </Box>
            </ProtectedRoute>
          }
        />
      </Routes>
      </ErrorBoundary>
    </>
  );
}

export default App;
