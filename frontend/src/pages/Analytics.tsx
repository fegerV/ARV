// ARV/frontend/src/pages/Analytics.tsx
import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  MenuItem,
  TextField,
  LinearProgress,
} from '@mui/material';
import { AppLayout } from '@/components/(layout)/AppLayout';
import { PageHeader } from '@/components/(layout)/PageHeader';
import { analyticsApi } from '@/services/analytics';
import { KpiCard } from '@/components/(analytics)/KpiCard';
import { LineChartViews } from '@/components/(analytics)/LineChartViews';
import { DevicePieChart } from '@/components/(analytics)/DevicePieChart';
import { TopContentTable } from '@/components/(analytics)/TopContentTable';
import { LiveSessionsWidget } from '@/components/(analytics)/LiveSessionsWidget';

const AnalyticsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const companyId = searchParams.get('company_id') || 'all';
  const range = searchParams.get('range') || '30d';

  const { data, isLoading } = useQuery(
    ['analytics', { companyId, range }],
    () => analyticsApi.dashboard({ company_id: companyId, range }),
  );

  const dashboard = data?.data;

  return (
    <AppLayout>
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <PageHeader
          title="Аналитика AR‑контента"
          subtitle="KPI, вовлечённость и устройства"
          backUrl="/"
        />

        {/* Фильтры */}
        <Box sx={{ mb: 3 }}>
          <Paper sx={{ p: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <TextField
              select
              size="small"
              label="Компания"
              value={companyId}
              onChange={(e) =>
                setSearchParams({
                  company_id: e.target.value,
                  range,
                })
              }
              sx={{ minWidth: 220 }}
            >
              <MenuItem value="all">Все компании</MenuItem>
              {/* сюда подставишь companies из кэша/отдельного hook */}
            </TextField>

            <TextField
              select
              size="small"
              label="Период"
              value={range}
              onChange={(e) =>
                setSearchParams({
                  company_id: companyId,
                  range: e.target.value,
                })
              }
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="7d">7 дней</MenuItem>
              <MenuItem value="30d">30 дней</MenuItem>
              <MenuItem value="90d">90 дней</MenuItem>
            </TextField>
          </Paper>
        </Box>

        {isLoading && <LinearProgress sx={{ mb: 2 }} />}

        {dashboard && (
          <Grid container spacing={3}>
            {/* KPI */}
            <Grid item xs={12}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <KpiCard
                    label="Просмотры"
                    value={dashboard.kpi.views}
                    trend={dashboard.kpi.views_trend}
                    helper="за выбранный период"
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <KpiCard
                    label="Уникальные сессии"
                    value={dashboard.kpi.unique_sessions}
                    trend={dashboard.kpi.unique_sessions_trend}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <KpiCard
                    label="Средняя длительность"
                    value={`${dashboard.kpi.avg_duration}s`}
                    trend={dashboard.kpi.avg_duration_trend}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <KpiCard
                    label="Marker detect rate"
                    value={`${dashboard.kpi.marker_detect_rate}%`}
                    trend={dashboard.kpi.marker_detect_rate_trend}
                  />
                </Grid>
              </Grid>
            </Grid>

            {/* Графики */}
            <Grid item xs={12} md={8}>
              <Paper sx={{ p: 2, height: '100%' }}>
                <Typography variant="h6" gutterBottom>
                  Динамика просмотров
                </Typography>
                <LineChartViews data={dashboard.timeseries.views} />
              </Paper>
            </Grid>

            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Устройства
                </Typography>
                <DevicePieChart data={dashboard.devices} />
              </Paper>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Сейчас онлайн
                </Typography>
                <LiveSessionsWidget />
              </Paper>
            </Grid>

            {/* Топ AR‑контента */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Топ AR‑портретов по вовлечённости
                </Typography>
                <TopContentTable rows={dashboard.top_contents} />
              </Paper>
            </Grid>
          </Grid>
        )}
      </Container>
    </AppLayout>
  );
};

export default AnalyticsPage;
