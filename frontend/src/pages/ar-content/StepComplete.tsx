// pages/Projects/ARContent/StepComplete.tsx
import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { useWizard } from './useWizard';

export const StepComplete: React.FC = () => {
  const { data } = useWizard();

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', textAlign: 'center' }}>
      <Typography variant="h3" gutterBottom color="success.main">
        ✅ Готово!
      </Typography>
      
      <Typography variant="h5" gutterBottom sx={{ mb: 4 }}>
        AR-контент "{data.title}" создан
      </Typography>
      
      <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
        <Button variant="contained" size="large">
          Скачать QR (PDF)
        </Button>
        <Button variant="outlined" size="large">
          Отправить клиенту
        </Button>
        <Button variant="outlined" size="large">
          Посмотреть AR
        </Button>
      </Box>
    </Box>
  );
};