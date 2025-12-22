import { useState, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  TextField, 
  Button, 
  Alert, 
  CircularProgress,
  useTheme,
  Container,
  Divider,
  Chip,
  InputAdornment,
  IconButton,
  Link as MuiLink,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { 
  Login as LoginIcon,
  Visibility,
  VisibilityOff,
  Email as EmailIcon,
  Lock as LockIcon,
  Security as SecurityIcon,
  Help as HelpIcon,
} from '@mui/icons-material';
import { useThemeStore } from '../store/themeStore';
import { useAuthStore } from '../store/authStore';
import ThemeToggle from '../components/common/ThemeToggle';
import { useToast } from '../store/useToast';
import api from '../services/api';
import { format } from 'date-fns';
// Removed unused import - ru locale not needed

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  last_login_at?: string;
}

interface LoginResponse {
  access_token: string;
  user: User;
}

interface LoginError {
  detail: string;
  locked_until?: string;
  attempts_left?: number;
}

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [lockedUntil, setLockedUntil] = useState<Date | null>(null);
  const [attemptsLeft, setAttemptsLeft] = useState<number | null>(null);
  
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuthStore();
  const { addToast: showToast } = useToast();
  const theme = useTheme();

  // Redirect if already authenticated AND on login page
  useEffect(() => {
    if (isAuthenticated) {
      // Only redirect if we're actually on the login page
      if (window.location.pathname === '/login') {
        navigate('/', { replace: true });
      }
    }
  }, [isAuthenticated, navigate]);

  // Countdown timer for locked account
  useEffect(() => {
    if (!lockedUntil) return;

    const interval = setInterval(() => {
      const now = new Date();
      if (now >= lockedUntil) {
        setLockedUntil(null);
        setError('');
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [lockedUntil]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !password) {
      setError('Заполните все поля');
      return;
    }

    setLoading(true);
    setError('');
    setAttemptsLeft(null);

    try {
      // FormData для OAuth2PasswordRequestForm
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post<LoginResponse>('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      
      login(response.data);
      showToast('Успешный вход в систему', 'success');
      
      // Navigate handled by useEffect
    } catch (err: any) {
      const errorData = err.response?.data as LoginError;
      
      if (errorData?.locked_until) {
        const lockTime = new Date(errorData.locked_until);
        setLockedUntil(lockTime);
        setError(`Аккаунт временно заблокирован до ${format(lockTime, 'HH:mm:ss')}`);
      } else if (errorData?.attempts_left !== undefined) {
        setAttemptsLeft(errorData.attempts_left);
        setError(errorData.detail || 'Неверный email или пароль');
      } else {
        setError(errorData?.detail || 'Ошибка авторизации');
      }
      
      showToast(errorData?.detail || 'Ошибка авторизации', 'error');
    } finally {
      setLoading(false);
    }
  };

  const getRemainingTime = (): string => {
    if (!lockedUntil) return '';
    
    const now = new Date();
    const diff = Math.max(0, Math.floor((lockedUntil.getTime() - now.getTime()) / 1000));
    
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  if (isAuthenticated) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <Container
      maxWidth="sm"
      sx={{
        py: 8,
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: theme.palette.mode === 'dark'
          ? `radial-gradient(circle at top right, ${theme.palette.primary.dark}, ${theme.palette.background.default})`
          : `radial-gradient(circle at top right, ${theme.palette.primary.light}, ${theme.palette.grey[100]})`,
      }}
    >
      <Paper
        elevation={16}
        sx={{
          p: 6,
          width: '100%',
          maxWidth: '450px',
          borderRadius: 3,
          position: 'relative',
          overflow: 'visible',
          [theme.breakpoints.down('sm')]: {
            p: 4,
            mx: 2
          },
          boxShadow: theme.palette.mode === 'dark'
            ? '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
            : '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
          transition: 'all 0.3s ease-in-out',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: theme.palette.mode === 'dark'
              ? '0 35px 60px -15px rgba(0, 0, 0, 0.6)'
              : '0 35px 60px -15px rgba(0, 0, 0, 0.2)',
          }
        }}
      >
        {/* Logo & Title */}
        <Box sx={{ textAlign: 'center', mb: 4, position: 'relative', zIndex: 1 }}>
          <Box sx={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 96,
            height: 96,
            borderRadius: '50%',
            background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.light})`,
            mb: 3,
            boxShadow: theme.shadows[8],
          }}>
            <LoginIcon sx={{ fontSize: 48, color: 'white' }} />
          </Box>
          <Typography variant="h4" component="h1" gutterBottom fontWeight={700} color="text.primary">
            Vertex AR
          </Typography>
          <Typography variant="h6" color="text.secondary" fontWeight={500}>
            Админ-панель
          </Typography>
        </Box>

        {/* Error Alert */}
        {error && (
          <Alert
            severity={lockedUntil ? 'warning' : 'error'}
            sx={{
              mb: 3,
              borderRadius: 2,
              border: '1px solid',
              borderColor: lockedUntil
                ? theme.palette.warning.light + '80'
                : theme.palette.error.light + '80',
            }}
            icon={lockedUntil ? <SecurityIcon /> : undefined}
          >
            {error}
            {lockedUntil && (
              <Typography variant="body2" sx={{ mt: 1, fontWeight: 600 }}>
                ⏳ Разблокировка через: <strong>{getRemainingTime()}</strong>
              </Typography>
            )}
          </Alert>
        )}

        {/* Attempts Left Warning */}
        {attemptsLeft !== null && attemptsLeft <= 2 && (
          <Alert
            severity="warning"
            sx={{
              mb: 3,
              borderRadius: 2,
              border: '1px solid',
              borderColor: theme.palette.warning.light + '80',
            }}
          >
            ⚠️ Осталось попыток: <strong>{attemptsLeft}</strong> из 5
          </Alert>
        )}

        {/* Login Form */}
        <Box component="form" onSubmit={handleSubmit} sx={{ mb: 4 }}>
          <TextField
            fullWidth
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            autoFocus
            placeholder="admin@vertexar.com"
            sx={{
              mb: 3,
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
                backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                transition: 'all 0.3s ease',
                '&:hover': {
                  backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,0.08)' : 'rgba(0,0,0,0.05)',
                  boxShadow: `0 0 0 1px ${theme.palette.primary.main}`,
                },
                '&.Mui-focused': {
                  backgroundColor: 'transparent',
                  boxShadow: `0 0 2px ${theme.palette.primary.main}`,
                },
                '& fieldset': {
                  borderColor: theme.palette.mode === 'dark' ? 'rgba(255,0.23)' : 'rgba(0,0,0,0.23)',
                },
                '&:hover fieldset': {
                  borderColor: theme.palette.primary.main,
                },
                '&.Mui-focused fieldset': {
                  borderColor: theme.palette.primary.main,
                },
              }
            }}
            disabled={loading || !!lockedUntil}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <EmailIcon
                    sx={{
                      color: theme.palette.text.secondary,
                      ml: 0.5,
                    }}
                  />
                </InputAdornment>
              ),
            }}
          />
          
          <TextField
            fullWidth
            label="Пароль"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            placeholder="••••••••••••"
            sx={{ mb: 3 }}
            disabled={loading || !!lockedUntil}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <LockIcon color="action" />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowPassword(!showPassword)}
                    edge="end"
                    disabled={loading || !!lockedUntil}
                  >
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          
          <Button
            type="submit"
            fullWidth
            variant="contained"
            size="large"
            disabled={loading || !email || !password || !!lockedUntil}
            sx={{
              py: 1.5,
              borderRadius: 2,
              fontSize: '1.1rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              boxShadow: theme.palette.mode === 'dark'
                ? `0 4px 20px ${theme.palette.primary.dark}`
                : `0 4px 20px ${theme.palette.primary.light}`,
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: theme.palette.mode === 'dark'
                  ? `0 6px 25px ${theme.palette.primary.dark}`
                  : `0 6px 25px ${theme.palette.primary.light}`,
              },
              '&:active': {
                transform: 'translateY(0)',
              },
              '&.Mui-disabled': {
                opacity: 0.6,
                transform: 'none',
                boxShadow: 'none',
              }
            }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : 'ВОЙТИ'}
          </Button>
        </Box>

        {/* 2FA Notice */}
        <Divider sx={{ my: 3 }}>
          <Chip 
            icon={<SecurityIcon />}
            label="Двухфакторная аутентификация (в разработке)" 
            size="small" 
            variant="outlined"
          />
        </Divider>

        {/* Security Info */}
        <Alert severity="info" icon={<SecurityIcon />} sx={{ mt: 3 }}>
          <Typography variant="body2" fontWeight={600}>
            🔒 Защита от брутфорса активна
          </Typography>
          <Typography variant="caption" display="block">
            • Максимум 5 попыток входа за 15 минут
          </Typography>
          <Typography variant="caption" display="block">
            • Автоматическая блокировка при превышении лимита
          </Typography>
        </Alert>

        {/* Theme & Help */}
        <Box sx={{ 
          mt: 4, 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 2,
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Тема:
            </Typography>
            <ThemeToggle />
          </Box>
          
          <Button 
            variant="text" 
            size="small" 
            startIcon={<HelpIcon />}
            href="https://docs.vertexar.com/admin"
            target="_blank"
            sx={{ textTransform: 'none' }}
          >
            Помощь
          </Button>
        </Box>

        {/* Footer */}
        <Box sx={{ mt: 4, pt: 3, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary" align="center" display="block">
            © 2025 Vertex AR. Все права защищены.
          </Typography>
          <Typography variant="caption" color="text.secondary" align="center" display="block" sx={{ mt: 0.5 }}>
            <MuiLink href="/privacy" underline="hover" color="inherit">
              Политика конфиденциальности
            </MuiLink>
            {' • '}
            <MuiLink href="/terms" underline="hover" color="inherit">
              Условия использования
            </MuiLink>
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}

