// components/forms/StorageConnectionForm.tsx
import React, { useState } from 'react';
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
} from '@mui/material';
import { useForm, Controller } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { storageApi, StorageConnectionCreate, StorageConnectionUpdate } from '@/services/storage';
import { StorageConnection, StorageProvider } from '@/types/storage';
import { YandexOAuthButton } from '@/components/(forms)/YandexOAuthButton';

const schema = z.discriminatedUnion('provider', [
  z.object({
    provider: z.literal('yandex_disk'),
    name: z.string().min(3, 'Название должно содержать минимум 3 символа'),
    base_path: z.string().min(1, 'Базовый путь обязателен'),
    yandex_folder: z.string().min(1, 'Папка на Яндекс.Диске обязательна'),
  }),
  z.object({
    provider: z.literal('minio'),
    name: z.string().min(3, 'Название должно содержать минимум 3 символа'),
    base_path: z.string().min(1, 'Базовый путь обязателен'),
    endpoint: z.string().url('Неверный формат URL').min(1, 'Endpoint обязателен'),
    bucket: z.string().min(1, 'Bucket обязателен'),
    region: z.string().optional(),
    access_key: z.string().min(1, 'Access key обязателен'),
    secret_key: z.string().min(1, 'Secret key обязателен'),
  }),
]);

type FormValues = z.infer<typeof schema>;

interface StorageConnectionFormProps {
  defaultProvider?: 'yandex_disk' | 'minio';
  initialData?: StorageConnection;
  onSuccess: () => void;
}

