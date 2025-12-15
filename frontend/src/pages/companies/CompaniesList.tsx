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

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<CompanyListItem[]>([]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await companiesAPI.list({ page: 1, page_size: 50 });
        setItems(res.data?.items || []);
      } catch (err: any) {
        const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to load companies';
        setError(msg);
        addToast(msg, 'error');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [addToast]);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Companies</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/companies/new')}
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
                  <IconButton onClick={() => navigate(`/companies/${company.id}`)} size="small" title="Edit">
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton onClick={() => navigate(`/companies/${company.id}/projects`)} size="small" title="Open Projects">
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
