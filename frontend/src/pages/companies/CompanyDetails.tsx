import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { format } from 'date-fns';
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Grid,
  Chip,
  Divider,
} from '@mui/material';
import { ArrowBack as BackIcon, Folder as FolderIcon } from '@mui/icons-material';
import { companiesAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

interface CompanyDetail {
  id: string;
  name: string;
  contact_email?: string;
  storage_provider: string;
  status: string;
  projects_count: number;
  ar_content_count: number;
  created_at: string;
}

export default function CompanyDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [company, setCompany] = useState<CompanyDetail | null>(null);

  const load = useCallback(async () => {
    if (!id) {
      setError('Company id is missing');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await companiesAPI.get(id);
      setCompany(res.data as CompanyDetail);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to load company';
      setError(msg);
      addToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  }, [id, addToast]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button startIcon={<BackIcon />} variant="outlined" onClick={() => navigate('/companies')}>
            Back
          </Button>
          <Typography variant="h4">Company Details</Typography>
        </Box>
        <Button
          startIcon={<FolderIcon />}
          variant="contained"
          onClick={() => {
            if (!id) return;
            navigate(`/companies/${id}/projects`);
          }}
          disabled={!id}
        >
          Projects
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : !company ? (
          <Typography color="text.secondary">Company not found</Typography>
        ) : (
          <>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2, flexWrap: 'wrap' }}>
              <Box>
                <Typography variant="h5" sx={{ mb: 0.5 }}>
                  {company.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  ID: {company.id}
                </Typography>
              </Box>

              <Chip
                label={company.status}
                color={company.status === 'active' ? 'success' : 'default'}
                variant="outlined"
              />
            </Box>

            <Divider sx={{ my: 2 }} />

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">Contact Email</Typography>
                <Typography>{company.contact_email || '—'}</Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">Storage Provider</Typography>
                <Typography>{company.storage_provider || 'Local'}</Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">Projects</Typography>
                <Typography>{company.projects_count}</Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">AR Content</Typography>
                <Typography>{company.ar_content_count}</Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">Created</Typography>
                <Typography>
                  {company.created_at ? format(new Date(company.created_at), 'dd.MM.yyyy HH:mm') : '—'}
                </Typography>
              </Grid>
            </Grid>
          </>
        )}
      </Paper>
    </Box>
  );
}
