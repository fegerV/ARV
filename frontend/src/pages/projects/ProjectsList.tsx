import { useState, useEffect } from 'react';
import { Box, Typography, Button, Paper, Table, TableHead, TableBody, TableRow, TableCell, Chip, Select, MenuItem, FormControl, InputLabel, Alert, Dialog, DialogTitle, DialogContent, DialogActions, DialogContentText, CircularProgress } from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { companiesAPI, projectsAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

// Company interface
interface Company {
  id: number;
  name: string;
  is_default?: boolean;
}

// Project interface
interface Project {
  id: number;
  name: string;
  slug: string;
  status: string;
  contentCount?: number;
  createdAt?: string;
  period?: {
    starts_at?: string;
    expires_at?: string;
    days_left?: number;
  };
}

export default function ProjectsList() {
  const navigate = useNavigate();
  const { companyId } = useParams<{ companyId: string }>();
  const { addToast } = useToast();
  
  const [companies, setCompanies] = useState<Company[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);

  const [refreshing, setRefreshing] = useState(false);
  
  // Fetch companies and projects
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Fetch companies
        const companiesResponse = await companiesAPI.list();
        setCompanies(companiesResponse.data);
        
        // Set initial selected company
        let defaultCompanyId: number | null = null;
        
        if (companyId) {
          // Use the company ID from URL params
          defaultCompanyId = parseInt(companyId);
        } else {
          // Find the Vertex AR company (default company)
          const vertexARCompany = companiesResponse.data.find((company: Company) => 
            company.is_default === true || company.name === 'Vertex AR'
          );
          
          if (vertexARCompany) {
            defaultCompanyId = vertexARCompany.id;
          } else if (companiesResponse.data.length > 0) {
            // Fallback to first company if Vertex AR not found
            defaultCompanyId = companiesResponse.data[0].id;
          }
        }
        
        // Set the selected company and fetch its projects
        if (defaultCompanyId) {
          setSelectedCompanyId(defaultCompanyId);
          
          // Fetch projects for this company
          const projectsResponse = await projectsAPI.list(defaultCompanyId);
          setProjects(projectsResponse.data.projects || []);
          
          // Update URL if needed
          if (!companyId) {
            navigate(`/companies/${defaultCompanyId}/projects`, { replace: true });
          }
        }
      } catch (error) {
        console.error('Failed to fetch data:', error);
        addToast('Failed to load data', 'error');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [companyId]);

  // Fetch projects when selected company changes
  useEffect(() => {
    const fetchProjects = async () => {
      if (selectedCompanyId) {
        setLoading(true);
        try {
          const projectsResponse = await projectsAPI.list(selectedCompanyId);
          setProjects(projectsResponse.data.projects || []);
        } catch (error) {
          console.error('Failed to fetch projects:', error);
          addToast('Failed to load projects', 'error');
        } finally {
          setLoading(false);
        }
      } else {
        setProjects([]);
      }
    };
    
    fetchProjects();
  }, [selectedCompanyId]);

  const handleCreateProject = () => {
    if (selectedCompanyId) {
      navigate(`/companies/${selectedCompanyId}/projects/new`);
    } else {
      addToast('Please select a company first', 'warning');
    }
  };

  const handleDeleteProject = (project: Project) => {
    setProjectToDelete(project);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteProject = async () => {
    if (!projectToDelete) return;
    
    try {
      setDeleting(true);
      await projectsAPI.delete(projectToDelete.id);
      addToast('Project deleted successfully', 'success');
      setDeleteDialogOpen(false);
      setProjectToDelete(null);
      
      // Refresh the projects list
      if (selectedCompanyId) {
        const projectsResponse = await projectsAPI.list(selectedCompanyId);
        setProjects(projectsResponse.data.projects || []);
      }
    } catch (error) {
      console.error('Failed to delete project:', error);
      addToast('Failed to delete project', 'error');
    } finally {
      setDeleting(false);
    }
  };

  const handleCompanyChange = (event: any) => {
    const value = event.target.value;
    const companyId = value ? Number(value) : null;
    setSelectedCompanyId(companyId);
    if (companyId) {
      navigate(`/companies/${companyId}/projects`);
    } else {
      navigate('/projects');
    }
  };

  const handleRefresh = async () => {
    if (!selectedCompanyId) return;
    
    try {
      setRefreshing(true);
      const projectsResponse = await projectsAPI.list(selectedCompanyId);
      setProjects(projectsResponse.data.projects || []);
    } catch (error) {
      console.error('Failed to refresh projects:', error);
      addToast('Failed to refresh projects', 'error');
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Projects</Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={refreshing ? <CircularProgress size={20} /> : <RefreshIcon />}
            onClick={handleRefresh}
            disabled={!selectedCompanyId || refreshing}
            sx={{ mr: 2 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateProject}
            disabled={!selectedCompanyId}
          >
            New Project
          </Button>
        </Box>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>Company Selection</Typography>
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Select Company</InputLabel>
          <Select
            value={selectedCompanyId || ''}
            onChange={handleCompanyChange}
            label="Select Company"
          >
            {companies.map((company) => (
              <MenuItem key={company.id} value={company.id}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Typography sx={{ fontWeight: company.is_default ? 'bold' : 'normal' }}>
                    {company.name}
                  </Typography>
                  {company.is_default && (
                    <Chip 
                      label="Default" 
                      size="small" 
                      color="primary" 
                      variant="outlined" 
                      sx={{ ml: 1 }}
                    />
                  )}
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        {!selectedCompanyId && (
          <Alert severity="info">
            The Vertex AR company is selected by default. Please select another company if needed.
          </Alert>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        {loading ? (
          <Typography>Loading projects...</Typography>
        ) : projects.length === 0 ? (
          <Typography color="textSecondary">
            {selectedCompanyId 
              ? 'No projects found for this company.' 
              : 'Select a company to view its projects.'}
          </Typography>
        ) : (
          <>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>AR Content</TableCell>
                  <TableCell>Expires In</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {projects.map((project) => (
                  <TableRow key={project.id} hover>
                    <TableCell>
                      <Typography variant="subtitle2">
                        {project.name}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {project.slug}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={project.status} 
                        size="small" 
                        color={project.status === 'active' ? 'success' : 'default'}
                      />
                    </TableCell>
                    <TableCell>{project.contentCount || 0}</TableCell>
                    <TableCell>
                      {project.period?.days_left !== undefined ? (
                        <Chip 
                          label={`${project.period.days_left} days`}
                          size="small"
                          color={project.period.days_left < 30 ? 'warning' : 'default'}
                        />
                      ) : (
                        'N/A'
                      )}
                    </TableCell>
                    <TableCell>
                      {project.period?.starts_at 
                        ? new Date(project.period.starts_at).toLocaleDateString() 
                        : 'N/A'}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        startIcon={<DeleteIcon />}
                        onClick={() => handleDeleteProject(project)}
                        color="error"
                        disabled={deleting}
                      >
                        {deleting && projectToDelete?.id === project.id ? 'Deleting...' : 'Delete'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        )}
      </Paper>

      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the project "{projectToDelete?.name}"? 
            This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>Cancel</Button>
          <Button onClick={confirmDeleteProject} color="error" disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}