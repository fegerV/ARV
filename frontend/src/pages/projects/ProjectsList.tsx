import { useState, useEffect } from 'react';
import { Box, Typography, Button, Paper, Table, TableHead, TableBody, TableRow, TableCell, Chip, Select, MenuItem, FormControl, InputLabel, Alert, Dialog, DialogTitle, DialogContent, DialogActions, DialogContentText, CircularProgress } from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { companiesAPI, projectsAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

// Company interface
interface Company {
  id: string;
  name: string;
  is_default?: boolean;
}

// Project interface
interface Project {
  id: string;
  name: string;
  status: string;
  ar_content_count: number;
  created_at: string;
}

export default function ProjectsList() {
  const navigate = useNavigate();
  const { companyId } = useParams<{ companyId: string }>();
  const { addToast } = useToast();
  
  console.log('ProjectsList component mounted, companyId:', companyId);

  const [companies, setCompanies] = useState<Company[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);

  const [refreshing, setRefreshing] = useState(false);
  
  console.log('ProjectsList rendering with state:', { 
    companyId, 
    selectedCompanyId, 
    loading, 
    projectsCount: projects.length 
  });

  // Fetch companies and projects
  useEffect(() => {
    let isMounted = true;
    
    const fetchData = async () => {
      setLoading(true);
      try {
        // Try cached companies first
        const cachedCompanies = sessionStorage.getItem('cached_companies');
        if (cachedCompanies) {
          try {
            const parsed = JSON.parse(cachedCompanies);
            if (Date.now() - parsed.timestamp < 5 * 60 * 1000) { // 5 минут кэша
              console.log('Using cached companies data');
              if (isMounted) {
                setCompanies(parsed.data);
                
                // Set initial selected company from cache
                let defaultCompanyId: string | null = null;
                if (companyId) {
                  defaultCompanyId = companyId;
                } else {
                  const vertexARCompany = parsed.data.find((company: Company) => 
                    company.is_default === true || company.name === 'Vertex AR'
                  );
                  console.log('Searching for Vertex AR company in cache, found:', vertexARCompany);
                  
                  if (vertexARCompany) {
                    defaultCompanyId = vertexARCompany.id;
                  } else if (parsed.data.length > 0) {
                    defaultCompanyId = parsed.data[0].id;
                  }
                }
                console.log('Selected company ID from cache:', defaultCompanyId);
                
                if (defaultCompanyId) {
                  setSelectedCompanyId(defaultCompanyId);
                  
                  // Fetch projects for this company
                  console.log(`Fetching projects for company ${defaultCompanyId}`);
                  try {
                    const projectsResponse = await projectsAPI.listByCompany(defaultCompanyId, { page: 1, page_size: 100 });
                    if (isMounted) {
                      setProjects(projectsResponse.data?.items || []);
                    }
                  } catch (projectsError) {
                    console.error('Failed to fetch projects:', projectsError);
                    if (isMounted) {
                      addToast('Failed to load projects', 'error');
                    }
                  }
                  
                  // Убираем автоматический редирект, который вызывал проблему
                  /* if (!companyId && isMounted) {
                    navigate(`/companies/${defaultCompanyId}/projects`, { replace: true });
                  } */
                }
                setLoading(false);
                return;
              }
            }
          } catch (e) {
            console.error('Failed to parse cached companies', e);
          }
        }
        
        // Fetch fresh companies data
        const companiesResponse = await companiesAPI.list({ page: 1, page_size: 100 });
        if (!isMounted) return;
        
        // Cache the data
        sessionStorage.setItem('cached_companies', JSON.stringify({
          data: companiesResponse.data?.items || [],
          timestamp: Date.now()
        }));
        
        setCompanies(companiesResponse.data?.items || []);
        
        // Set initial selected company
        let defaultCompanyId: string | null = null;
        
        if (companyId) {
          // Use the company ID from URL params
          defaultCompanyId = companyId;
        } else {
          // Find the Vertex AR company (default company)
          const vertexARCompany = (companiesResponse.data?.items || []).find((company: Company) => 
            company.is_default === true || company.name === 'Vertex AR'
          );
          console.log('Searching for Vertex AR company, found:', vertexARCompany);
          
          if (vertexARCompany) {
            defaultCompanyId = vertexARCompany.id;
          } else if ((companiesResponse.data?.items || []).length > 0) {
            // Fallback to first company if Vertex AR not found
            defaultCompanyId = (companiesResponse.data?.items || [])[0].id;
          }
        }
        console.log('Selected company ID:', defaultCompanyId);
        
        // Set the selected company and fetch its projects
        if (defaultCompanyId) {
          setSelectedCompanyId(defaultCompanyId);
          
          // Fetch projects for this company
          console.log(`Fetching projects for company ${defaultCompanyId}`);
          try {
            const projectsResponse = await projectsAPI.listByCompany(defaultCompanyId, { page: 1, page_size: 100 });
            if (!isMounted) return;

            setProjects(projectsResponse.data?.items || []);
          } catch (projectsError) {
            console.error('Failed to fetch projects:', projectsError);
            if (isMounted) {
              addToast('Failed to load projects', 'error');
            }
          }
          
          // Убираем автоматический редирект, который вызывал проблему
          /* // Update URL if needed
          if (!companyId && isMounted) {
            navigate(`/companies/${defaultCompanyId}/projects`, { replace: true });
          } */
        }
      } catch (error) {
        console.error('Failed to fetch companies:', error);
        console.error('Error details:', {
          message: (error as any)?.message,
          response: (error as any)?.response,
          request: (error as any)?.request,
        });
        if (isMounted) {
          addToast('Failed to load companies. Please check your connection and try again.', 'error');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    
    fetchData();
    
    return () => {
      isMounted = false;
    };
  }, [companyId]);

  // Fetch projects when selected company changes
  useEffect(() => {
    const fetchProjects = async () => {
      if (selectedCompanyId) {
        setLoading(true);
        try {
          const projectsResponse = await projectsAPI.listByCompany(selectedCompanyId, { page: 1, page_size: 100 });
          setProjects(projectsResponse.data?.items || []);
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
        const projectsResponse = await projectsAPI.listByCompany(selectedCompanyId, { page: 1, page_size: 100 });
        setProjects(projectsResponse.data?.items || []);
      }
    } catch (error) {
      console.error('Failed to delete project:', error);
      addToast('Failed to delete project', 'error');
    } finally {
      setDeleting(false);
    }
  };

  const handleCompanyChange = (event: SelectChangeEvent) => {
    console.log('handleCompanyChange called with event:', event);
    const value = event.target.value as string;
    const nextCompanyId = value ? String(value) : null;
    setSelectedCompanyId(nextCompanyId);
    if (nextCompanyId) {
      console.log('Navigating to company projects:', `/companies/${nextCompanyId}/projects`);
      navigate(`/companies/${nextCompanyId}/projects`);
    } else {
      console.log('Would navigate to /projects, but skipping');
      // Убираем редирект на /projects, который может вызывать проблемы
      // navigate('/projects');
    }
  };

  const handleRefresh = async () => {
    if (!selectedCompanyId) return;
    
    try {
      setRefreshing(true);
      // Clear cache
      sessionStorage.removeItem('cached_companies');
      const projectsResponse = await projectsAPI.listByCompany(selectedCompanyId, { page: 1, page_size: 100 });
      setProjects(projectsResponse.data?.items || []);
    } catch (error) {
      console.error('Failed to refresh projects:', error);
      addToast('Failed to refresh projects', 'error');
    } finally {
      setRefreshing(false);
    }
  };

  const handleRefreshCompanies = async () => {
    try {
      setLoading(true);
      // Clear cache
      sessionStorage.removeItem('cached_companies');
      
      // Fetch fresh companies data
      const companiesResponse = await companiesAPI.list({ page: 1, page_size: 100 });
      
      // Cache the data
      sessionStorage.setItem('cached_companies', JSON.stringify({
        data: companiesResponse.data?.items || [],
        timestamp: Date.now()
      }));

      setCompanies(companiesResponse.data?.items || []);
      
      // If no company is selected or current selection is invalid, select default
      const refreshedCompanies = companiesResponse.data?.items || [];
      if (!selectedCompanyId || !refreshedCompanies.some((c: Company) => c.id === selectedCompanyId)) {
        const vertexARCompany = refreshedCompanies.find((company: Company) =>
          company.name === 'Vertex AR'
        );
        
        if (vertexARCompany) {
          setSelectedCompanyId(vertexARCompany.id);
          // Fetch projects for this company
          try {
            const projectsResponse = await projectsAPI.listByCompany(vertexARCompany.id, { page: 1, page_size: 100 });
            setProjects(projectsResponse.data?.items || []);
          } catch (projectsError) {
            console.error('Failed to fetch projects:', projectsError);
            addToast('Failed to load projects', 'error');
          }
          // Убираем автоматический редирект, который вызывал проблему
          // navigate(`/companies/${vertexARCompany.id}/projects`, { replace: true });
        }
      }
    } catch (error) {
      console.error('Failed to refresh companies:', error);
      addToast('Failed to refresh companies', 'error');
    } finally {
      setLoading(false);
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
            Refresh Projects
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefreshCompanies}
            disabled={loading}
            sx={{ mr: 2 }}
          >
            Refresh Companies
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
            {companies.map((company: Company) => (
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
                  <TableCell>Created</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {projects.map((project: Project) => (
                  <TableRow key={project.id} hover>
                    <TableCell>
                      <Typography variant="subtitle2">
                        {project.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={project.status} 
                        size="small" 
                        color={project.status === 'active' ? 'success' : 'default'}
                      />
                    </TableCell>
                    <TableCell>{project.ar_content_count ?? 0}</TableCell>
                    <TableCell>
                      {project.created_at ? new Date(project.created_at).toLocaleString() : '—'}
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
