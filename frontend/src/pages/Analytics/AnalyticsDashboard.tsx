// src/pages/Analytics/AnalyticsDashboard.tsx
import React, { useState } from 'react';
import {
  Container,
  Grid,
  Typography,
  Paper,
  Box,
  TextField,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { 
  analyticsService, 
  AnalyticsFilters, 
  AnalyticsOverview, 
  TrendsData, 
  TopContentItem, 
  DeviceStats, 
  EngagementMetrics as EngagementMetricsType 
} from '@/services/analyticsService';
import { KpiCard } from '@/components/(analytics)/KpiCard';
import { TrendsChart } from '@/components/(analytics)/TrendsChart';
import { TopContentTable } from '@/components/(analytics)/TopContentTable';
import { DeviceStatsChart } from '@/components/(analytics)/DeviceStatsChart';
import { EngagementMetrics } from '@/components/(analytics)/EngagementMetrics';

const AnalyticsDashboard: React.FC = () => {
  const [filters, setFilters] = useState<AnalyticsFilters>({
    start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
  });
  
  const [dateRange, setDateRange] = useState<{
    start: Date | null;
    end: Date | null;
  }>({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    end: new Date(),
  });

  const { data: overview, isLoading, error, refetch } = useQuery<AnalyticsOverview>({
    queryKey: ['analytics-overview', filters],
    queryFn: () => analyticsService.getOverview(filters)
  });

  const { data: trends } = useQuery<TrendsData>({
    queryKey: ['analytics-trends', filters],
    queryFn: () => analyticsService.getTrends(filters)
  });

  const { data: topContent } = useQuery<TopContentItem[]>({
    queryKey: ['analytics-top-content', filters],
    queryFn: () => analyticsService.getTopContent({ ...filters, limit: 10 })
  });

  const { data: deviceStats } = useQuery<DeviceStats>({
    queryKey: ['analytics-device-stats', filters],
    queryFn: () => analyticsService.getDeviceStats(filters)
  });

  const { data: engagement } = useQuery<EngagementMetricsType>({
    queryKey: ['analytics-engagement', filters],
    queryFn: () => analyticsService.getEngagementMetrics(filters)
  });

  const handleFilterChange = (field: keyof AnalyticsFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleApplyFilters = () => {
    if (dateRange.start) {
      handleFilterChange('start_date', dateRange.start.toISOString().split('T')[0]);
    }
    if (dateRange.end) {
      handleFilterChange('end_date', dateRange.end.toISOString().split('T')[0]);
    }
  };

  if (error) {
    return (
      <Container maxWidth={false}>
        <Alert severity="error">
          Error loading analytics data. Please try again later.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth={false}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Analytics Dashboard</Typography>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={3}>
            <TextField
              label="Start Date"
              type="date"
              value={dateRange.start ? dateRange.start.toISOString().split('T')[0] : ''}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value ? new Date(e.target.value) : null }))}
              fullWidth
              InputLabelProps={{
                shrink: true,
              }}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField
              label="End Date"
              type="date"
              value={dateRange.end ? dateRange.end.toISOString().split('T')[0] : ''}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value ? new Date(e.target.value) : null }))}
              fullWidth
              InputLabelProps={{
                shrink: true,
              }}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <Button
              variant="contained"
              onClick={handleApplyFilters}
              fullWidth
            >
              Apply Filters
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {isLoading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="200px">
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* KPI Cards */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={2}>
              <KpiCard
                title="Total Views"
                value={overview?.total_views || 0}
                trend={{ value: 0, direction: 'up' }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <KpiCard
                title="Unique Sessions"
                value={overview?.unique_sessions || 0}
                trend={{ value: 0, direction: 'up' }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <KpiCard
                title="Avg Duration (sec)"
                value={overview?.avg_session_duration || 0}
                trend={{ value: 0, direction: 'up' }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <KpiCard
                title="Avg FPS"
                value={overview?.avg_fps || 0}
                trend={{ value: 0, direction: 'up' }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <KpiCard
                title="Tracking Success"
                value={`${overview?.tracking_success_rate || 0}%`}
                trend={{ value: 0, direction: 'up' }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={2}>
              <KpiCard
                title="Active Content"
                value={overview?.active_content || 0}
                trend={{ value: 0, direction: 'up' }}
              />
            </Grid>
          </Grid>

          {/* Charts and Tables */}
          <Grid container spacing={3}>
            {/* Trends Chart */}
            <Grid item xs={12} lg={8}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Views and Duration Trends
                </Typography>
                <TrendsChart data={trends} />
              </Paper>
            </Grid>

            {/* Device Stats */}
            <Grid item xs={12} lg={4}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Device Distribution
                </Typography>
                <DeviceStatsChart data={deviceStats} />
              </Paper>
            </Grid>

            {/* Top Content */}
            <Grid item xs={12} lg={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Top AR Content
                </Typography>
                <TopContentTable data={topContent || []} />
              </Paper>
            </Grid>

            {/* Engagement Metrics */}
            <Grid item xs={12} lg={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Engagement Metrics
                </Typography>
                <EngagementMetrics data={engagement} />
              </Paper>
            </Grid>
          </Grid>
        </>
      )}
    </Container>
  );
};

export default AnalyticsDashboard;