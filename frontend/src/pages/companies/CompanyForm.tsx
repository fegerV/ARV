import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  TextField,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { ArrowBack as BackIcon, Save as SaveIcon } from '@mui/icons-material';
import { companiesAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

interface CompanyData {
  name: string;
  contact_email: string;
  status: 'active' | 'inactive';
}

export default function CompanyForm() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<CompanyData>({
    name: '',
    contact_email: '',
    status: 'active',
  });

  const handleChange = (field: keyof CompanyData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (!formData.name.trim()) {
        setError('Company name is required');
        setLoading(false);
        return;
      }

      if (!formData.contact_email.trim()) {
        setError('Contact email is required');
        setLoading(false);
        return;
      }

      await companiesAPI.create({
        name: formData.name,
        contact_email: formData.contact_email,
        status: formData.status,
      });

      addToast('Company created successfully!', 'success');
      navigate('/companies');
    } catch (err) {
      const errorMsg = (err as any)?.response?.data?.detail || 'Failed to create company';
      setError(errorMsg);
      addToast(errorMsg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate('/companies')}
          sx={{ mr: 2 }}
        >
          Back
        </Button>
        <Typography variant="h4">Create New Company</Typography>
      </Box>

      <Paper sx={{ p: 3, maxWidth: 600 }}>
        <Alert severity="info" sx={{ mb: 3 }}>
          Для создания компании достаточно указать название, контактный email и статус.
        </Alert>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label="Company Name"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            margin="normal"
            required
            disabled={loading}
          />

          <TextField
            fullWidth
            label="Contact Email"
            type="email"
            value={formData.contact_email}
            onChange={(e) => handleChange('contact_email', e.target.value)}
            margin="normal"
            required
            disabled={loading}
          />

          <FormControl fullWidth margin="normal" disabled={loading}>
            <InputLabel>Status</InputLabel>
            <Select
              label="Status"
              value={formData.status}
              onChange={(e) => handleChange('status', String(e.target.value) as CompanyData['status'])}
            >
              <MenuItem value="active">active</MenuItem>
              <MenuItem value="inactive">inactive</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
            <Button
              variant="outlined"
              onClick={() => navigate('/companies')}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              type="submit"
              startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create Company'}
            </Button>
          </Box>
        </form>
      </Paper>
    </Box>
  );
}
