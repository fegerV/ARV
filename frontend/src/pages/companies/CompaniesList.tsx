import { useEffect, useState } from 'react';
import { Box, Typography, Button, Paper, Table, TableHead, TableBody, TableRow, TableCell, Chip, IconButton, CircularProgress } from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Folder as FolderIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { companiesAPI } from '../../services/api';

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

  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<CompanyListItem[]>([]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await companiesAPI.list({ page: 1, page_size: 50 });
        setItems(res.data?.items || []);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

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
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
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
                <TableCell>{company.created_at}</TableCell>
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
