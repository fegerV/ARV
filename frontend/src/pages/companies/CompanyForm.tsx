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
  slug: string;
  description: string;
  contact_email: string;
  contact_phone: string;
  storage_connection_id: number | null;
  storage_path: string;
}

export default function CompanyForm() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<CompanyData>({
    name: '',
    slug: '',
    description: '',
    contact_email: '',
    contact_phone: '',
    storage_connection_id: null,
    storage_path: '',
  });

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  };

  const handleChange = (field: keyof CompanyData, value: string) => {
    setFormData((prev) => {
      const updated = { ...prev, [field]: value };
      if (field === 'name') {
        updated.slug = generateSlug(value);
      }
      return updated;
    });
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

      if (!formData.storage_connection_id) {
        setError('Storage connection is required. Please create a storage connection first (MinIO or Yandex Disk).');
        setLoading(false);
        return;
      }

      await companiesAPI.create({
        name: formData.name,
        contact_email: formData.contact_email,
        contact_phone: formData.contact_phone || undefined,
        storage_connection_id: formData.storage_connection_id,
        storage_path: formData.storage_path || undefined,
        notes: formData.description || undefined,
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
          <Typography variant="subtitle2" gutterBottom>
            Creating New Companies
          </Typography>
          <Typography variant="body2" paragraph>
            Note: A default company "Vertex AR" with local storage already exists. 
            New companies must use external storage providers (MinIO or Yandex Disk).
          </Typography>
          <Typography variant="body2">
            To create a company, you need to first set up a storage connection (MinIO or Yandex Disk) in the Settings page. 
            Then provide the storage connection ID and path.
          </Typography>
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
            label="Slug"
            value={formData.slug}
            onChange={(e) => handleChange('slug', e.target.value)}
            margin="normal"
            helperText="Auto-generated from company name"
            disabled={loading}
          />

          <TextField
            fullWidth
            label="Description"
            value={formData.description}
            onChange={(e) => handleChange('description', e.target.value)}
            margin="normal"
            multiline
            rows={3}
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

          <TextField
            fullWidth
            label="Phone Number"
            value={formData.contact_phone}
            onChange={(e) => handleChange('contact_phone', e.target.value)}
            margin="normal"
            disabled={loading}
          />

          <TextField
            fullWidth
            label="Storage Connection ID"
            type="number"
            value={formData.storage_connection_id || ''}
            onChange={(e) => {
              setFormData((prev) => ({
                ...prev,
                storage_connection_id: e.target.value ? parseInt(e.target.value) : null,
              }));
            }}
            margin="normal"
            required
            disabled={loading}
            helperText="Create a Yandex Disk or MinIO storage connection first in Settings"
          />

          <TextField
            fullWidth
            label="Storage Path"
            value={formData.storage_path}
            onChange={(e) => handleChange('storage_path', e.target.value)}
            margin="normal"
            disabled={loading}
            helperText="Path in Yandex Disk (e.g., /Companies/MyCompany) or bucket name for MinIO"
          />

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
