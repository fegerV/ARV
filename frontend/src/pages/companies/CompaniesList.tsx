import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  MoreVert as MoreIcon,
} from '@mui/icons-material';
import { companiesAPI } from '@/services/api';
import { PageHeader, PageContent } from '@/components';
import { useToast } from '@/store/useToast';

interface Company {
  id: number;
  name: string;
  slug: string;
  status: 'active' | 'expiring' | 'expired';
  subscription_tier: string;
  expiry_date: string;
  contact_email: string;
}

export default function CompaniesList() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'expiring' | 'expired'>('all');
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  // Fetch companies
  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        setLoading(true);
        const response = await companiesAPI.list();
        setCompanies(response.data);
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Ошибка загрузки компаний');
        console.error('Failed to fetch companies:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchCompanies();
  }, []);

  // Filter companies
  const filteredCompanies = companies.filter((company) => {
    const matchesSearch =
      company.name.toLowerCase().includes(search.toLowerCase()) ||
      company.slug.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || company.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Paginate
  const paginatedCompanies = filteredCompanies.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleDeleteCompany = async (id: number) => {
    try {
      await companiesAPI.delete(id);
      setCompanies(companies.filter((c) => c.id !== id));
      setDeleteConfirm(null);
      showToast('Компания удалена', 'success');
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Ошибка удаления', 'error');
    }
  };

  const getStatusChip = (status: string) => {
    const statusMap: { [key: string]: { label: string; color: any } } = {
      active: { label: '⭐ Active', color: 'success' },
      expiring: { label: '⚠️ Expiring', color: 'warning' },
      expired: { label: '❌ Expired', color: 'error' },
    };
    const s = statusMap[status] || { label: status, color: 'default' };
    return <Chip label={s.label} color={s.color} size="small" />;
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
        title="Компании"
        subtitle="Управление клиентскими компаниями"
        actions={
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => navigate('/companies/new')}>
            Новая компания
          </Button>
        }
      />

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3, display: 'flex', gap: 2, alignItems: 'flex-end' }}>
        <TextField
          label="Поиск по имени или slug"
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
            <MenuItem value="expiring">Expiring</MenuItem>
            <MenuItem value="expired">Expired</MenuItem>
          </Select>
        </FormControl>
      </Paper>

      {/* Table */}
      <Paper sx={{ overflow: 'auto' }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell>Имя</TableCell>
              <TableCell>Slug</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Статус</TableCell>
              <TableCell>Срок действия</TableCell>
              <TableCell align="right">Действия</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedCompanies.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                  <Typography color="textSecondary">Компании не найдены</Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedCompanies.map((company) => (
                <TableRow key={company.id} hover>
                  <TableCell>
                    <Typography
                      sx={{ cursor: 'pointer', color: '#1976d2', '&:hover': { textDecoration: 'underline' } }}
                      onClick={() => navigate(`/companies/${company.id}`)}
                    >
                      {company.name}
                    </Typography>
                  </TableCell>
                  <TableCell>{company.slug}</TableCell>
                  <TableCell>{company.contact_email}</TableCell>
                  <TableCell>{getStatusChip(company.status)}</TableCell>
                  <TableCell>{formatDate(company.expiry_date)}</TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => navigate(`/companies/${company.id}`)}
                      title="Редактировать"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => setDeleteConfirm(company.id)}
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
          count={filteredCompanies.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => setRowsPerPage(parseInt(e.target.value, 10))}
          labelRowsPerPage="Строк на странице:"
        />
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirm !== null} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Удалить компанию?</DialogTitle>
        <DialogContent>
          <Typography>
            Это действие невозможно отменить. Все проекты и контент будут удалены.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Отмена</Button>
          <Button
            onClick={() => deleteConfirm && handleDeleteCompany(deleteConfirm)}
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
