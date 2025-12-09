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
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import { analyticsAPI } from '../services/api';

const COLORS = ['#1976d2', '#2e7d32', '#ed6c02', '#d32f2f', '#7b1fa2'];

interface AnalyticsFilters {
  period: '1d' | '7d' | '30d' | 'custom';
}

export default function Analytics() {
  const [filters, setFilters] = useState<AnalyticsFilters>({
    period: '7d',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mock data
  const overviewCards = [
    { title: 'Total Views', value: '125,892', change: '+12.5%' },
    { title: 'Unique Sessions', value: '98,234', change: '+8.3%' },
    { title: 'Avg. Duration', value: '2m 34s', change: '+4.2%' },
    { title: 'Conversion Rate', value: '12.5%', change: '-2.1%' },
  ];

  const viewsTrendData = [
    { date: 'Jan 1', views: 1200, sessions: 800 },
    { date: 'Jan 2', views: 1900, sessions: 1200 },
    { date: 'Jan 3', views: 900, sessions: 600 },
    { date: 'Jan 4', views: 2200, sessions: 1400 },
    { date: 'Jan 5', views: 2290, sessions: 1500 },
    { date: 'Jan 6', views: 2000, sessions: 1300 },
    { date: 'Jan 7', views: 2181, sessions: 1400 },
  ];

  const viewsByCompanyData = [
    { name: 'Company A', views: 25000 },
    { name: 'Company B', views: 20000 },
    { name: 'Company C', views: 15000 },
    { name: 'Others', views: 65000 },
  ];

  const deviceBreakdownData = [
    { name: 'iPhone', value: 35 },
    { name: 'Android', value: 45 },
    { name: 'Web', value: 15 },
    { name: 'Tablet', value: 5 },
  ];

  const topContentData = [
    { id: 1, title: 'Winter Santa Campaign', views: 25892, sessions: 18234, duration: '3m 45s' },
    { id: 2, title: 'New Year Offer', views: 18234, sessions: 12500, duration: '2m 30s' },
    { id: 3, title: 'Holiday Special', views: 15000, sessions: 10000, duration: '2m 15s' },
    { id: 4, title: 'Winter Showcase', views: 12450, sessions: 8500, duration: '2m 00s' },
    { id: 5, title: 'Magical Forest', views: 10234, sessions: 7200, duration: '3m 20s' },
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
    try {
      await analyticsAPI.overview();
      setTimeout(() => setLoading(false), 1000);
    } catch (err) {
      setError('Failed to fetch analytics');
      setLoading(false);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Analytics
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Detailed analysis of views and user interactions
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
          onClick={handleRefresh}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3, display: 'flex', gap: 2, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Period</InputLabel>
          <Select
            value={filters.period}
            label="Period"
            onChange={(e) => handleFilterChange('period', e.target.value)}
          >
            <MenuItem value="1d">Last 24 hours</MenuItem>
            <MenuItem value="7d">Last 7 days</MenuItem>
            <MenuItem value="30d">Last 30 days</MenuItem>
            <MenuItem value="custom">Custom Range</MenuItem>
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
                  {card.title}
                </Typography>
                <Typography variant="h5" sx={{ mb: 1 }}>
                  {card.value}
                </Typography>
                <Chip
                  label={card.change}
                  size="small"
                  color={card.change.startsWith('+') ? 'success' : 'error'}
                  variant="outlined"
                />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Views Trend Chart */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Views & Sessions Trend
        </Typography>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={viewsTrendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="views" stroke="#1976d2" strokeWidth={2} />
            <Line type="monotone" dataKey="sessions" stroke="#2e7d32" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </Paper>

      {/* Charts Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {/* Views by Company */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Views by Company
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
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
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Device Breakdown
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
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
                  {deviceBreakdownData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Session Duration Chart */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Session Duration Distribution
        </Typography>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={sessionDurationData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="duration" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#ed6c02" />
          </BarChart>
        </ResponsiveContainer>
      </Paper>

      {/* Top Content Table */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Top AR Content
        </Typography>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell>Title</TableCell>
              <TableCell align="right">Views</TableCell>
              <TableCell align="right">Sessions</TableCell>
              <TableCell align="right">Avg. Duration</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {topContentData.map((content) => (
              <TableRow key={content.id} hover>
                <TableCell>{content.title}</TableCell>
                <TableCell align="right">{content.views.toLocaleString()}</TableCell>
                <TableCell align="right">{content.sessions.toLocaleString()}</TableCell>
                <TableCell align="right">{content.duration}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
