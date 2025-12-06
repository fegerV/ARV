// pages/Projects/ARContent/Step2Marker.tsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, LinearProgress } from '@mui/material';
import { MarkerStatusBadge } from '../../components/(media)/MarkerStatusBadge';
import { useWizard } from './useWizard';

export const Step2Marker: React.FC = () => {
  const { data, goNext } = useWizard();
  const [markerStatus, setMarkerStatus] = useState<'pending' | 'processing' | 'ready'>('pending');
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Simulate marker generation
    setMarkerStatus('processing');
    
    // Simulate polling status
    const interval = setInterval(() => {
      setMarkerStatus(prev => {
        if (prev === 'processing') {
          const newProgress = Math.min(progress + 10, 90);
          setProgress(newProgress);
          
          // When progress reaches 90%, mark as ready
          if (newProgress >= 90) {
            clearInterval(interval);
            setTimeout(() => {
              setMarkerStatus('ready');
              setProgress(100);
              setTimeout(goNext, 1500);
            }, 1000);
            return 'processing';
          }
          return 'processing';
        }
        return prev;
      });
    }, 2000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ textAlign: 'center', maxWidth: 600, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>
        Генерация NFT-маркера
      </Typography>
      
      <Box sx={{ mb: 4 }}>
        <MarkerStatusBadge status={markerStatus} size="large" />
        <Typography variant="h6" sx={{ mt: 2 }}>
          {markerStatus === 'processing' && 'Генерируем маркер...'}
          {markerStatus === 'ready' && '✅ Маркер готов!'}
        </Typography>
      </Box>
      
      <LinearProgress variant="determinate" value={progress} sx={{ mb: 2 }} />
      
      {markerStatus === 'ready' && (
        <Typography variant="body2" color="success.main">
          Качество: 1,247 feature points (отлично)
        </Typography>
      )}
    </Box>
  );
};