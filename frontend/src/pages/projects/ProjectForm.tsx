import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Button,
  TextField,
  Paper,
  Typography,
  CircularProgress,
  Alert,
} from '@mui/material';
import { ArrowBack as BackIcon, Save as SaveIcon } from '@mui/icons-material';
import { projectsAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

interface ProjectData {
  name: string;
  description: string;
  slug: string;
}

export default function ProjectForm() {
  const navigate = useNavigate();
  const { companyId } = useParams<{ companyId: string }>();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<ProjectData>({
    name: '',
    description: '',
    slug: '',
  });

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  };

  const handleChange = (field: keyof ProjectData, value: string) => {
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
        setError('Project name is required');
        setLoading(false);
        return;
      }

      if (!companyId) {
        setError('Company ID is missing');
        setLoading(false);
        return;
      }

      await projectsAPI.create({
        company_id: companyId,
        name: formData.name,
      });

      addToast('Project created successfully!', 'success');
      navigate(`/companies/${companyId}/projects`);
    } catch (err) {
      const errorMsg = (err as any)?.response?.data?.detail || 'Failed to create project';
      setError(errorMsg);
      addToast(errorMsg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    if (companyId) {
      navigate(`/companies/${companyId}/projects`);
    } else {
      navigate('/companies');
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<BackIcon />}
          onClick={handleBack}
          sx={{ mr: 2 }}
        >
          Back
        </Button>
        <Typography variant="h4">Create New Project</Typography>
      </Box>

      <Paper sx={{ p: 3, maxWidth: 600 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label="Project Name"
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
            helperText="Auto-generated from project name"
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

          <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
            <Button
              variant="outlined"
              onClick={handleBack}
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
              {loading ? 'Creating...' : 'Create Project'}
            </Button>
          </Box>
        </form>
      </Paper>
    </Box>
  );
}
