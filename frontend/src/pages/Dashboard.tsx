/**
 * Dashboard - Обзор системы с метриками
 * Обновлено: подключение к реальному API аналитики и активности
 */

import { Grid, Box as MuiBox, Typography, Paper, LinearProgress } from '@mui/material';
import { PageHeader, PageContent, KpiCard } from '@/components';
import {
  Eye,
  Users,
  Package,
  HardDrive,
  Building2,
  FolderOpen,
  DollarSign,
  CheckCircle,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/services/analytics';
import { activityApi } from '@/services/activity';

export default function Dashboard() {
  const {
    data: summaryData,
    isLoading: summaryLoading,
  } = useQuery(['analytics-summary'], () => analyticsApi.summary());

  const {
    data: activityData,
    isLoading: activityLoading,
  } = useQuery(['activity-feed', { limit: 10 }], () =>
    activityApi.list({ limit: 10 }),
  );

  const summary = summaryData?.data;
  const activity = activityData?.data?.items ?? [];

  const statsCards = [
    {
      title: 'Всего просмотров',
      value: summary ? summary.views_total.toLocaleString() : '—',
      trend: summary
        ? { value: summary.views_trend, direction: summary.views_trend >= 0 ? ('up' as const) : ('down' as const) }
        : undefined,
      icon: <Eye size={24} />,
    },
    {
      title: 'Уникальных сессий',
      value: summary ? summary.unique_sessions_total.toLocaleString() : '—',
      trend: summary
        ? {
            value: summary.unique_sessions_trend,
            direction: summary.unique_sessions_trend >= 0 ? ('up' as const) : ('down' as const),
          }
        : undefined,
      icon: <Users size={24} />,
    },
    {
      title: 'Активного контента',
      value: summary ? String(summary.active_contents) : '—',
      subtitle: summary ? `+${summary.new_contents_30d} за 30 дней` : undefined,
      icon: <Package size={24} />,
    },
    {
      title: 'Использовано',
      value: summary ? `${summary.storage_used_gb}GB` : '—',
      subtitle: summary ? `${summary.storage_used_percent}% от лимита` : undefined,
      icon: <HardDrive size={24} />,
    },
    {
      title: 'Компаний',
      value: summary ? String(summary.companies_count) : '—',
      trend: summary
        ? {
            value: summary.companies_trend,
            direction: summary.companies_trend >= 0 ? ('up' as const) : ('down' as const),
          }
        : undefined,
      icon: <Building2 size={24} />,
    },
    {
      title: 'Проектов',
      value: summary ? String(summary.projects_count) : '—',
      subtitle: summary ? `+${summary.active_projects_delta} активных` : undefined,
      icon: <FolderOpen size={24} />,
    },
    {
      title: 'Доход',
      value: summary ? `$${summary.revenue_mrr.toLocaleString()}` : '—',
      trend: summary
        ? {
            value: summary.revenue_trend,
            direction: summary.revenue_trend >= 0 ? ('up' as const) : ('down' as const),
          }
        : undefined,
      icon: <DollarSign size={24} />,
    },
    {
      title: 'Uptime',
      value: summary ? `${summary.uptime_percent.toFixed(2)}%` : '—',
      subtitle: summary?.all_services_ok ? '✅ Все сервисы работают' : 'Есть предупреждения',
      icon: <CheckCircle size={24} />,
    },
  ];

  return (
    <PageContent>
      <PageHeader title="Dashboard" subtitle="Обзор системы Vertex AR" />

      {summaryLoading && <LinearProgress sx={{ mb: 2 }} />}

      <Grid container spacing={3}>
        {statsCards.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <KpiCard
              title={stat.title}
              value={stat.value}
              icon={stat.icon}
              trend={stat.trend}
              subtitle={stat.subtitle}
              loading={summaryLoading}
            />
          </Grid>
        ))}
      </Grid>

      <MuiBox sx={{ mt: 4 }}>
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Недавняя активность
          </Typography>

          {activityLoading && <LinearProgress sx={{ mb: 2 }} />}

          {activity.length === 0 && !activityLoading ? (
            <Typography variant="body2" color="textSecondary">
              Пока нет событий.
            </Typography>
          ) : (
            activity.map((item: any) => (
              <MuiBox
                key={item.id}
                sx={{
                  py: 1,
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                  '&:last-of-type': { borderBottom: 'none' },
                }}
              >
                <Typography variant="body2" fontWeight={500}>
                  {item.title}
                </Typography>
                {item.description && (
                  <Typography variant="body2" color="textSecondary">
                    {item.description}
                  </Typography>
                )}
                <Typography variant="caption" color="textSecondary">
                  {item.created_at_readable} • {item.scope_human}
                </Typography>
              </MuiBox>
            ))
          )}
        </Paper>
      </MuiBox>
    </PageContent>
  );
}
