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
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith(accept.split(',')[0])) {
      onFileSelect(droppedFile);
    }
  }, [onFileSelect]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
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
    <Card
      sx={{
        border: 2,
        borderColor: 'divider',
        borderStyle: 'dashed',
        borderRadius: 2,
        transition: 'all 0.3s',
        '&:hover': {
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
    >
      {uploading ? (
        <Box sx={{ textAlign: 'center' }}>
          <CircularProgress size={48} />
          <Typography sx={{ mt: 2 }}>Загрузка...</Typography>
        </Box>
      ) : file ? (
        <Box sx={{ textAlign: 'center', p: 2 }}>
          <img
            src={URL.createObjectURL(file)}
            alt="Preview"
            style={{
              maxWidth: 300,
              maxHeight: 300,
              objectFit: 'contain',
              borderRadius: 8
            }}
          />
          <Typography variant="h6" sx={{ mt: 2 }}>
            {file.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {formatBytes(file.size)} • {file.type}
          </Typography>
          <Button
            variant="outlined"
            startIcon={<Delete />}
            onClick={() => onFileSelect(null)}
            sx={{ mt: 2 }}
          >
            Удалить
          </Button>
        </Box>
      ) : (
        <CardContent sx={{ textAlign: 'center', p: 4 }}>
          <CloudUpload sx={{ fontSize: 64, color: 'action.active', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            {label}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Перетащите файл сюда или кликните для выбора
          </Typography>
          <Button
            variant="contained"
            component="label"
            startIcon={<Image />}
          >
            Выбрать файл
            <input
              ref={inputRef}
              type="file"
              accept={accept}
              hidden
              onChange={handleFileSelect}
            />
          </Button>
        </CardContent>
      )}
    </Card>
  );
};