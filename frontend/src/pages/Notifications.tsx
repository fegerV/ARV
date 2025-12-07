// ARV/frontend/src/pages/Notifications.tsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Container,
  Paper,
  Typography,
  Chip,
  IconButton,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  MenuItem,
  Tooltip,
} from '@mui/material';
import MarkEmailReadIcon from '@mui/icons-material/MarkEmailRead';
import RefreshIcon from '@mui/icons-material/Refresh';
import { AppLayout } from '@/components/(layout)/AppLayout';
import { PageHeader } from '@/components/(layout)/PageHeader';
import { notificationsApi } from '@/services/notifications';

const NotificationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = React.useState(0);
  const [limit, setLimit] = React.useState(25);
  const [type, setType] = React.useState<string>('');
  const [status, setStatus] = React.useState<string>('');

  const { data, isLoading, refetch } = useQuery(
    ['notifications', { page, limit, type, status }],
    () =>
      notificationsApi.list({
        page: page + 1,
        limit,
        type: type || undefined,
        status: status || undefined,
      })
  );

  const notifications = data?.data.notifications ?? [];
  const total = data?.data.total ?? 0;

  const handlePageChange = (_: unknown, newPage: number) => setPage(newPage);
  const handleRowsPerPageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLimit(parseInt(e.target.value, 10));
    setPage(0);
  };

  const handleMarkRead = async (id?: number) => {
    if (id) {
      await notificationsApi.markRead(id);
    } else {
      await notificationsApi.markAllRead();
    }
    refetch();
  };

  const typeColor = (t: string) =>
    t === 'error' ? 'error' : t === 'warning' ? 'warning' : t === 'success' ? 'success' : 'default';

  return (
    <AppLayout>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <PageHeader
          title="Центр уведомлений"
          subtitle="События системы, статусы задач и ошибки"
          backUrl="/"
          actions={[
            {
              label: 'Отметить всё прочитанным',
              variant: 'outlined',
              onClick: () => handleMarkRead(),
            },
          ]}
        />

        {/* Фильтры */}
        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <TextField
              select
              size="small"
              label="Тип"
              value={type}
              onChange={(e) => {
                setType(e.target.value);
                setPage(0);
              }}
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="">Все</MenuItem>
              <MenuItem value="info">Информация</MenuItem>
              <MenuItem value="success">Успех</MenuItem>
              <MenuItem value="warning">Предупреждение</MenuItem>
              <MenuItem value="error">Ошибка</MenuItem>
            </TextField>
            <TextField
              select
              size="small"
              label="Статус"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(0);
              }}
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="">Все</MenuItem>
              <MenuItem value="unread">Непрочитанные</MenuItem>
              <MenuItem value="read">Прочитанные</MenuItem>
            </TextField>
            <Box sx={{ flexGrow: 1 }} />
            <IconButton onClick={() => refetch()}>
              <RefreshIcon />
            </IconButton>
          </Box>
        </Paper>

        {/* Таблица уведомлений */}
        <Paper>
          {isLoading && <LinearProgress />}
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Сообщение</TableCell>
                  <TableCell>Тип</TableCell>
                  <TableCell>Компания</TableCell>
                  <TableCell>Объект</TableCell>
                  <TableCell>Создано</TableCell>
                  <TableCell align="right">Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {notifications.length === 0 && !isLoading && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="text.secondary">
                        Уведомлений нет
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {notifications.map((n: any) => (
                  <TableRow
                    key={n.id}
                    hover
                    sx={{
                      cursor: n.target_url ? 'pointer' : 'default',
                      bgcolor: !n.is_read ? 'action.hover' : undefined,
                    }}
                    onClick={() => n.target_url && navigate(n.target_url)}
                  >
                    <TableCell>
                      <Typography fontWeight={n.is_read ? 400 : 600}>
                        {n.title}
                      </Typography>
                      {n.message && (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          noWrap
                        >
                          {n.message}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={n.type_human}
                        color={typeColor(n.type)}
                      />
                    </TableCell>
                    <TableCell>{n.company_name || '—'}</TableCell>
                    <TableCell>{n.object_human || '—'}</TableCell>
                    <TableCell>{n.created_at_readable}</TableCell>
                    <TableCell align="right">
                      {!n.is_read && (
                        <Tooltip title="Отметить прочитанным">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMarkRead(n.id);
                            }}
                          >
                            <MarkEmailReadIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, newPage) => handlePageChange(_, newPage)}
            rowsPerPage={limit}
            onRowsPerPageChange={handleRowsPerPageChange}
            rowsPerPageOptions={[10, 25, 50]}
          />
        </Paper>
      </Container>
    </AppLayout>
  );
};

export default NotificationsPage;
