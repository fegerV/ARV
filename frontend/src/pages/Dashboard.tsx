/**
 * Dashboard - Обзор системы с метриками
 * Обновлено: использует новую структуру компонентов
 */

import { Grid, Box as MuiBox, Typography, Paper } from '@mui/material';
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

const statsCards = [
  {
    title: 'Всего просмотров',
    value: '45,892',
    trend: { value: 12.5, direction: 'up' as const },
    icon: <Eye size={24} />,
  },
  {
    title: 'Уникальных сессий',
    value: '38,234',
    trend: { value: 8.2, direction: 'up' as const },
    icon: <Users size={24} />,
  },
  {
    title: 'Активного контента',
    value: '280',
    subtitle: '+15 за месяц',
    icon: <Package size={24} />,
  },
  {
    title: 'Использовано',
    value: '125GB',
    subtitle: '10% от лимита',
    icon: <HardDrive size={24} />,
  },
  {
    title: 'Компаний',
    value: '15',
    trend: { value: 2, direction: 'up' as const },
    icon: <Building2 size={24} />,
  },
  {
    title: 'Проектов',
    value: '100',
    subtitle: '+12 активных',
    icon: <FolderOpen size={24} />,
  },
  {
    title: 'Доход',
    value: '$4,200',
    trend: { value: 15, direction: 'up' as const },
    icon: <DollarSign size={24} />,
  },
  {
    title: 'Uptime',
    value: '99.92%',
    subtitle: '✅ Все сервисы работают',
    icon: <CheckCircle size={24} />,
  },
];

export default function Dashboard() {
  return (
    <PageContent>
      <PageHeader
        title="Dashboard"
        subtitle="Обзор системы Vertex AR"
      />

      <Grid container spacing={3}>
        {statsCards.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <KpiCard
              title={stat.title}
              value={stat.value}
              icon={stat.icon}
              trend={stat.trend}
              subtitle={stat.subtitle}
            />
          </Grid>
        ))}
      </Grid>

      <MuiBox sx={{ mt: 4 }}>
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Недавняя активность
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Activity feed будет здесь...
          </Typography>
        </Paper>
      </MuiBox>
    </PageContent>
  );
}
