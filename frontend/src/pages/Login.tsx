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
import { ru } from 'date-fns/locale';

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
    last_login_at?: string;
  };
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
  const { showToast } = useToast();
  const theme = useTheme();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
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
        setError(`Аккаунт временно заблокирован до ${format(lockTime, 'HH:mm:ss', { locale: ru })}`);
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
          ? 'linear-gradient(135deg, #1e1e1e 0%, #121212 100%)'
          : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Paper 
        elevation={24} 
        sx={{ 
          p: 6, 
          width: '100%',
          borderRadius: 4,
          position: 'relative',
          overflow: 'hidden',
          [theme.breakpoints.down('sm')]: { 
            p: 4, 
            px: 3 
          },
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '4px',
            background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
          }
        }}
      >
        {/* Logo & Title */}
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <LoginIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
          <Typography variant="h3" component="h1" gutterBottom fontWeight={700}>
            Vertex AR
          </Typography>
          <Typography variant="h5" color="text.secondary">
            Админ-панель
          </Typography>
        </Box>

        {/* Error Alert */}
        {error && (
          <Alert 
            severity={lockedUntil ? 'warning' : 'error'} 
            sx={{ mb: 3 }}
            icon={lockedUntil ? <SecurityIcon /> : undefined}
          >
            {error}
            {lockedUntil && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                ⏳ Разблокировка через: <strong>{getRemainingTime()}</strong>
              </Typography>
            )}
          </Alert>
        )}

        {/* Attempts Left Warning */}
        {attemptsLeft !== null && attemptsLeft <= 2 && (
          <Alert severity="warning" sx={{ mb: 3 }}>
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
            sx={{ mb: 3 }}
            disabled={loading || !!lockedUntil}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <EmailIcon color="action" />
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
