// components/(media)/QRCodeCard.tsx
import React from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent
} from '@mui/material';
import { Download, Print } from '@mui/icons-material';

interface QRCodeCardProps {
  value?: string;
  title: string;
  size?: number;
  uniqueId?: string;
  url?: string;
}

export const QRCodeCard: React.FC<QRCodeCardProps> = ({ value, title, size = 200, uniqueId, url }) => {
  // In a real implementation, you would generate an actual QR code
  // For now, we'll show a placeholder
  
  const handleDownload = () => {
    // Implementation for downloading QR code
    console.log('Downloading QR code for:', uniqueId || value);
  };

  const handlePrint = () => {
    // Implementation for printing QR code
    console.log('Printing QR code for:', uniqueId || value);
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          my: 3,
          p: 2,
          border: '1px dashed #ccc',
          borderRadius: 1
        }}>
          <Box sx={{ 
            width: size, 
            height: size, 
            bgcolor: '#f5f5f5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 2
          }}>
            <Typography color="text.secondary">
              QR-код<br />
              <small>({uniqueId || value})</small>
            </Typography>
          </Box>
          
          <Typography variant="caption" color="text.secondary">
            Сканируйте QR-код для доступа к AR-контенту
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={handleDownload}
          >
            Скачать
          </Button>
          <Button
            variant="contained"
            startIcon={<Print />}
            onClick={handlePrint}
          >
            Печать
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};