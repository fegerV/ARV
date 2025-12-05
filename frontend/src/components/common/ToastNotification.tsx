import { Snackbar, Alert } from '@mui/material';
import { useToast } from '../../store/useToast';

export default function ToastNotification() {
  const { open, message, severity, hideToast } = useToast();

  return (
    <Snackbar
      open={open}
      autoHideDuration={6000}
      onClose={hideToast}
      anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
    >
      <Alert onClose={hideToast} severity={severity} sx={{ width: '100%' }}>
        {message}
      </Alert>
    </Snackbar>
  );
}
