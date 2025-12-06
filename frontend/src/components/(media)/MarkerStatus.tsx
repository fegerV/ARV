// components/(media)/MarkerStatus.tsx
import React from 'react';
import {
  Box,
  CircularProgress,
  Chip,
  CheckCircle,
  Error,
  HourglassEmpty
} from '@mui/material';
import { amber, green, red } from '@mui/material/colors';

interface MarkerStatusProps {
  status: 'pending' | 'processing' | 'ready' | 'failed';
  progress?: number;
}

export const MarkerStatus: React.FC<MarkerStatusProps> = ({ status, progress = 0 }) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'pending':
        return <HourglassEmpty sx={{ color: amber[500] }} />;
      case 'processing':
        return <CircularProgress size={24} thickness={4} />;
      case 'ready':
        return <CheckCircle sx={{ color: green[500] }} />;
      case 'failed':
        return <Error sx={{ color: red[500] }} />;
      default:
        return <HourglassEmpty sx={{ color: amber[500] }} />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'pending':
        return amber[100];
      case 'processing':
        return amber[100];
      case 'ready':
        return green[100];
      case 'failed':
        return red[100];
      default:
        return amber[100];
    }
  };

  const getStatusLabel = () => {
    switch (status) {
      case 'pending':
        return 'Ожидание';
      case 'processing':
        return `Обработка ${progress}%`;
      case 'ready':
        return 'Готово';
      case 'failed':
        return 'Ошибка';
      default:
        return 'Ожидание';
    }
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center' }}>
      <Chip
        icon={getStatusIcon()}
        label={getStatusLabel()}
        sx={{
          backgroundColor: getStatusColor(),
          fontWeight: 500,
          '.MuiChip-icon': {
            color: 'inherit !important'
          }
        }}
        variant="filled"
      />
    </Box>
  );
};