/**
 * KpiCard - Карточка метрики с трендом
 */

import { Card, CardContent, Typography, Box, Skeleton } from '@mui/material';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { ReactNode } from 'react';

interface KpiCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  loading?: boolean;
  subtitle?: string;
}

export const KpiCard = ({ title, value, icon, trend, loading, subtitle }: KpiCardProps) => {
  if (loading) {
    return (
      <Card>
        <CardContent>
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="40%" height={40} />
          <Skeleton variant="text" width="50%" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h4" component="div" fontWeight={700}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          {icon && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 48,
                height: 48,
                borderRadius: 2,
                bgcolor: 'primary.light',
                color: 'primary.main',
                opacity: 0.8,
              }}
            >
              {icon}
            </Box>
          )}
        </Box>

        {trend && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1.5 }}>
            {trend.direction === 'up' ? (
              <TrendingUp size={20} color="#2e7d32" />
            ) : (
              <TrendingDown size={20} color="#d32f2f" />
            )}
            <Typography
              variant="body2"
              sx={{
                ml: 0.5,
                color: trend.direction === 'up' ? 'success.main' : 'error.main',
                fontWeight: 600,
              }}
            >
              {Math.abs(trend.value)}%
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
              vs прошлый месяц
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};
