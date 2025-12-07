// ARV/frontend/src/pages/Storage.tsx
import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import RefreshIcon from '@mui/icons-material/Refresh';
import { AppLayout } from '@/components/(layout)/AppLayout';
import { PageHeader } from '@/components/(layout)/PageHeader';
import { storageApi } from '@/services/storage';
import { StorageConnectionFormDialog } from '@/components/(forms)/StorageConnectionFormDialog';

const StoragePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [dialogOpen, setDialogOpen] = React.useState<null | 'yandex' | 'minio'>(null);
  const companyId = searchParams.get('company_id');

  const { data, isLoading, refetch } = useQuery(
    ['storage-connections', companyId],
    () => storageApi.list(),
  );

  const connections = data?.data ?? [];

  return (
    <AppLayout>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <PageHeader
          title="Настройки хранилищ"
          subtitle="Подключения локального диска, Яндекс Диска и MinIO"
          backUrl="/settings"
          actions={[
            {
              label: 'Новое подключение Яндекс Диск',
              variant: 'outlined',
              onClick: () => setDialogOpen('yandex'),
            },
            {
              label: 'Новое подключение MinIO',
              variant: 'contained',
              onClick: () => setDialogOpen('minio'),
            },
          ]}
        />

        <Paper sx={{ mb: 2 }}>
          {isLoading && <LinearProgress />}
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Название</TableCell>
                  <TableCell>Провайдер</TableCell>
                  <TableCell>Базовый путь</TableCell>
                  <TableCell>Статус</TableCell>
                  <TableCell>По умолчанию</TableCell>
                  <TableCell align="right">Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {connections.length === 0 && !isLoading && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="text.secondary">
                        Подключения хранилищ не настроены
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {connections.map((c: any) => (
                  <TableRow key={c.id} hover>
                    <TableCell>{c.name}</TableCell>
                    <TableCell>{c.provider_human}</TableCell>
                    <TableCell>{c.base_path}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={c.is_active ? 'Активно' : 'Отключено'}
                        color={c.is_active ? 'success' : 'default'}
                      />
                      {c.test_status && (
                        <Chip
                          size="small"
                          sx={{ ml: 1 }}
                          label={c.test_status === 'success' ? 'OK' : 'Ошибка'}
                          color={c.test_status === 'success' ? 'success' : 'error'}
                          variant="outlined"
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      {c.is_default && (
                        <Chip
                          size="small"
                          label="По умолчанию"
                          color="primary"
                          variant="outlined"
                        />
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() =>
                          setDialogOpen(c.provider === 'yandex_disk' ? 'yandex' : 'minio')
                        }
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => storageApi.test(c.id).then(() => refetch())}
                      >
                        <RefreshIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>

        {/* Диалог создания/редактирования подключения */}
        {dialogOpen && (
          <StorageConnectionFormDialog
            provider={dialogOpen}
            open={!!dialogOpen}
            onClose={() => setDialogOpen(null)}
            onSuccess={() => {
              setDialogOpen(null);
              refetch();
            }}
          />
        )}
      </Container>
    </AppLayout>
  );
};

export default StoragePage;
