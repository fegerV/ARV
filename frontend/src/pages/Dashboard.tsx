import { useEffect, useState } from 'react';
import { Box, Typography, Grid, Card, CardContent, Paper, CircularProgress, Alert } from '@mui/material';
import {
  Visibility as ViewsIcon,
  People as SessionsIcon,
  ViewInAr as ContentIcon,
  Storage as StorageIcon,
  Business as CompaniesIcon,
  Folder as ProjectsIcon,
  AttachMoney as RevenueIcon,
  CheckCircle as UptimeIcon,
} from '@mui/icons-material';

import { analyticsAPI } from '../services/api';
import { useToast } from '../store/useToast';

interface AnalyticsSummary {
  total_views: number;
  unique_sessions: number;
  active_content: number;
  storage_used_gb: number | null;
}

export default function Dashboard() {
  const { addToast } = useToast();
  
  console.log('Dashboard component rendered');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await analyticsAPI.summary();
        setSummary(res.data as AnalyticsSummary);
      } catch (err: any) {
        const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to load dashboard data';
        setError(msg);
        addToast(msg, 'error');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [addToast]);

  const statsCards = [
    {
      title: 'Total AR Views',
      value: summary && summary.total_views !== undefined ? summary.total_views.toLocaleString() : '—',
      change: '',
      icon: <ViewsIcon fontSize="large" />,
      color: '#1976d2',
    },
    {
      title: 'Unique Sessions',
      value: summary && summary.unique_sessions !== undefined ? summary.unique_sessions.toLocaleString() : '—',
      change: '',
      icon: <SessionsIcon fontSize="large" />,
      color: '#2e7d32',
    },
    {
      title: 'Active Content',
      value: summary && summary.active_content !== undefined ? summary.active_content.toLocaleString() : '—',
      change: '',
      icon: <ContentIcon fontSize="large" />,
      color: '#9c27b0',
    },
    {
      title: 'Storage Usage',
      value: summary?.storage_used_gb != null ? `${summary.storage_used_gb} GB` : '—',
      change: '',
      icon: <StorageIcon fontSize="large" />,
      color: '#ed6c02',
    },
    { title: 'Active Companies', value: '—', change: '', icon: <CompaniesIcon fontSize="large" />, color: '#0288d1' },
    { title: 'Active Projects', value: '—', change: '', icon: <ProjectsIcon fontSize="large" />, color: '#7b1fa2' },
    { title: 'Revenue', value: '—', change: '', icon: <RevenueIcon fontSize="large" />, color: '#2e7d32' },
    { title: 'Uptime', value: '—', change: '', icon: <UptimeIcon fontSize="large" />, color: '#4caf50' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
          <CircularProgress />
        </Box>
      )}

      <Grid container spacing={3}>
        {statsCards.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card elevation={2}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box>
                    <Typography color="textSecondary" variant="caption" gutterBottom>
                      {stat.title}
                    </Typography>
                    <Typography variant="h5" sx={{ fontWeight: 700, my: 1 }}>
                      {stat.value}
                    </Typography>
                    {stat.change ? (
                      <Typography variant="body2" color="success.main">
                        {stat.change}
                      </Typography>
                    ) : null}
                  </Box>
                  <Box sx={{ color: stat.color }}>
                    {stat.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Box sx={{ mt: 4 }}>
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Recent Activity
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Activity feed будет здесь...
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
}
