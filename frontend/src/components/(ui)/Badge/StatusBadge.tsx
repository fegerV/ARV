/**
 * StatusBadge - Badge для отображения статусов AR контента
 */

import { Chip } from '@mui/material';
import {
  CheckCircle,
  Schedule,
  Error,
  HourglassEmpty,
  Warning,
} from '@mui/icons-material';
import type { StatusBadgeProps } from '../../../types/components';

const statusConfig = {
  pending: {
    label: 'В очереди',
    color: 'default' as const,
    icon: <Schedule fontSize="small" />,
  },
  processing: {
    label: 'Обработка',
    color: 'info' as const,
    icon: <HourglassEmpty fontSize="small" />,
  },
  ready: {
    label: 'Готово',
    color: 'success' as const,
    icon: <CheckCircle fontSize="small" />,
  },
  failed: {
    label: 'Ошибка',
    color: 'error' as const,
    icon: <Error fontSize="small" />,
  },
  active: {
    label: 'Активно',
    color: 'success' as const,
    icon: <CheckCircle fontSize="small" />,
  },
  expired: {
    label: 'Истекло',
    color: 'warning' as const,
    icon: <Warning fontSize="small" />,
  },
};

export const StatusBadge = ({ status, size = 'medium' }: StatusBadgeProps) => {
  const config = statusConfig[status];

  return (
    <Chip
      label={config.label}
      color={config.color}
      size={size}
      icon={config.icon}
      sx={{ fontWeight: 500 }}
    />
  );
};
