// pages/Projects/ARContent/Step3Videos.tsx
import React from 'react';
import { Box, Typography, Button, IconButton } from '@mui/material';
import { VideoUploadList } from '../../components';
import { useWizard } from './useWizard';
import { VideoUpload } from '../../types/ar-content';
import { Add, Remove } from '@mui/icons-material';

export const Step3Videos: React.FC = () => {
  const { data, setData, goNext } = useWizard();

  const handleAddVideo = () => {
    const newVideo: VideoUpload = {
      id: Date.now().toString(),
      file: new File([], ''),
      title: ''
    };
    setData(prev => ({
      ...prev,
      videos: [...prev.videos, newVideo]
    }));
  };

  const handleRemoveVideo = (id: string) => {
    setData(prev => ({
      ...prev,
      videos: prev.videos.filter(video => video.id !== id)
    }));
  };

  const handleVideoChange = (id: string, field: keyof VideoUpload, value: any) => {
    setData(prev => ({
      ...prev,
      videos: prev.videos.map(video => 
        video.id === id ? { ...video, [field]: value } : video
      )
    }));
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom align="center">
        Загрузите видео
      </Typography>
      <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 4 }}>
        Вы можете загрузить несколько видео для ротации
      </Typography>
      
      {data.videos.map((video) => (
        <Box key={video.id} sx={{ mb: 2, p: 2, border: '1px solid #eee', borderRadius: 1 }}>
          <VideoUploadList
            video={video}
            onChange={(field: keyof VideoUpload, value: any) => handleVideoChange(video.id, field, value)}
          />
          <IconButton 
            onClick={() => handleRemoveVideo(video.id)}
            sx={{ mt: 1 }}
          >
            <Remove />
          </IconButton>
        </Box>
      ))}
      
      <Button
        startIcon={<Add />}
        onClick={handleAddVideo}
        variant="outlined"
        sx={{ mb: 3 }}
      >
        Добавить видео
      </Button>
    </Box>
  );
};