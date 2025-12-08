import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Grid,
  LinearProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Cloud as CloudIcon,
} from '@mui/icons-material';
import { PageHeader, PageContent } from '@/components';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { useToast } from '@/store/useToast';

const COLORS = ['#1976d2', '#2e7d32', '#ed6c02', '#d32f2f'];

interface StorageConnection {
  id: number;
  provider: 'local' | 'minio' | 'yandex_disk';
  status: 'connected' | 'failed';
  used_gb: number;
  total_gb: number;
  companies_count: number;
}

export default function Storage() {
  const { showToast } = useToast();
  const [connections, setConnections] = useState<StorageConnection[]>([
    {
      id: 1,
      provider: 'local',
      status: 'connected',
      used_gb: 125,
      total_gb: 250,
      companies_count: 1,
    },
    {
      id: 2,
      provider: 'minio',
      status: 'connected',
      used_gb: 100,
      total_gb: 500,
      companies_count: 10,
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  const breakdownData = [
    { name: 'Видео', value: 60 },
    { name: 'Маркеры', value: 20 },
    { name: 'Портреты', value: 15 },
    { name: 'QR-коды', value: 5 },
  ];

  const totalUsed = connections.reduce((sum, c) => sum + c.used_gb, 0);
  const totalCapacity = connections.reduce((sum, c) => sum + c.total_gb, 0);
  const usagePercent = (totalUsed / totalCapacity) * 100;

  const handleDeleteConnection = (id: number) => {
    setConnections(connections.filter((c) => c.id !== id));
    setDeleteConfirm(null);
    showToast('Хранилище удалено', 'success');
  };

  const getStatusChip = (status: string) => {
    return (
      <Chip
        label={status === 'connected' ? '✅ Connected' : '❌ Failed'}
        color={status === 'connected' ? 'success' : 'error'}
        size="small"
      />
    );
  };

  const getProviderLabel = (provider: string) => {
    const labels: { [key: string]: string } = {
      local: '💾 Local Disk',
      minio: 'MinIO S3',
      yandex_disk: '🔗 Yandex Disk',
    };
    return labels[provider] || provider;
  };

  return (
    <PageContent>
      <PageHeader
        title="Управление хранилищами"
        subtitle="Конфигурация и мониторинг хранилищ данных"
        actions={
          <Button variant="contained" startIcon={<AddIcon />}>
            Добавить хранилище
          </Button>
        }
      />

      {/* Overview */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              📊 Общая статистика
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2">Использовано хранилища</Typography>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="textSecondary">
                  {totalUsed.toFixed(1)} GB
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  {totalCapacity.toFixed(1)} GB
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={Math.min(usagePercent, 100)}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: '#e0e0e0',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 4,
                    backgroundColor: usagePercent > 80 ? '#d32f2f' : '#1976d2',
                  },
                }}
              />
              <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                {usagePercent.toFixed(1)}% заполнено
              </Typography>
            </Box>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              📁 Распределение по типам
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={breakdownData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={60}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {breakdownData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Connections Table */}
      <Paper sx={{ overflow: 'auto' }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell>Провайдер</TableCell>
              <TableCell>Статус</TableCell>
              <TableCell align="right">Использовано</TableCell>
              <TableCell align="center">Компаний</TableCell>
              <TableCell align="right">Действия</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {connections.map((connection) => (
              <TableRow key={connection.id} hover>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CloudIcon />
                    <Typography>{getProviderLabel(connection.provider)}</Typography>
                  </Box>
                </TableCell>
                <TableCell>{getStatusChip(connection.status)}</TableCell>
                <TableCell align="right">
                  <Typography variant="body2">
                    {connection.used_gb} GB / {connection.total_gb} GB
                  </Typography>
                  <Typography variant="caption" color="textSecondary">
                    ({((connection.used_gb / connection.total_gb) * 100).toFixed(1)}%)
                  </Typography>
                </TableCell>
                <TableCell align="center">{
 connection.companies_count}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" title="Проверить">
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => setDeleteConfirm(connection.id)}
                    title="Удалить"
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      {/* Delete Dialog */}
      <Dialog open={deleteConfirm !== null} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Удалить хранилище?</DialogTitle>
        <DialogContent>
          <Typography>
            ⚠️ Это хранилище все еще используется некоторыми компаниями. Убедитесь, что они перенесены на другое хранилище.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Отмена</Button>
          <Button
            onClick={() => deleteConfirm && handleDeleteConnection(deleteConfirm)}
            color="error"
            variant="contained"
          >
            Удалить
          </Button>
        </DialogActions>
      </Dialog>
    </PageContent>
  );
}
