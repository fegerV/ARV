// ARV/frontend/src/pages/Settings.tsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Button,
  Divider,
} from '@mui/material';
import { AppLayout } from '@/components/(layout)/AppLayout';
import { PageHeader } from '@/components/(layout)/PageHeader';

const SettingsPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <AppLayout>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <PageHeader
          title="Настройки"
          subtitle="Управление аккаунтом, компаниями и хранилищами"
          backUrl="/"
        />

        <Grid container spacing={3}>
          {/* Аккаунт */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Аккаунт и доступ
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Профиль пользователя, пароль, роли и входы.
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/profile')}
                >
                  Профиль
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/users')}
                >
                  Пользователи и роли
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Компании и клиенты */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Компании и клиенты
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Управление компаниями, квотами и демо‑окружением.
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/companies')}
                >
                  Компании
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/companies/new')}
                >
                  Новая компания
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Хранилища */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Хранилища файлов
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Локальное хранилище, Яндекс Диск, MinIO/S3.
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/storage')}
                >
                  Подключения хранилищ
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Уведомления и почта */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Уведомления и email
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Центр уведомлений, email‑шаблоны и рассылки.
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/notifications')}
                >
                  Уведомления
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/settings/email-templates')}
                >
                  Шаблоны писем
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Аналитика / системные настройки */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Аналитика и система
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Глобальные параметры аналитики, ретеншна и логирования.
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/analytics')}
                >
                  Панель аналитики
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => navigate('/settings/system')}
                >
                  Системные параметры
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Разделитель / версия */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2, mt: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">
                  Vertex AR Admin • версия 0.1.0
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Build ID: DEV
                </Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </AppLayout>
  );
};

export default SettingsPage;
