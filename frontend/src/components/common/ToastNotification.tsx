import { Snackbar, Alert } from '@mui/material';
import { useToast } from '../../store/useToast';

export default function ToastNotification() {
  const { toasts, removeToast } = useToast();

  return (
    <>
      {toasts.map((toast) => (
        <Snackbar
          key={toast.id}
          open={true}
          autoHideDuration={toast.duration || 5000}
          onClose={() => removeToast(toast.id)}
          anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        >
          <Alert
            onClose={() => removeToast(toast.id)}
            severity={toast.type}
            sx={{ width: '100%' }}
          >
            {toast.message}
          </Alert>
        </Snackbar>
      ))}
    </>
  );
}
