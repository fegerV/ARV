// src/components/MinioDirectUpload.tsx
import React, { useState } from 'react';
import {
  Box,
  Button,
  LinearProgress,
  Typography,
  Alert,
  TextField,
  Card,
  CardContent,
  CardActions,
} from '@mui/material';
import { minioService, PresignedURLRequest } from '@/services/minioService';

interface MinioDirectUploadProps {
  connectionId: number;
  bucket: string;
  onUploadComplete?: (objectName: string) => void;
}

export const MinioDirectUpload: React.FC<MinioDirectUploadProps> = ({
  connectionId,
  bucket,
  onUploadComplete,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [objectName, setObjectName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [presignedUrl, setPresignedUrl] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const selectedFile = event.target.files[0];
      setFile(selectedFile);
      
      // Auto-generate object name if not set
      if (!objectName) {
        setObjectName(`uploads/${Date.now()}_${selectedFile.name}`);
      }
    }
  };

  const handleGeneratePresignedUrl = async () => {
    if (!file || !objectName) {
      setError('Please select a file and specify an object name');
      return;
    }

    try {
      setError(null);
      setUploading(true);
      
      // Generate presigned URL
      const request: PresignedURLRequest = {
        bucket,
        object_name: objectName,
        method: 'PUT',
        expires_in: 3600, // 1 hour
      };
      
      const response = await minioService.generatePresignedURL(connectionId, request);
      setPresignedUrl(response.url);
      
      // Upload file directly to MinIO
      await minioService.uploadFileWithPresignedURL(
        response.url,
        file,
        (progress) => setProgress(progress)
      );
      
      // Upload complete
      setUploading(false);
      setProgress(100);
      
      if (onUploadComplete) {
        onUploadComplete(objectName);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Direct MinIO Upload
        </Typography>
        
        <Box sx={{ mb: 2 }}>
          <input
            accept="*/*"
            style={{ display: 'none' }}
            id="file-upload"
            type="file"
            onChange={handleFileChange}
          />
          <label htmlFor="file-upload">
            <Button variant="outlined" component="span" fullWidth>
              {file ? file.name : 'Choose File'}
            </Button>
          </label>
        </Box>
        
        <TextField
          fullWidth
          label="Object Name"
          value={objectName}
          onChange={(e) => setObjectName(e.target.value)}
          placeholder="e.g., uploads/my-file.jpg"
          sx={{ mb: 2 }}
        />
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        {uploading && (
          <Box sx={{ mb: 2 }}>
            <LinearProgress variant="determinate" value={progress} />
            <Typography variant="body2" align="center" sx={{ mt: 1 }}>
              Uploading... {progress}%
            </Typography>
          </Box>
        )}
        
        {progress === 100 && !uploading && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Upload completed successfully!
          </Alert>
        )}
      </CardContent>
      
      <CardActions>
        <Button
          variant="contained"
          onClick={handleGeneratePresignedUrl}
          disabled={!file || !objectName || uploading}
          fullWidth
        >
          Upload to MinIO
        </Button>
      </CardActions>
    </Card>
  );
};