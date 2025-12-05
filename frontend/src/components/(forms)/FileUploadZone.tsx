/**
 * FileUploadZone - Drag-n-drop зона для загрузки файлов
 */

import { useState, useCallback } from 'react';
import { Box, Typography, Paper, IconButton } from '@mui/material';
import { Upload, X, Paperclip } from 'lucide-react';
import { useToast } from '../../store/useToast';

interface FileUploadZoneProps {
  accept: string;
  maxSize?: number; // MB
  onFileSelect: (file: File) => void;
  label?: string;
  description?: string;
  preview?: string;
}

export const FileUploadZone = ({
  accept,
  maxSize = 10,
  onFileSelect,
  label = 'Загрузить файл',
  description,
}: FileUploadZoneProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const { showToast } = useToast();

  const validateFile = (file: File): boolean => {
    const maxSizeBytes = maxSize * 1024 * 1024;

    if (file.size > maxSizeBytes) {
      showToast(`Файл слишком большой. Максимум ${maxSize}MB`, 'error');
      return false;
    }

    return true;
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile && validateFile(droppedFile)) {
        setFile(droppedFile);
        onFileSelect(droppedFile);
      }
    },
    [maxSize, onFileSelect]
  );

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && validateFile(selectedFile)) {
      setFile(selectedFile);
      onFileSelect(selectedFile);
    }
  };

  const handleRemove = () => {
    setFile(null);
  };

  return (
    <Paper
      sx={{
        p: 3,
        border: 2,
        borderStyle: 'dashed',
        borderColor: isDragging ? 'primary.main' : 'divider',
        bgcolor: isDragging ? 'action.hover' : 'background.paper',
        textAlign: 'center',
        cursor: 'pointer',
        transition: 'all 300ms',
        '&:hover': {
          borderColor: 'primary.main',
          bgcolor: 'action.hover',
        },
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      {!file ? (
        <>
          <Upload size={48} style={{ color: 'text.secondary', marginBottom: 16 }} />
          <Typography variant="h6" gutterBottom>
            {label}
          </Typography>
          {description && (
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {description}
            </Typography>
          )}
          <Typography variant="caption" display="block" color="text.secondary">
            Перетащите файл или нажмите для выбора
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Максимальный размер: {maxSize}MB
          </Typography>
          <input
            type="file"
            accept={accept}
            onChange={handleFileInput}
            style={{ display: 'none' }}
            id="file-upload-input"
          />
          <label htmlFor="file-upload-input">
            <Box component="span" sx={{ display: 'block', mt: 2 }}>
              <Typography variant="button" color="primary" sx={{ cursor: 'pointer' }}>
                Выбрать файл
              </Typography>
            </Box>
          </label>
        </>
      ) : (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Paperclip size={20} />
              <Typography variant="body1">{file.name}</Typography>
            </Box>
            <IconButton onClick={handleRemove} size="small" color="error">
              <X size={20} />
            </IconButton>
          </Box>
          <Typography variant="caption" color="text.secondary">
            {(file.size / 1024 / 1024).toFixed(2)} MB
          </Typography>
        </Box>
      )}
    </Paper>
  );
};
