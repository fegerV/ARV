import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { CircularProgress, Box } from '@mui/material';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore();
  
  console.log('ProtectedRoute check, isAuthenticated:', isAuthenticated);

  if (!isAuthenticated) {
    console.log('ProtectedRoute: redirecting to /login');
    return <Navigate to="/login" replace />;
  }

  console.log('ProtectedRoute: rendering children');
  return <>{children}</>;
}