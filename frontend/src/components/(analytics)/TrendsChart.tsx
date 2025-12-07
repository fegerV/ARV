// src/components/(analytics)/TrendsChart.tsx
import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { Typography, Box } from '@mui/material';
import { TrendsData } from '@/services/analyticsService';

interface TrendsChartProps {
  data?: TrendsData;
}

export const TrendsChart: React.FC<TrendsChartProps> = ({ data }) => {
  if (!data || !data.views_trend.length) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="300px">
        <Typography>No data available</Typography>
      </Box>
    );
  }

  // Combine views and duration data by date
  const combinedData = data.views_trend.map((viewPoint, index) => {
    const durationPoint = data.duration_trend[index];
    return {
      date: new Date(viewPoint.date).toLocaleDateString(),
      views: viewPoint.views,
      avg_duration: durationPoint?.avg_duration,
    };
  });

  return (
    <Box sx={{ width: '100%', height: 400 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={combinedData}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="views"
            stroke="#8884d8"
            activeDot={{ r: 8 }}
            name="Views"
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="avg_duration"
            stroke="#82ca9d"
            name="Avg Duration (sec)"
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
};