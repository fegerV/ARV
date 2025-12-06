// components/(media)/MarkerStatusBadge.tsx
import React from 'react';
import {
  Box,
  CircularProgress,
  Chip,
  CheckCircle,
  HourglassEmpty
} from '@mui/material';
import { amber, green } from '@mui/material/colors';

interface MarkerStatusBadgeProps {
  status: 'pending' | 'processing' | 'ready';
  size?: 'small' | 'medium' | 'large';
}

export const MarkerStatusBadge: React.FC<MarkerStatusBadgeProps> = ({ status, size = 'medium' }) => {
  const getSize = () => {
    switch (size) {
      case 'small': return 16;
      case 'large': return 32;
      default: return 24;
    }
  };

  const getStatusIcon = () => {
    const iconSize = getSize();
    
    switch (status) {
      case 'pending':
        return <HourglassEmpty sx={{ color: amber[500], fontSize: iconSize }} />;
      case 'processing':
        return <CircularProgress size={iconSize} thickness={4} />;
      case 'ready':
        return <CheckCircle sx={{ color: green[500], fontSize: iconSize }} />;
      default:
        return <HourglassEmpty sx={{ color: amber[500], fontSize: iconSize }} />;
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
      default:
        return amber[100];
    }
  };

  const getStatusLabel = () => {
    switch (status) {
      case 'pending':
        return 'Ожидание';
      case 'processing':
        return 'Обработка';
      case 'ready':
        return 'Готово';
      default:
        return 'Ожидание';
    }
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
      <Chip
        icon={getStatusIcon()}
        label={getStatusLabel()}
        sx={{
          backgroundColor: getStatusColor(),
          fontWeight: 500,
          height: size === 'small' ? 24 : size === 'large' ? 48 : 32,
          '.MuiChip-icon': {
            color: 'inherit !important'
          }
        }}
        variant="filled"
      />
    </Box>
  );
};