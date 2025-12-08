import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TablePagination,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Avatar,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { arContentAPI } from '@/services/api';
import { PageHeader, PageContent } from '@/components';
import { useToast } from '@/store/useToast';

interface ARContent {
  id: number;
  title: string;
  portrait_url?: string;
  marker_status: 'pending' | 'processing' | 'ready' | 'failed';
  videos_count: number;
  views: number;
  unique_id: string;
  created_at: string;
}

export default function ARContentList() {
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();
  const { showToast } = useToast();

  const [content, setContent] = useState<ARContent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState('');
  const [markerFilter, setMarkerFilter] = useState<'all' | 'pending' | 'processing' | 'ready' | 'failed'>('all');
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  // Fetch AR content (mock data for now)
  useEffect(() => {
    const fetchContent = async () => {
      try {
        setLoading(true);
        // TODO: Replace with actual API call when endpoint is ready
        // const response = await arContentAPI.list(parseInt(projectId || '0'));
        // Mock data
        setContent([
          {
            id: 1,
            title: 'Постер #1 - Санта с подарками',
            portrait_url: 'https://via.placeholder.com/50',
            marker_status: 'ready',
            videos_count: 5,
            views: 3245,
            unique_id: 'abc-123-def',
            created_at: '2025-01-08',
          },
          {
            id: 2,
            title: 'Ёлка на станде',
            portrait_url: 'https://via.placeholder.com/50',
            marker_status: 'processing',
            videos_count: 3,
            views: 1892,
            unique_id: 'xyz-456-uvw',
            created_at: '2025-01-07',
          },
          {
            id: 3,
            title: 'Подарки в величине',
            portrait_url: 'https://via.placeholder.com/50',
            marker_status: 'failed',
            videos_count: 0,
            views: 0,
            unique_id: 'pqr-789-stu',
            created_at: '2025-01-06',
          },
        ]);
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Ошибка загружки контента');
        console.error('Failed to fetch AR content:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, [projectId]);

  // Filter content
  const filteredContent = content.filter((item) => {
    const matchesSearch = item.title.toLowerCase().includes(search.toLowerCase()) ||
                          item.unique_id.toLowerCase().includes(search.toLowerCase());
    const matchesMarker = markerFilter === 'all' || item.marker_status === markerFilter;
    return matchesSearch && matchesMarker;
  });

  // Paginate
  const paginatedContent = filteredContent.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleDeleteContent = async (id: number) => {
    try {
      await arContentAPI.delete(id);
      setContent(content.filter((c) => c.id !== id));
      setDeleteConfirm(null);
      showToast('AR контент удален', 'success');
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Ошибка удаления', 'error');
    }
  };

  const getMarkerStatusChip = (status: string) => {
    const statusMap: { [key: string]: { label: string; color: any } } = {
      pending: { label: '⏳ Pending', color: 'default' },
      processing: { label: '🔄 Processing', color: 'info' },
      ready: { label: '✅ Ready', color: 'success' },
      failed: { label: '❌ Failed', color: 'error' },
    };
    const s = statusMap[status] || { label: status, color: 'default' };
    return <Chip label={s.label} color={s.color} size="small" />;
  };

  const formatNumber = (num: number) => new Intl.NumberFormat('ru-RU').format(num);

  if (loading) {
    return (
      <PageContent>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
          <CircularProgress />
        </Box>
      </PageContent>
    );
  }

  return (
    <PageContent>
      <PageHeader
        title="AR Контент"
        subtitle="управление нарисованным контентом"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/ar-content/new')}
          >
            Новый контент
          </Button>
        }
      />

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3, display: 'flex', gap: 2, alignItems: 'flex-end' }}>
        <TextField
          label="Поиск по заголовку или ID"
          size="small"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 250 }}
        />
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Маркер</InputLabel>
          <Select
            value={markerFilter}
            label="Маркер"
            onChange={(e) => {
              setMarkerFilter(e.target.value as any);
              setPage(0);
            }}
          >
            <MenuItem value="all">Все</MenuItem>
            <MenuItem value="pending">Pending</MenuItem>
            <MenuItem value="processing">Processing</MenuItem>
            <MenuItem value="ready">Ready</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
          </Select>
        </FormControl>
      </Paper>

      {/* Table */}
      <Paper sx={{ overflow: 'auto' }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell width={60}>Портрет</TableCell>
              <TableCell>Название</TableCell>
              <TableCell>Маркер</TableCell>
              <TableCell align="center">Видео</TableCell>
              <TableCell align="center">Просмотры</TableCell>
              <TableCell>ID</TableCell>
              <TableCell align="right">Действия</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedContent.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 3 }}>
                  <Typography color="textSecondary">Контент не найден</Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedContent.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>
                    <Avatar
                      src={item.portrait_url}
                      sx={{ width: 40, height: 40 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography
                      sx={{ cursor: 'pointer', color: '#1976d2', '&:hover': { textDecoration: 'underline' } }}
                      onClick={() => navigate(`/ar-content/${item.id}`)}
                    >
                      {item.title}
                    </Typography>
                  </TableCell>
                  <TableCell>{getMarkerStatusChip(item.marker_status)}</TableCell>
                  <TableCell align="center">
                    <Chip label={item.videos_count} size="small" />
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                      {formatNumber(item.views)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="caption"
                      sx={{
                        fontFamily: 'monospace',
                        cursor: 'pointer',
                        '&:hover': { textDecoration: 'underline' },
                      }}
                      onClick={() => {
                        navigator.clipboard.writeText(item.unique_id);
                        showToast('ID скопирован', 'success');
                      }}
                    >
                      {item.unique_id}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/ar-content/${item.id}`)}
                      title="Посмотреть"
                    >
                      <ViewIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/ar-content/${item.id}`)}
                      title="Редактировать"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => setDeleteConfirm(item.id)}
                      title="Удалить"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={filteredContent.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => setRowsPerPage(parseInt(e.target.value, 10))}
          labelRowsPerPage="Строк на странице:"
        />
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirm !== null} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Удалить контент?</DialogTitle>
        <DialogContent>
          <Typography>
            Это действие невозможно отменить. Все видео будут удалены.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Отмена</Button>
          <Button
            onClick={() => deleteConfirm && handleDeleteContent(deleteConfirm)}
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
