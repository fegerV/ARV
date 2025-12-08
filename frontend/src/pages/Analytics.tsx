import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Card,
  CardContent,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { PageHeader, PageContent, KpiCard } from '@/components';
import { analyticsAPI } from '@/services/api';
import { RefreshCw as RefreshIcon } from 'lucide-react';

const COLORS = ['#1976d2', '#2e7d32', '#ed6c02', '#d32f2f', '#7b1fa2'];

interface AnalyticsFilters {
  company_id?: string;
  project_id?: string;
  device_type?: string;
  period: '1d' | '7d' | '30d' | 'custom';
  start_date?: string;
  end_date?: string;
}

export default function Analytics() {
  const [filters, setFilters] = useState<AnalyticsFilters>({
    period: '7d',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mock data
  const overviewCards = [
    { title: 'Всего просмотров', value: '125,892', icon: '👁️' },
    { title: 'Уникальных сессий', value: '98,234', icon: '👤' },
    { title: 'Avg. длительность', value: '2m 34s', icon: '⏱️' },
    { title: 'Conversion Rate', value: '12.5%', icon: '📈' },
  ];

  const viewsTrendData = [
    { date: '2025-01-01', views: 1200, sessions: 800 },
    { date: '2025-01-02', views: 1900, sessions: 1200 },
    { date: '2025-01-03', views: 900, sessions: 600 },
    { date: '2025-01-04', views: 2200, sessions: 1400 },
    { date: '2025-01-05', views: 2290, sessions: 1500 },
    { date: '2025-01-06', views: 2000, sessions: 1300 },
    { date: '2025-01-07', views: 2181, sessions: 1400 },
  ];

  const viewsByCompanyData = [
    { name: 'ООО Артём', views: 25000 },
    { name: 'МегаПринт', views: 20000 },
    { name: 'СтудияХК', views: 15000 },
    { name: 'Other', views: 65000 },
  ];

  const deviceBreakdownData = [
    { name: 'iPhone', value: 35 },
    { name: 'Android', value: 45 },
    { name: 'Web', value: 15 },
    { name: 'Tablet', value: 5 },
  ];

  const topContentData = [
    { id: 1, title: 'Санта с подарками', views: 25892, sessions: 18234, duration: '3m 45s' },
    { id: 2, title: 'Ёлка на стенде', views: 18234, sessions: 12500, duration: '2m 30s' },
    { id: 3, title: 'Новогодние огни', views: 15000, sessions: 10000, duration: '2m 15s' },
    { id: 4, title: 'Морозные узоры', views: 12450, sessions: 8500, duration: '2m 00s' },
    { id: 5, title: 'Сказочный лес', views: 10234, sessions: 7200, duration: '3m 20s' },
  ];

  const sessionDurationData = [
    { duration: '0-1m', count: 5234 },
    { duration: '1-2m', count: 8934 },
    { duration: '2-3m', count: 12534 },
    { duration: '3-4m', count: 8234 },
    { duration: '4-5m', count: 3145 },
    { duration: '5m+', count: 1234 },
  ];

  const handleRefresh = async () => {
    setLoading(true);
    // TODO: Fetch actual data from API
    setTimeout(() => setLoading(false), 1000);
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <PageContent>
      <PageHeader
        title="Аналитика"
        subtitle="Детальный анализ просмотров и взаимодействия пользователей"
        actions={
          <Button
            variant="outlined"
            startIcon={<RefreshIcon size={20} />}
            onClick={handleRefresh}
            disabled={loading}
          >
            Обновить
          </Button>
        }
      />

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {/* Filters */}
      <Paper sx={{ p: 3, mb: 3, display: 'flex', gap: 2, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Период</InputLabel>
          <Select
            value={filters.period}
            label="Период"
            onChange={(e) => handleFilterChange('period', e.target.value)}
          >
            <MenuItem value="1d">Сегодня</MenuItem>
            <MenuItem value="7d">Последние 7 дней</MenuItem>
            <MenuItem value="30d">Последние 30 дней</MenuItem>
            <MenuItem value="custom">Пользовательский</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Компания</InputLabel>
          <Select
            value={filters.company_id || ''}
            label="Компания"
            onChange={(e) => handleFilterChange('company_id', e.target.value)}
          >
            <MenuItem value="">Все</MenuItem>
            <MenuItem value="1">ООО Артём</MenuItem>
            <MenuItem value="2">МегаПринт</MenuItem>
            <MenuItem value="3">СтудияХК</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Устройство</InputLabel>
          <Select
            value={filters.device_type || ''}
            label="Устройство"
            onChange={(e) => handleFilterChange('device_type', e.target.value)}
          >
            <MenuItem value="">Все</MenuItem>
            <MenuItem value="ios">iPhone/iOS</MenuItem>
            <MenuItem value="android">Android</MenuItem>
            <MenuItem value="web">Web</MenuItem>
          </Select>
        </FormControl>
      </Paper>

      {/* Overview Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {overviewCards.map((card, idx) => (
          <Grid item xs={12} sm={6} md={3} key={idx}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {card.icon} {card.title}
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                  {card.value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Charts Grid */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Views Trend */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Просмотры и сессии (тренд)
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={viewsTrendData}>
                <defs>
                  <linearGradient id="colorViews" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1976d2" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#1976d2" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="views"
                  stroke="#1976d2"
                  fillOpacity={1}
                  fill="url(#colorViews)"
                />
                <Area
                  type="monotone"
                  dataKey="sessions"
                  stroke="#2e7d32"
                  fillOpacity={0.3}
                  fill="#2e7d32"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Views by Company */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Просмотры по компаниям
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={viewsByCompanyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="views" fill="#1976d2" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Device Breakdown */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Распределение по устройствам
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={deviceBreakdownData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {deviceBreakdownData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Session Duration */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Распределение по длительности сессии
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sessionDurationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="duration" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#ed6c02" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Top Content Table */}
      <Paper elevation={2} sx={{ overflow: 'auto', mb: 3 }}>
        <Box sx={{ p: 3, borderBottom: '1px solid #e0e0e0' }}>
          <Typography variant="h6">Топ контент по просмотрам</Typography>
        </Box>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell>#</TableCell>
              <TableCell>Название контента</TableCell>
              <TableCell align="right">Просмотры</TableCell>
              <TableCell align="right">Сессии</TableCell>
              <TableCell align="right">Avg. длительность</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {topContentData.map((item, idx) => (
              <TableRow key={item.id} hover>
                <TableCell>{idx + 1}</TableCell>
                <TableCell>{item.title}</TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {item.views.toLocaleString('ru-RU')}
                  </Typography>
                </TableCell>
                <TableCell align="right">{item.sessions.toLocaleString('ru-RU')}</TableCell>
                <TableCell align="right">{item.duration}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </PageContent>
  );
}
