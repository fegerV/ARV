// components/(media)/ContentPreviewCell.tsx
import React from 'react';
import { Box, Avatar, Skeleton } from '@mui/material';

interface ContentPreviewCellProps {
  imageUrl?: string;
  size?: number;
}

export const ContentPreviewCell: React.FC<ContentPreviewCellProps> = ({ 
  imageUrl, 
  size = 60 
}) => {
  if (!imageUrl) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Skeleton variant="rectangular" width={size} height={size} />
      </Box>
    );
  }

  return (
    <Avatar
      src={imageUrl}
      sx={{ 
        width: size, 
        height: size,
        borderRadius: 1
      }}
      variant="rounded"
    />
  );
};