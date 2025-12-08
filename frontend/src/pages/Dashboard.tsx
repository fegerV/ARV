/**
 * Dashboard - Обзор системы с метриками
 * Подключено: реальные данные из API + Recharts
 */

import { useState, useEffect } from 'react';
import {
  Grid,
  Box as MuiBox,
  Typography,
  Paper,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { PageHeader, PageContent, KpiCard } from '@/components';
import { DashboardSkeleton } from '@/components/skeletons';
import { analyticsAPI } from '@/services/api';
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

// Цвета для диаграмм
const COLORS = ['#1976d2', '#2e7d32', '#ed6c02', '#d32f2f', '#7b1fa2', '#1976d2'];

interface DashboardData {
  total_views: number;
  unique_sessions: number;
  active_content: number;
  storage_used_gb: number;
  storage_limit_gb: number;
  active_companies: number;
  active_projects: number;
  monthly_views_trend: { date: string; views: number }[];
  views_by_company: { name: string; views: number }[];
  device_breakdown: { name: string; value: number }[];
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const response = await analyticsAPI.overview();
        setData(response.data);
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Ошибка загрузки данных');
        console.error('Failed to fetch dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
    // Обновляем каждые 5 минут
    const interval = setInterval(fetchAnalytics, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <PageContent>
        <PageHeader title="Dashboard" subtitle="Обзор системы Vertex AR" />
        <DashboardSkeleton />
      </PageContent>
    );
  }

  if (error || !data) {
    return (
      <PageContent>
        <PageHeader title="Dashboard" subtitle="Обзор системы Vertex AR" />
        <Alert severity="error">Ошибка загрузки данных: {error}</Alert>
      </PageContent>
    );
  }

  // Форматирование чисел
  const formatNumber = (num: number) => new Intl.NumberFormat('ru-RU').format(num);
  const formatStorage = (gb: number | null) => {
    if (gb === null || gb === undefined) return '0 GB';
    return `${gb.toFixed(1)} GB`;
  };
  const formatPercent = (used: number | null, total: number | null) => {
    if (used === null || total === null || total === 0) return '0';
    return ((used / total) * 100).toFixed(1);
  };

  // KPI cards
  const kpiCards = [
    {
      title: 'Всего просмотров',
      value: formatNumber(data?.total_views || 0),
      icon: <Eye size={24} />,
    },
    {
      title: 'Уникальных сессий',
      value: formatNumber(data?.unique_sessions || 0),
      icon: <Users size={24} />,
    },
    {
      title: 'Активного контента',
      value: formatNumber(data?.active_content || 0),
      subtitle: 'элементов',
      icon: <Package size={24} />,
    },
    {
      title: 'Использовано',
      value: formatStorage(data?.storage_used_gb || 0),
      subtitle: `${formatPercent(data?.storage_used_gb || 0, data?.storage_limit_gb || 1)}% от лимита`,
      icon: <HardDrive size={24} />,
    },
    {
      title: 'Компаний',
      value: formatNumber(data?.active_companies || 0),
      icon: <Building2 size={24} />,
    },
    {
      title: 'Проектов',
      value: formatNumber(data?.active_projects || 0),
      icon: <FolderOpen size={24} />,
    },
  ];

  return (
    <PageContent>
      <PageHeader
        title="Dashboard"
        subtitle="Обзор системы Vertex AR"
      />

      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {kpiCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={index}>
            <KpiCard
              title={card.title}
              value={card.value}
              icon={card.icon}
              subtitle={card.subtitle}
            />
          </Grid>
        ))}
      </Grid>

      {/* Charts Grid */}
      <Grid container spacing={3}>
        {/* Views Over Time - Line Chart */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Просмотры за месяц
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data?.monthly_views_trend || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="views"
                  stroke="#1976d2"
                  isAnimationActive={true}
                />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Views by Company - Bar Chart */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Просмотры по компаниям
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data?.views_by_company || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="views" fill="#2e7d32" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Device Breakdown - Pie Chart */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Распределение по устройствам
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={data?.device_breakdown || []}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {(data?.device_breakdown || []).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Storage Usage Summary */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Емкость хранилища
            </Typography>
            <MuiBox sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="body2">Использовано</Typography>
              <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                {formatStorage(data?.storage_used_gb)} / {formatStorage(data?.storage_limit_gb)}
              </Typography>
            </MuiBox>
            <MuiBox
              sx={{
                width: '100%',
                height: 8,
                backgroundColor: '#e0e0e0',
                borderRadius: 4,
                overflow: 'hidden',
              }}
            >
              <MuiBox
                sx={{
                  height: '100%',
                  width: `${formatPercent(data?.storage_used_gb, data?.storage_limit_gb)}%`,
                  backgroundColor: '#1976d2',
                  transition: 'width 0.3s ease',
                }}
              />
            </MuiBox>
            <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
              {formatPercent(data?.storage_used_gb, data?.storage_limit_gb)}% заполнено
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </PageContent>
  );
}
