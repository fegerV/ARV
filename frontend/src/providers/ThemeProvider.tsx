import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { useThemeStore } from '../store/themeStore';
import { useSystemTheme } from '../hooks/useSystemTheme';
import { useMemo, useEffect } from 'react';

const getDesignTokens = (mode: 'light' | 'dark') => ({
  palette: {
    mode,
    ...(mode === 'dark'
      ? {
          // Dark theme
          primary: {
            main: '#90caf9',
            light: '#a6d4fa',
            dark: '#5d99c6',
          },
          secondary: {
            main: '#ce93d8',
          },
          background: {
            default: '#121212',
            paper: '#1e1e1e',
          },
          text: {
            primary: '#ffffff',
            secondary: '#b0b0b0',
          },
          divider: 'rgba(255,255,255,0.12)',
          action: {
            hover: 'rgba(255,255,255,0.08)',
            selected: 'rgba(255,255,255,0.16)',
          },
        }
      : {
          // Light theme
          primary: {
            main: '#1976d2',
            light: '#42a5f5',
            dark: '#1565c0',
          },
          secondary: {
            main: '#9c27b0',
          },
          background: {
            default: '#f5f5f5',
            paper: '#ffffff',
          },
          text: {
            primary: '#000000',
            secondary: '#666666',
          },
          divider: 'rgba(0,0,0,0.12)',
          action: {
            hover: 'rgba(0,0,0,0.04)',
            selected: 'rgba(0,0,0,0.08)',
          },
        }),
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
    },
    h2: {
      fontWeight: 700,
    },
    h3: {
      fontWeight: 600,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
    h6: {
      fontWeight: 500,
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRadius: 0,
          transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        },
      },
    },
  },
});

export const VertexThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { mode } = useThemeStore();
  const systemTheme = useSystemTheme();

  const effectiveMode = mode === 'system' ? systemTheme : mode;
  
  const theme = useMemo(
    () => createTheme(getDesignTokens(effectiveMode)),
    [effectiveMode]
  );

  // Add class to document for TailwindCSS dark mode
  useEffect(() => {
    if (effectiveMode === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [effectiveMode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline enableColorScheme />
      {children}
    </ThemeProvider>
  );
};
