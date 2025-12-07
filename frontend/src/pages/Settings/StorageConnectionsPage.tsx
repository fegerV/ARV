// pages/Settings/StorageConnectionsPage.tsx
import React, { useState } from 'react';
import {
  Container,
  Typography,
  Button,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Cloud as CloudIcon,
  Storage as StorageIcon,
  Folder as FolderIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { StorageConnection } from '@/types/storage';
import { storageApi } from '@/services/storage';
import { StorageConnectionForm } from '@/components/forms/StorageConnectionForm';

const StorageConnectionsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [openForm, setOpenForm] = useState<false | 'yandex_disk' | 'minio' | StorageConnection>(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const { data: connections, isLoading, refetch } = useQuery<StorageConnection[]>(
    ['storage-connections'],
    storageApi.list
  );

  const deleteMutation = useMutation(
    (id: number) => storageApi.delete(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['storage-connections']);
        setSnackbar({
          open: true,
          message: 'Подключение успешно удалено',
          severity: 'success',
        });
      },
      onError: () => {
        setSnackbar({
          open: true,
          message: 'Ошибка при удалении подключения',
          severity: 'error',
        });
      },
    }
  );

  const handleDelete = (id: number, name: string) => {
    if (window.confirm(`Вы уверены, что хотите удалить подключение "${name}"?`)) {
      deleteMutation.mutate(id);
    }
  };

  const handleCloseForm = () => {
    setOpenForm(false);
  };

  const handleSuccess = () => {
    handleCloseForm();
    refetch();
    setSnackbar({
      open: true,
      message: 'Подключение успешно сохранено',
      severity: 'success',
    });
  };

  const getStatusIcon = (isActive: boolean) => {
    return isActive ? (
      <CheckCircleIcon color="success" />
    ) : (
      <CancelIcon color="error" />
    );
  };

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'yandex_disk':
        return <CloudIcon />;
      case 'minio':
        return <StorageIcon />;
      default:
        return <FolderIcon />;
    }
  };

  const getProviderName = (provider: string) => {
    switch (provider) {
      case 'yandex_disk':
        return 'Яндекс Диск';
      case 'minio':
        return 'MinIO';
      case 'local_disk':
        return 'Локальное хранилище';
      default:
        return provider;
    }
  };

  return (
    <Container maxWidth={false}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Подключения хранилищ</Typography>
        <Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenForm('yandex_disk')}
            sx={{ mr: 2 }}
          >
            Новое подключение Яндекс Диск
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenForm('minio')}
          >
            Новое подключение MinIO
          </Button>
        </Box>
      </Box>

      {isLoading ? (
        <Typography>Загрузка...</Typography>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Название</TableCell>
                <TableCell>Провайдер</TableCell>
                <TableCell>Базовый путь</TableCell>
                <TableCell>Доп. информация</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Действия</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {connections?.map((connection) => (
                <TableRow key={connection.id}>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      {getProviderIcon(connection.provider)}
                      <Box sx={{ ml: 1 }}>
                        {connection.name}
                        {connection.is_default && (
                          <Chip
                            label="По умолчанию"
                            size="small"
                            sx={{ ml: 1 }}
                          />
                        )}
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>{getProviderName(connection.provider)}</TableCell>
                  <TableCell>{connection.base_path}</TableCell>
                  <TableCell>
                    {connection.provider === 'yandex_disk' && connection.yandex_folder && (
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <FolderIcon sx={{ fontSize: 16, mr: 1 }} />
                        {connection.yandex_folder}
                      </Box>
                    )}
                    {connection.provider === 'minio' && connection.bucket && (
                      <Box>
                        Bucket: {connection.bucket}
                        {connection.endpoint && <div>Endpoint: {connection.endpoint}</div>}
                      </Box>
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      {getStatusIcon(connection.is_active)}
                      <span style={{ marginLeft: 8 }}>
                        {connection.is_active ? 'Активно' : 'Неактивно'}
                      </span>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Редактировать">
                      <IconButton
                        onClick={() => setOpenForm(connection)}
                        disabled={connection.is_default}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Удалить">
                      <IconButton
                        onClick={() => handleDelete(connection.id, connection.name)}
                        disabled={connection.is_default}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog
        open={!!openForm}
        onClose={handleCloseForm}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {typeof openForm === 'object'
            ? `Редактировать подключение: ${openForm.name}`
            : openForm === 'yandex_disk'
            ? 'Новое подключение Яндекс Диск'
            : 'Новое подключение MinIO'}
        </DialogTitle>
        <DialogContent>
          {(openForm === 'yandex_disk' || openForm === 'minio' || typeof openForm === 'object') && (
            <StorageConnectionForm
              defaultProvider={
                typeof openForm === 'object' ? openForm.provider as 'yandex_disk' | 'minio' : openForm
              }
              initialData={typeof openForm === 'object' ? openForm : undefined}
              onSuccess={handleSuccess}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseForm}>Отмена</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default StorageConnectionsPage;