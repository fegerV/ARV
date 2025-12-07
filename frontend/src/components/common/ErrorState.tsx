import { Box, Button, Typography } from '@mui/material';

type Props = {
  message?: string;
  onRetry?: () => void;
};

export const ErrorState: React.FC<Props> = ({ message, onRetry }) => (
  <Box sx={{ py: 6, textAlign: 'center' }}>
    <Typography variant="h6" gutterBottom>
      Что-то пошло не так
    </Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
      {message || 'Попробуйте обновить страницу или повторить попытку.'}
    </Typography>
    {onRetry && (
      <Button variant="contained" onClick={onRetry}>
        Повторить
      </Button>
    )}
  </Box>
);