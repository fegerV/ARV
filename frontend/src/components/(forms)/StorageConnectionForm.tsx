// components/(forms)/StorageConnectionForm.tsx
import React, { useState } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Typography, 
  FormControl, 
  RadioGroup, 
  Radio,
  TextField,
  Alert,
  CircularProgress
} from '@mui/material';
import { YandexOAuthButton } from './YandexOAuthButton';

interface StorageConnectionFormProps {
  onConnectionSelect: (connectionId: number, storagePath: string) => void;
  disabled?: boolean;
}

export const StorageConnectionForm: React.FC<StorageConnectionFormProps> = ({
  onConnectionSelect,
  disabled
}) => {
  const [provider, setProvider] = useState<'local_disk' | 'yandex_disk'>('local_disk');
  const [connectionId, setConnectionId] = useState<number>(1); // Default local
  const [storagePath, setStoragePath] = useState('');
  const [loading, setLoading] = useState(false);
  const [connectionName, setConnectionName] = useState('Demo Storage');

  const handleYandexSuccess = (id: number, path: string) => {
    setConnectionId(id);
    setStoragePath(path);
    onConnectionSelect(id, path);
  };

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Хранилище файлов
        </Typography>
        
        <FormControl fullWidth sx={{ mb: 3 }}>
          <RadioGroup
            value={provider}
            onChange={(e) => setProvider(e.target.value as any)}
          >
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
              <Radio value="local_disk" />
              <Box>
                <Typography>Локальное хранилище Vertex AR</Typography>
                <Typography variant="body2" color="text.secondary">
                  Файлы хранятся на сервере Vertex AR (демо)
                </Typography>
              </Box>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
              <Radio value="yandex_disk" />
              <Box>
                <Typography>Яндекс.Диск (OAuth)</Typography>
                <Typography variant="body2" color="text.secondary">
                  Подключите Яндекс.Диск клиента
                </Typography>
              </Box>
            </Box>
          </RadioGroup>
        </FormControl>

        {provider === 'local_disk' && (
          <Alert severity="info">
            Локальное хранилище уже подключено (ID: 1)
          </Alert>
        )}

        {provider === 'yandex_disk' && (
          <Box sx={{ mt: 2 }}>
            <TextField
              fullWidth
              label="Название подключения"
              value={connectionName}
              onChange={(e) => setConnectionName(e.target.value)}
              sx={{ mb: 2 }}
            />
            
            <YandexOAuthButton
              connectionName={connectionName}
              onSuccess={handleYandexSuccess}
              disabled={loading}
            />
            
            {storagePath && (
              <Alert severity="success" sx={{ mt: 2 }}>
                ✅ Подключено: {storagePath}
              </Alert>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};