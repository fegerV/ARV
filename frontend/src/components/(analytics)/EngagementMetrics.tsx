// src/components/(analytics)/EngagementMetrics.tsx
import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Typography, Box, Grid } from '@mui/material';
import { EngagementMetrics as EngagementMetricsType } from '@/services/analyticsService';
import { KpiCard } from './KpiCard';

interface EngagementMetricsProps {
  data?: EngagementMetricsType;
}

export const EngagementMetrics: React.FC<EngagementMetricsProps> = ({ data }) => {
  if (!data) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="200px">
        <Typography>No data available</Typography>
      </Box>
    );
  }

  // Prepare hourly distribution data
  const hourlyData = data.hourly_distribution.map(item => ({
    hour: `${item.hour}:00`,
    count: item.count,
  }));

  return (
    <Box>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6}>
          <KpiCard
            title="Avg First Session"
            value={`${data.avg_first_session_duration.toFixed(2)}s`}
          />
        </Grid>
        <Grid item xs={6}>
          <KpiCard
            title="Sessions per User"
            value={data.avg_sessions_per_user.toFixed(2)}
          />
        </Grid>
      </Grid>

      <Box sx={{ width: '100%', height: 300 }}>
        <Typography variant="subtitle1" gutterBottom>
          Hourly Distribution
        </Typography>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={hourlyData}
            margin={{
              top: 5,
              right: 30,
              left: 20,
              bottom: 40,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="hour" 
              angle={-45} 
              textAnchor="end" 
              height={60}
            />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#8884d8" name="Sessions" />
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
};