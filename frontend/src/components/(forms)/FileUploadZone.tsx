import React, { useCallback, useRef } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  CircularProgress,
  Card,
  CardContent,
  useTheme
} from '@mui/material';
import { CloudUpload, Image, Delete } from '@mui/icons-material';

interface FileUploadZoneProps {
  label: string;
  accept: string;
  onFileSelect: (file: File | null) => void;
  file?: File;
  uploading?: boolean;
}

export const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  label,
  accept,
  onFileSelect,
  file,
  uploading
}) => {
  const theme = useTheme();
  const inputRef = useRef&lt;HTMLInputElement&gt;(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith(accept.split(',')[0])) {
      onFileSelect(droppedFile);
    }
  }, [onFileSelect]);

  const handleFileSelect = (e: React.ChangeEvent&lt;HTMLInputElement&gt;) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      onFileSelect(selectedFile);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    &lt;Card
      sx={{
        border: 2,
        borderColor: 'divider',
        borderStyle: 'dashed',
        borderRadius: 2,
        transition: 'all 0.3s',
        '&amp;:hover': {
          borderColor: 'primary.main',
          backgroundColor: 'action.hover'
        },
        minHeight: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative'
      }}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    &gt;
      {uploading ? (
        &lt;Box sx={{ textAlign: 'center' }}&gt;
          &lt;CircularProgress size={48} /&gt;
          &lt;Typography sx={{ mt: 2 }}&gt;Загрузка...&lt;/Typography&gt;
        &lt;/Box&gt;
      ) : file ? (
        &lt;Box sx={{ textAlign: 'center', p: 2 }}&gt;
          &lt;img
            src={URL.createObjectURL(file)}
            alt="Preview"
            style={{
              maxWidth: 300,
              maxHeight: 300,
              objectFit: 'contain',
              borderRadius: 8
            }}
          /&gt;
          &lt;Typography variant="h6" sx={{ mt: 2 }}&gt;
            {file.name}
          &lt;/Typography&gt;
          &lt;Typography variant="body2" color="text.secondary"&gt;
            {formatBytes(file.size)} • {file.type}
          &lt;/Typography&gt;
          &lt;Button
            variant="outlined"
            startIcon={&lt;Delete /&gt;}
            onClick={() => onFileSelect(null)}
            sx={{ mt: 2 }}
          &gt;
            Удалить
          &lt;/Button&gt;
        &lt;/Box&gt;
      ) : (
        &lt;CardContent sx={{ textAlign: 'center', p: 4 }}&gt;
          &lt;CloudUpload sx={{ fontSize: 64, color: 'action.active', mb: 2 }} /&gt;
          &lt;Typography variant="h6" gutterBottom&gt;
            {label}
          &lt;/Typography&gt;
          &lt;Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}&gt;
            Перетащите файл сюда или кликните для выбора
          &lt;/Typography&gt;
          &lt;Button
            variant="contained"
            component="label"
            startIcon={&lt;Image /&gt;}
          &gt;
            Выбрать файл
            &lt;input
              ref={inputRef}
              type="file"
              accept={accept}
              hidden
              onChange={handleFileSelect}
            /&gt;
          &lt;/Button&gt;
        &lt;/CardContent&gt;
      )}
    &lt;/Card&gt;
  );
};