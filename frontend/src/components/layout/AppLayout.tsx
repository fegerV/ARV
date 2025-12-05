import { ReactNode } from 'react';
import { Box } from '@mui/material';
import Sidebar from '../layout/Sidebar';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  useKeyboardShortcuts();

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <Box 
        component="main" 
        sx={{ 
          flexGrow: 1, 
          p: 3, 
          mt: 8,
          bgcolor: 'background.default',
          transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
