import { Box, CircularProgress, Typography } from '@mui/material';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ message = 'Загрузка...' }) => (
  <Box sx={{ py: 6, textAlign: 'center' }}>
    <CircularProgress sx={{ mb: 2 }} />
    <Typography variant="body2" color="text.secondary">
      {message}
    </Typography>
  </Box>
);