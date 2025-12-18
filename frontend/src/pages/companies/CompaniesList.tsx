import { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { Box, Typography, Button, Paper, Table, TableHead, TableBody, TableRow, TableCell, Chip, IconButton, CircularProgress, Alert } from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Folder as FolderIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { companiesAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

interface CompanyListItem {
  id: string;
  name: string;
  contact_email?: string;
  storage_provider: string;
  status: string;
  projects_count: number;
  created_at: string;
}

export default function CompaniesList() {
  const navigate = useNavigate();
  const { addToast } = useToast();

  console.log('CompaniesList component mounted');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<CompanyListItem[]>([]);

  console.log('CompaniesList rendering...');

  useEffect(() => {
    console.log('CompaniesList useEffect triggered');
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        console.log('Загрузка списка компаний...');
        const res = await companiesAPI.list({ page: 1, page_size: 50 });
        console.log('Данные о компаниях получены:', res);
        setItems(res.data?.items || []);
        console.log('Список компаний установлен');
      } catch (err: any) {
        console.error('Ошибка при загрузке компаний:', err);
        console.error('Статус ошибки:', err?.response?.status);
        console.error('Данные ошибки:', err?.response?.data);
        const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to load companies';
        setError(msg);
        addToast(msg, 'error');
      } finally {
        setLoading(false);
        console.log('Загрузка компаний завершена');
      }
    };
    load();
    
    // Cleanup function
    return () => {
      console.log('CompaniesList component unmounting');
    };
  }, [addToast]);

  console.log('CompaniesList rendered with items:', items.length);

  // Log navigation attempts
  const originalNavigate = navigate;
  const navigateWrapper = (to: any, options?: any) => {
    console.log('CompaniesList navigation attempt:', { to, options });
    return originalNavigate(to, options);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Companies</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            console.log('Navigate to /companies/new');
            navigateWrapper('/companies/new');
          }}
        >
          New Company
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : items.length === 0 ? (
          <Typography color="text.secondary">No companies</Typography>
        ) : (
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Contact Email</TableCell>
              <TableCell>Storage Provider</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Projects</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((company) => (
              <TableRow key={company.id} hover>
                <TableCell>
                  <Typography variant="subtitle2">{company.name}</Typography>
                </TableCell>
                <TableCell>{company.contact_email}</TableCell>
                <TableCell>{company.storage_provider || 'Local'}</TableCell>
                <TableCell>
                  <Chip 
                    label={company.status} 
                    size="small" 
                    color={company.status === 'active' ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell>{company.projects_count}</TableCell>
                <TableCell>
                  {company.created_at ? format(new Date(company.created_at), 'dd.MM.yyyy HH:mm') : '—'}
                </TableCell>
                <TableCell>
                  <IconButton 
                    onClick={() => {
                      console.log('Navigate to company edit:', `/companies/${company.id}`);
                      navigateWrapper(`/companies/${company.id}`);
                    }} 
                    size="small" 
                    title="Edit"
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton 
                    onClick={() => {
                      console.log('Navigate to company projects:', `/companies/${company.id}/projects`);
                      navigateWrapper(`/companies/${company.id}/projects`);
                    }} 
                    size="small" 
                    title="Open Projects"
                  >
                    <FolderIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        )}
      </Paper>
    </Box>
  );
}
