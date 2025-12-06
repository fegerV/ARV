// pages/Projects/ARContent/Step1Portrait.tsx
import React, { useState } from 'react';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import { FileUploadZone } from '../../components/(forms)/FileUploadZone';
import { useWizard } from './useWizard';
import { arContentApi } from '../../services/ar-content';

export const Step1Portrait: React.FC = () => {
  const { goNext, data, setData } = useWizard();
  const [uploading, setUploading] = useState(false);

  const handlePortraitSelect = async (file: File | null) => {
    if (!file) {
      setData(prev => ({ ...prev, portraitFile: null }));
      return;
    }

    setData(prev => ({ ...prev, portraitFile: file }));
  };

  const handleNext = async () => {
    if (!data.portraitFile) {
      // In a real implementation, we would show an error toast here
      console.error('Загрузите портрет');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', data.portraitFile);
      formData.append('title', data.title || 'Новый контент');
      
      // In a real implementation, we would call the API:
      // const response = await arContentApi.create(formData);
      // setData(prev => ({ ...prev, arContentId: response.data.id }));
      
      // For now, we'll simulate the API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      goNext();
    } catch (error) {
      // In a real implementation, we would show an error toast here
      console.error('Ошибка загрузки портрета', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom align="center">
        Загрузите портрет
      </Typography>
      <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 4 }}>
        Это будет основа для AR-маркера. Рекомендуемое разрешение 1200x1600
      </Typography>
      
      <FileUploadZone
        label="PNG, JPG (до 10MB)"
        accept="image/png,image/jpeg,image/jpg"
        onFileSelect={handlePortraitSelect}
        file={data.portraitFile || undefined}
        uploading={uploading}
      />
      
      <Box sx={{ mt: 4, textAlign: 'center' }}>
        <Button
          variant="contained"
          size="large"
          onClick={handleNext}
          disabled={!data.portraitFile || uploading}
        >
          {uploading ? <CircularProgress size={24} /> : 'Далее: Создать маркер'}
        </Button>
      </Box>
    </Box>
  );
};