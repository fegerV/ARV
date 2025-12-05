import React, { useState } from 'react';
import {
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Box,
  Alert,
} from '@mui/material';
import axios from 'axios';
import { YandexDiskAuth } from './YandexDiskAuth';
import { YandexDiskFolderPicker } from './YandexDiskFolderPicker';

export const CompanyForm: React.FC = () => {
  const [companyName, setCompanyName] = useState('');
  const [storageProvider, setStorageProvider] = useState<string>('');
  const [storageConnectionId, setStorageConnectionId] = useState<number | null>(null);
  const [selectedFolder, setSelectedFolder] = useState('');
  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleYandexAuthSuccess = (connectionId: number) => {
    setStorageConnectionId(connectionId);
    setStorageProvider('yandex_disk');
    setShowFolderPicker(true);
  };

  const handleFolderSelect = (folderPath: string) => {
    setSelectedFolder(folderPath);
    setShowFolderPicker(false);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const payload = {
        name: companyName,
        storage_connection_id: storageConnectionId,
        storage_path: selectedFolder,
        subscription_tier: 'basic',
        storage_quota_gb: 10,
        projects_limit: 50,
      };
      const res = await axios.post('/api/companies', payload);
      console.log('Company created:', res.data);
    } catch (err) {
      console.error('Failed to create company:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto', p: 3 }}>
      <h2>Создание новой компании</h2>

      <TextField
        fullWidth
        label="Название компании"
        value={companyName}
        onChange={(e) => setCompanyName(e.target.value)}
        sx={{ mb: 2 }}
      />

      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Хранилище</InputLabel>
        <Select
          value={storageProvider}
          label="Хранилище"
          onChange={(e) => setStorageProvider(e.target.value as string)}
        >
          <MenuItem value="yandex_disk">Яндекс Диск</MenuItem>
          <MenuItem value="minio">MinIO</MenuItem>
        </Select>
      </FormControl>

      {storageProvider === 'yandex_disk' && !storageConnectionId && (
        <Box sx={{ mb: 2 }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            Для использования Яндекс Диска необходимо авторизоваться
          </Alert>
          <YandexDiskAuth
            connectionName={`${companyName || 'New Company'} - Yandex Disk`}
            onSuccess={handleYandexAuthSuccess}
          />
        </Box>
      )}

      {storageProvider === 'yandex_disk' && storageConnectionId && (
        <Box sx={{ mb: 2 }}>
          <Alert severity="success" sx={{ mb: 2 }}>
            Яндекс Диск подключён. Выберите папку для хранения данных компании.
          </Alert>
          <Button variant="outlined" onClick={() => setShowFolderPicker(true)}>
            Выбрать папку на Яндекс Диске
          </Button>
          <Box sx={{ mt: 1 }}>
            <strong>Папка:</strong> {selectedFolder || 'не выбрана'}
          </Box>
        </Box>
      )}

      {/* TODO: обработка MinIO (bucket name) при необходимости */}

      <Button
        variant="contained"
        disabled={!companyName || !storageConnectionId || submitting}
        onClick={handleSubmit}
      >
        {submitting ? 'Создание...' : 'Создать компанию'}
      </Button>

      <YandexDiskFolderPicker
        open={showFolderPicker}
        connectionId={storageConnectionId ?? 0}
        onClose={() => setShowFolderPicker(false)}
        onSelect={handleFolderSelect}
        initialPath="/"
      />
    </Box>
  );
};
