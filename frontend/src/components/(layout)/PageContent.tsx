/**
 * PageContent - Контентная область страницы с отступами
 */

import { Box } from '@mui/material';
import { ReactNode } from 'react';

interface PageContentProps {
  children: ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | false;
}

export const PageContent = ({ children, maxWidth = 'xl' }: PageContentProps) => {
  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: maxWidth ? `${maxWidth}.breakpoint` : 'none',
        mx: 'auto',
        px: { xs: 2, sm: 3 },
        py: 3,
      }}
    >
      {children}
    </Box>
  );
};
