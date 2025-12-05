/**
 * ConfirmDialog - Диалог подтверждения действия
 */

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
} from '@mui/material';
import { AlertTriangle, Info, AlertCircle } from 'lucide-react';
import { Button } from '../(ui)';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'info';
}

export const ConfirmDialog = ({
  open,
  title,
  message,
  onConfirm,
  onCancel,
  loading = false,
  confirmLabel = 'Подтвердить',
  cancelLabel = 'Отмена',
  variant = 'warning',
}: ConfirmDialogProps) => {
  const getIcon = () => {
    switch (variant) {
      case 'danger':
        return <AlertCircle size={24} color="#d32f2f" />;
      case 'info':
        return <Info size={24} color="#0288d1" />;
      default:
        return <AlertTriangle size={24} color="#ed6c02" />;
    }
  };

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        {getIcon()}
        {title}
      </DialogTitle>
      <DialogContent>
        <Typography>{message}</Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button variant="secondary" onClick={onCancel} disabled={loading}>
          {cancelLabel}
        </Button>
        <Button
          variant={variant === 'danger' ? 'danger' : 'primary'}
          onClick={onConfirm}
          loading={loading}
          disabled={loading}
        >
          {confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
