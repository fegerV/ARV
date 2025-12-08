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
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  InfoOutlined as InfoIcon,
} from '@mui/icons-material';
import { projectsAPI, companiesAPI } from '@/services/api';
import { PageHeader, PageContent } from '@/components';
import { useToast } from '@/store/useToast';

interface Project {
  id: number;
  name: string;
  type: string;
  status: 'active' | 'draft' | 'paused' | 'expired';
  expiry_date: string;
  ar_items_count: number;
  views: number;
  created_at: string;
}

interface Company {
  id: number;
  name: string;
}

export default function ProjectsList() {
  const navigate = useNavigate();
  const { companyId } = useParams<{ companyId: string }>();
  const { showToast } = useToast();

  const [projects, setProjects] = useState<Project[]>([]);
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'draft' | 'paused' | 'expired'>('all');
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  // Fetch company and projects
  useEffect(() => {
    const fetchData = async () => {
      if (!companyId) return;
      try {
        setLoading(true);
        const [companyRes, projectsRes] = await Promise.all([
          companiesAPI.get(parseInt(companyId)),
          projectsAPI.list(parseInt(companyId)),
        ]);
        setCompany(companyRes.data);
        setProjects(projectsRes.data);
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Ошибка загружения данных');
        console.error('Failed to fetch data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [companyId]);

  // Filter projects
  const filteredProjects = projects.filter((project) => {
    const matchesSearch = project.name.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || project.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Paginate
  const paginatedProjects = filteredProjects.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleDeleteProject = async (id: number) => {
    try {
      // Assuming there's a DELETE /api/projects/:id endpoint
      // await projectsAPI.delete(id);
      setProjects(projects.filter((p) => p.id !== id));
      setDeleteConfirm(null);
      showToast('Проект удален', 'success');
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Ошибка удаления', 'error');
    }
  };

  const getStatusChip = (status: string) => {
    const statusMap: { [key: string]: { label: string; color: any } } = {
      active: { label: '✅ Active', color: 'success' },
      draft: { label: '📑 Draft', color: 'default' },
      paused: { label: '⏸️ Paused', color: 'info' },
      expired: { label: '❌ Expired', color: 'error' },
    };
    const s = statusMap[status] || { label: status, color: 'default' };
    return <Chip label={s.label} color={s.color} size="small" />;
  };

  const isExpiringSoon = (expiryDate: string) => {
    const days = Math.ceil(
      (new Date(expiryDate).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
    );
    return days >= 0 && days <= 7;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('ru-RU');
  };

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
        title={`Проекты${company ? ` (${company.name})` : ''}`}
        subtitle="Организация проектов и новых каталогов"
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate(`/companies/${companyId}/projects/new`)}
          >
            Новый проект
          </Button>
        }
      />

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3, display: 'flex', gap: 2, alignItems: 'flex-end' }}>
        <TextField
          label="Поиск по имени"
          size="small"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 250 }}
        />
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Статус</InputLabel>
          <Select
            value={statusFilter}
            label="Статус"
            onChange={(e) => {
              setStatusFilter(e.target.value as any);
              setPage(0);
            }}
          >
            <MenuItem value="all">Все</MenuItem>
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="draft">Draft</MenuItem>
            <MenuItem value="paused">Paused</MenuItem>
            <MenuItem value="expired">Expired</MenuItem>
          </Select>
        </FormControl>
      </Paper>

      {/* Table */}
      <Paper sx={{ overflow: 'auto' }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell>Наименование</TableCell>
              <TableCell>Тип</TableCell>
              <TableCell align="center">AR демос</TableCell>
              <TableCell>Статус</TableCell>
              <TableCell>Срок действия</TableCell>
              <TableCell align="right">Действия</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedProjects.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                  <Typography color="textSecondary">Проекты не найдены</Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedProjects.map((project) => (
                <TableRow key={project.id} hover>
                  <TableCell>
                    <Typography
                      sx={{ cursor: 'pointer', color: '#1976d2', '&:hover': { textDecoration: 'underline' } }}
                      onClick={() => navigate(`/projects/${project.id}/content`)}
                    >
                      {project.name}
                    </Typography>
                  </TableCell>
                  <TableCell>{project.type}</TableCell>
                  <TableCell align="center">
                    <Chip label={project.ar_items_count} size="small" />
                  </TableCell>
                  <TableCell>{getStatusChip(project.status)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {formatDate(project.expiry_date)}
                      {isExpiringSoon(project.expiry_date) && (
                        <IconButton size="small" title="Скоро истечет">
                          <InfoIcon fontSize="small" color="warning" />
                        </IconButton>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/projects/${project.id}/content`)}
                      title="Контент"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => setDeleteConfirm(project.id)}
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
          count={filteredProjects.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => setRowsPerPage(parseInt(e.target.value, 10))}
          labelRowsPerPage="Строк на странице:"
        />
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirm !== null} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Удалить проект?</DialogTitle>
        <DialogContent>
          <Typography>
            Это действие невозможно отменить. Все AR-контент будет удален.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Отмена</Button>
          <Button
            onClick={() => deleteConfirm && handleDeleteProject(deleteConfirm)}
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
