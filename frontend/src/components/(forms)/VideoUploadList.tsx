// components/(forms)/VideoUploadList.tsx
import React from 'react';
import {
  Box,
  TextField,
  Typography
} from '@mui/material';
import { FileUploadZone } from './FileUploadZone';
import { VideoUpload } from '../../types/ar-content';

interface VideoUploadListProps {
  video: VideoUpload;
  onChange: (field: keyof VideoUpload, value: any) => void;
}

export const VideoUploadList: React.FC<VideoUploadListProps> = ({ video, onChange }) => {
  const handleFileSelect = (file: File | null) => {
    if (file) {
      onChange('file', file);
      
      // Auto-fill title from filename if empty
      if (!video.title) {
        const title = file.name.replace(/\.[^/.]+$/, ""); // Remove extension
        onChange('title', title);
      }
    }
  };

  return (
    <Box>
      <TextField
        fullWidth
        label="Название видео"
        value={video.title}
        onChange={(e) => onChange('title', e.target.value)}
        margin="normal"
        required
      />
      
      <Box sx={{ my: 2 }}>
        <FileUploadZone
          label="Загрузите видео файл"
          accept="video/*"
          onFileSelect={handleFileSelect}
          file={video.file}
        />
      </Box>
      
      {video.file && video.file.size > 0 && (
        <Typography variant="caption" color="text.secondary">
          Размер файла: {(video.file.size / (1024 * 1024)).toFixed(2)} MB
        </Typography>
      )}
    </Box>
  );
};