export const StorageConnectionForm: React.FC<StorageConnectionFormProps> = ({
  defaultProvider = 'yandex_disk',
  initialData,
  onSuccess,
}) => {
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message?: string } | null>(null);
  const [oauthDialogOpen, setOauthDialogOpen] = useState(false);
  const [createdConnectionId, setCreatedConnectionId] = useState<number | null>(null);

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      provider: initialData?.provider as 'yandex_disk' | 'minio' || defaultProvider,
      name: initialData?.name || '',
      base_path: initialData?.base_path || '/clients',
      yandex_folder: initialData?.yandex_folder || '',
      endpoint: initialData?.endpoint || '',
      bucket: initialData?.bucket || '',
      region: initialData?.region || '',
      access_key: initialData?.access_key || '',
      secret_key: '', // Never pre-fill secret key
    },
  });

  const provider = watch('provider');

  const onSubmit = async (values: FormValues) => {
    try {
      if (initialData) {
        // Update existing connection
        const updateData: StorageConnectionUpdate = {
          name: values.name,
          base_path: values.base_path,
        };

        if (values.provider === 'yandex_disk') {
          updateData.yandex_folder = values.yandex_folder;
        } else if (values.provider === 'minio') {
          updateData.endpoint = values.endpoint;
          updateData.bucket = values.bucket;
          updateData.region = values.region;
          updateData.access_key = values.access_key;
          if (values.secret_key) {
            updateData.secret_key = values.secret_key;
          }
        }

        await storageApi.update(initialData.id, updateData);
      } else {
        // Create new connection
        const createData: StorageConnectionCreate = {
          name: values.name,
          provider: values.provider,
          base_path: values.base_path,
        };

        if (values.provider === 'yandex_disk') {
          createData.yandex_folder = values.yandex_folder;
        } else if (values.provider === 'minio') {
          createData.endpoint = values.endpoint;
          createData.bucket = values.bucket;
          createData.region = values.region;
          createData.access_key = values.access_key;
          createData.secret_key = values.secret_key;
        }

        const response = await storageApi.create(createData);
        setCreatedConnectionId(response.data.id);
      }

      onSuccess();
    } catch (error) {
      console.error('Error saving storage connection:', error);
    }
  };

  const handleTestConnection = async () => {
    if (!createdConnectionId) return;

    setIsTesting(true);
    setTestResult(null);

    try {
      const response = await storageApi.test(createdConnectionId);
      setTestResult(response.data);
    } catch (error: any) {
      setTestResult({
        success: false,
        message: error.response?.data?.detail || 'Ошибка при тестировании подключения',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleYandexOAuthSuccess = (connectionId: number, folderPath: string) => {
    setCreatedConnectionId(connectionId);
    setValue('yandex_folder', folderPath);
    setOauthDialogOpen(false);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Controller
        name="provider"
        control={control}
        render={({ field }) => (
          <FormControl fullWidth sx={{ mb: 2 }} disabled={!!initialData}>
            <InputLabel>Провайдер</InputLabel>
            <Select {...field} label="Провайдер">
              <MenuItem value="yandex_disk">Яндекс Диск</MenuItem>
              <MenuItem value="minio">MinIO</MenuItem>
            </Select>
          </FormControl>
        )}
      />

      <Controller
        name="name"
        control={control}
        render={({ field, fieldState }) => (
          <TextField
            {...field}
            label="Название подключения"
            placeholder="Мое хранилище"
            error={!!fieldState.error}
            helperText={fieldState.error?.message}
            fullWidth
            sx={{ mb: 2 }}
          />
        )}
      />

      <Controller
        name="base_path"
        control={control}
        render={({ field, fieldState }) => (
          <TextField
            {...field}
            label="Базовый путь"
            placeholder="/clients"
            error={!!fieldState.error}
            helperText={fieldState.error?.message || 'Базовый путь для хранения файлов клиентов'}
            fullWidth
            sx={{ mb: 2 }}
          />
        )}
      />

      {provider === 'yandex_disk' && (
        <>
          <Controller
            name="yandex_folder"
            control={control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                label="Папка на Яндекс.Диске"
                placeholder="/VertexAR/Clients/Demo"
                error={!!fieldState.error}
                helperText={fieldState.error?.message || 'Файлы клиента будут в этой папке'}
                fullWidth
                sx={{ mb: 2 }}
                InputProps={{
                  readOnly: !!initialData,
                }}
              />
            )}
          />
          
          {!initialData && (
            <Button
              variant="contained"
              onClick={() => setOauthDialogOpen(true)}
              sx={{ mb: 2 }}
            >
              Подключить через Яндекс OAuth
            </Button>
          )}
        </>
      )}

      {provider === 'minio' && (
        <>
          <Controller
            name="endpoint"
            control={control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                label="Endpoint MinIO"
                placeholder="https://minio.example.com"
                error={!!fieldState.error}
                helperText={fieldState.error?.message}
                fullWidth
                sx={{ mb: 2 }}
              />
            )}
          />
          <Controller
            name="bucket"
            control={control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                label="Bucket"
                placeholder="vertex-ar"
                error={!!fieldState.error}
                helperText={fieldState.error?.message}
                fullWidth
                sx={{ mb: 2 }}
              />
            )}
          />
          <Controller
            name="region"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Region"
                placeholder="us-east-1"
                fullWidth
                sx={{ mb: 2 }}
              />
            )}
          />
          <Controller
            name="access_key"
            control={control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                label="Access key"
                error={!!fieldState.error}
                helperText={fieldState.error?.message}
                fullWidth
                sx={{ mb: 2 }}
              />
            )}
          />
          <Controller
            name="secret_key"
            control={control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                type="password"
                label={initialData ? "Новый Secret key (оставьте пустым, чтобы не менять)" : "Secret key"}
                error={!!fieldState.error}
                helperText={fieldState.error?.message}
                fullWidth
                sx={{ mb: 2 }}
              />
            )}
          />
        </>
      )}

      {errors.root && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errors.root.message}
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
        <Button
          type="submit"
          variant="contained"
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={20} /> : null}
        >
          {initialData ? 'Сохранить изменения' : 'Создать подключение'}
        </Button>

        {createdConnectionId && (
          <Button
            variant="outlined"
            onClick={handleTestConnection}
            disabled={isTesting}
            startIcon={isTesting ? <CircularProgress size={20} /> : null}
          >
            Протестировать подключение
          </Button>
        )}
      </Box>

      {testResult && (
        <Alert
          severity={testResult.success ? 'success' : 'error'}
          sx={{ mt: 2 }}
        >
          {testResult.message || (testResult.success ? 'Подключение успешно протестировано' : 'Ошибка подключения')}
        </Alert>
      )}

      <Dialog open={oauthDialogOpen} onClose={() => setOauthDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Подключение через Яндекс OAuth</DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 2 }}>
            Нажмите кнопку ниже, чтобы авторизоваться через Яндекс и выбрать папку для подключения.
          </Typography>
          <YandexOAuthButton
            connectionName={watch('name') || 'New Yandex Storage'}
            onSuccess={handleYandexOAuthSuccess}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOauthDialogOpen(false)}>Отмена</Button>
        </DialogActions>
      </Dialog>
    </form>
  );
};