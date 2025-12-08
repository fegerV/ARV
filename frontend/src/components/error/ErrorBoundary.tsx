import React, { Component, ReactNode } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Container,
  Alert,
  Stack,
} from '@mui/material';
import { ErrorOutline as ErrorIcon, Home as HomeIcon } from '@mui/icons-material';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

/**
 * Global Error Boundary для отлавливания React ошибок
 * Отображает fallback UI вместо белого экрана смерти
 */
export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    // Логирование ошибки
    console.error('Error Boundary caught:', error, errorInfo);

    // Callback для внешних сервисов логирования (Sentry и т.д.)
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <Container maxWidth="md">
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '100vh',
              }}
            >
              <Paper elevation={3} sx={{ p: 4, textAlign: 'center', maxWidth: 500 }}>
                <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center' }}>
                  <ErrorIcon sx={{ fontSize: 80, color: 'error.main' }} />
                </Box>

                <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
                  Something went wrong
                </Typography>

                <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
                  We encountered an unexpected error. Please try to refresh the page or go back home.
                </Typography>

                {process.env.NODE_ENV === 'development' && this.state.error && (
                  <Alert severity="error" sx={{ mb: 3, textAlign: 'left' }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                      Error Details:
                    </Typography>
                    <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {this.state.error.toString()}
                    </Typography>
                    {this.state.errorInfo && (
                      <Typography variant="body2" component="pre" sx={{ mt: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {this.state.errorInfo.componentStack}
                      </Typography>
                    )}
                  </Alert>
                )}

                <Stack direction="row" spacing={2} justifyContent="center">
                  <Button
                    variant="contained"
                    onClick={this.handleReset}
                  >
                    Try Again
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<HomeIcon />}
                    onClick={this.handleHome}
                  >
                    Go Home
                  </Button>
                </Stack>
              </Paper>
            </Box>
          </Container>
        )
      );
    }

    return this.props.children;
  }
}
