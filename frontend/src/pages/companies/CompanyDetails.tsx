// src/pages/Companies/CompanyDetails.tsx
import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Chip,
  Button,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import { PageHeader } from '@/components/(layout)/PageHeader';
import { AppLayout } from '@/components/(layout)/AppLayout';
import { companiesApi } from '@/services/companies';
import { ErrorState } from '@/components/(system)/ErrorState';
import { StatsGrid } from '@/components/(data)/StatsGrid';

const CompanyDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data, isLoading, isError, refetch } = useQuery(
    ['company', id],
    () => companiesApi.get(Number(id)),
    { enabled: !!id }
  );

  const company = data?.data;

  if (isLoading) {
    return (
      <AppLayout>
        <Container maxWidth="lg" sx={{ py: 3 }}>
          <PageHeader title="Загрузка компании..." backUrl="/companies" />
          <LinearProgress />
        </Container>
      </AppLayout>
    );
  }

  if (isError || !company) {
    return (
      <AppLayout>
        <Container maxWidth="lg" sx={{ py: 3 }}>
          <PageHeader title="Компания" backUrl="/companies" />
          <ErrorState message="Компания не найдена" onRetry={() => refetch()} />
        </Container>
      </AppLayout>
    );
  }

  const storageUsedPerc =
    company.storage_quota_gb > 0
      ? (company.storage_used_gb / company.storage_quota_gb) * 100
      : 0;

  return (
    <AppLayout>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <PageHeader
          title={company.name}
          subtitle={`ID: ${company.id} • ${company.slug}`}
          backUrl="/companies"
          actions={[
            {
              label: 'Новый проект',
              variant: 'outlined',
              onClick: () => navigate(`/projects/new?company_id=${company.id}`),
            },
            {
              label: 'Редактировать',
              variant: 'contained',
              onClick: () => navigate(`/companies/${company.id}/edit`),
            },
          ]}
        />

        <Grid container spacing={3}>
          {/* Левая колонка: реквизиты + хранилище */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Общая информация
              </Typography>
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  Слаг
                </Typography>
                <Typography variant="body1">{company.slug}</Typography>
              </Box>
              {company.contact_email && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Email
                  </Typography>
                  <Typography variant="body1">{company.contact_email}</Typography>
                </Box>
              )}
              {company.contact_phone && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Телефон
                  </Typography>
                  <Typography variant="body1">{company.contact_phone}</Typography>
                </Box>
              )}
              <Box sx={{ mt: 1 }}>
                <Chip
                  label={company.is_active ? 'Активна' : 'Неактивна'}
                  color={company.is_active ? 'success' : 'default'}
                  size="small"
                  sx={{ mr: 1 }}
                />
                {company.is_default && (
                  <Chip
                    label="Компания по умолчанию"
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                )}
              </Box>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Хранилище
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Провайдер: {company.storage_provider_human}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Путь: {company.storage_path}
              </Typography>

              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Использовано {company.storage_used_gb.toFixed(2)} ГБ из{' '}
                  {company.storage_quota_gb} ГБ
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(storageUsedPerc, 100)}
                  sx={{ mt: 1, height: 8, borderRadius: 4 }}
                  color={
                    storageUsedPerc > 90 ? 'error' : storageUsedPerc > 70 ? 'warning' : 'primary'
                  }
                />
              </Box>

              <Button
                size="small"
                sx={{ mt: 2 }}
                onClick={() => navigate(`/settings/storage?company_id=${company.id}`)}
              >
                Настроить подключение
              </Button>
            </Paper>
          </Grid>

          {/* Правая колонка: KPI + проекты/заказы */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                KPI компании
              </Typography>
              <StatsGrid
                items={[
                  {
                    label: 'Всего AR‑заказов',
                    value: company.stats?.ar_contents_count ?? 0,
                  },
                  {
                    label: 'Всего просмотров',
                    value: (company.stats?.views_30d ?? 0).toLocaleString(),
                  },
                  {
                    label: 'Уникальные сессии (30д)',
                    value: company.stats?.unique_sessions_30d ?? 0,
                  },
                  {
                    label: 'Средняя длит. сессии',
                    value: `${company.stats?.avg_duration_30d ?? 0}s`,
                  },
                ]}
              />
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Активные проекты
              </Typography>
              {company.projects?.length ? (
                <List dense>
                  {company.projects.map((p: any) => (
                    <ListItem
                      key={p.id}
                      button
                      onClick={() => navigate(`/projects/${p.id}/content`)}
                    >
                      <ListItemText
                        primary={p.name}
                        secondary={`Заказов: ${p.ar_contents_count} • Статус: ${p.status_human}`}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Нет активных проектов
                </Typography>
              )}
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </AppLayout>
  );
};

export default CompanyDetailsPage;
