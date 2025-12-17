import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  CardMedia,
  MenuItem,
  Chip,
  FormControl,
  InputLabel,
  Select,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormLabel,
  Checkbox,
  Grid,
  Divider,
  IconButton,
} from '@mui/material';
import { 
  ArrowBack as BackIcon, 
  Save as SaveIcon,
  Delete as DeleteIcon,
  QrCode as QrCodeIcon,
  CheckCircle as CheckIcon,
  Business as BusinessIcon,
  Folder as FolderIcon,
  Image as ImageIcon,
  VideoLibrary as VideoIcon,
} from '@mui/icons-material';
import { arContentAPI, companiesAPI, projectsAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

interface ARContentFormData {
  // Customer info
  customerName: string;
  customerPhone: string;
  customerEmail: string;
  
  // Company info
  companyId: string | null;
  
  // Project info
  projectId: string | null;
  newProjectName: string;
  creatingNewProject: boolean;
  
  // Content info
  name: string;
  description: string;
  
  // Media
  image: File | null;
  video: File | null;
  
  // Schedule
  scheduleType: 'daily' | 'weekly' | 'monthly' | 'custom';
  scheduleTime: string;
  
  // Playback duration
  playbackDuration: '1_year' | '3_years' | '5_years';
  
  // Status
  isActive: boolean;
}

interface Company {
  id: string;
  name: string;
  contact_email: string;
  is_default?: boolean;
}

interface Project {
  id: string;
  name: string;
  slug?: string;
}

interface CreationResponse {
  id: string;
  unique_id: string;
  unique_link: string;
  image_url?: string;
  video_url?: string;
  qr_code_url?: string;
  preview_url?: string;
}

export default function ARContentForm() {
  const navigate = useNavigate();
  const { projectId, companyId } = useParams<{ projectId: string; companyId: string }>();
  const { addToast } = useToast();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [creationResponse, setCreationResponse] = useState<CreationResponse | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  
  // Data for dropdowns
  const [companies, setCompanies] = useState<Company[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  
  const [formData, setFormData] = useState<ARContentFormData>({
    // Customer info
    customerName: '',
    customerPhone: '',
    customerEmail: '',
    
    // Company info
    companyId: companyId || null,
    
    // Project info
    projectId: projectId || null,
    newProjectName: '',
    creatingNewProject: false,
    
    // Content info
    name: '',
    description: '',
    
    // Media
    image: null,
    video: null,
    
    // Schedule
    scheduleType: 'daily',
    scheduleTime: '09:00',
    
    // Playback duration
    playbackDuration: '3_years',
    
    // Status
    isActive: true,
  });

  // Fetch companies and projects
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch companies (including default)
        const companiesResponse = await companiesAPI.list();
        const fetchedCompanies = (companiesResponse as any).data?.items || (companiesResponse as any).data || [];
        setCompanies(fetchedCompanies);

        // Set company ID from URL params or default company
        if (fetchedCompanies.length > 0) {
          const defaultCompanyId = (() => {
            if (companyId) return companyId;
            const vertexARCompany = fetchedCompanies.find((company: Company) => company.name === 'Vertex AR');
            return vertexARCompany ? vertexARCompany.id : fetchedCompanies[0].id;
          })();

          setFormData(prev => {
            if (prev.companyId) return prev;
            return {
              ...prev,
              companyId: defaultCompanyId,
            };
          });
        }
      } catch (err) {
        console.error('Failed to fetch data:', err);
        addToast('Failed to load companies and projects', 'error');
      }
    };
    
    fetchData();
  }, [companyId, addToast]); // companyId влияет на дефолтный выбор компании

  // Handle company change
  const handleCompanyChange = (companyId: string) => {
    setFormData(prev => ({
      ...prev,
      companyId,
      projectId: null, // Reset project when company changes
      newProjectName: '',
      creatingNewProject: false,
    }));
  };

  // Fetch projects when companyId changes
  useEffect(() => {
    const fetchProjects = async () => {
      if (formData.companyId) {
        try {
          const projectsResponse = await projectsAPI.listByCompany(formData.companyId);
          const fetchedProjects = (projectsResponse as any).data?.items || [];
          setProjects(fetchedProjects);

          // Если projectId задан в URL, но его нет в списке компании — сбрасываем
          if (projectId) {
            const projectExists = fetchedProjects.some((p: Project) => p.id === projectId);
            if (!projectExists) {
              setFormData(prev => ({
                ...prev,
                projectId: null,
              }));
            }
          }
        } catch (err) {
          console.error('Failed to fetch projects:', err);
          addToast('Failed to load projects', 'error');
        }
      } else {
        setProjects([]);
      }
    };

    fetchProjects();
  }, [formData.companyId, projectId, addToast]);

  // Image preview URL (avoid leaking object URLs)
  useEffect(() => {
    if (!formData.image) {
      setImagePreviewUrl(null);
      return;
    }

    const url = URL.createObjectURL(formData.image);
    setImagePreviewUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [formData.image]);

  // Handle image file change
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData(prev => ({ ...prev, image: e.target.files![0] }));
      setError(null);
    }
  };

  // Handle video file change
  const handleVideoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData(prev => ({ ...prev, video: e.target.files![0] }));
      setError(null);
    }
  };

  // Validate form
  const validateForm = (): string | null => {
    if (!formData.name.trim()) {
      return 'Content name is required';
    }
    
    if (!formData.customerName.trim()) {
      return 'Customer name is required';
    }
    
    if (!formData.customerEmail.trim()) {
      return 'Customer email is required';
    }
    
    if (!formData.companyId) {
      return 'Please select a company';
    }
    
    if (formData.creatingNewProject) {
      if (!formData.newProjectName.trim()) {
        return 'Project name is required';
      }
    } else {
      if (!formData.projectId) {
        return 'Please select a project or create a new one';
      }
    }
    
    if (!formData.image) {
      return 'Please upload an image';
    }
    
    return null;
  };

  // Handle form submission
  const handleSubmit = async () => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // If creating a new project, do that first
      let finalProjectId = formData.projectId;
      if (formData.creatingNewProject && formData.newProjectName.trim() && formData.companyId) {
        try {
          const projectResponse = await projectsAPI.create(formData.companyId, {
            company_id: formData.companyId,
            name: formData.newProjectName,
          });
          finalProjectId = (projectResponse as any).data?.id;
        } catch (projectErr) {
          const errorMsg = (projectErr as any)?.response?.data?.detail || 'Failed to create project';
          setError(`Project creation failed: ${errorMsg}`);
          setLoading(false);
          return;
        }
      }

      // Ensure we have both companyId and projectId
      if (!formData.companyId || !finalProjectId) {
        setError('Company and project information is missing');
        setLoading(false);
        return;
      }

      // Prepare form data for upload
      const uploadData = new FormData();
      uploadData.append('name', formData.name);
      uploadData.append('description', formData.description);
      
      // Add customer info as metadata
      const metadata = {
        customer_name: formData.customerName,
        customer_phone: formData.customerPhone,
        customer_email: formData.customerEmail,
        schedule_type: formData.scheduleType,
        schedule_time: formData.scheduleTime,
        playback_duration: formData.playbackDuration,
      };
      uploadData.append('content_metadata', JSON.stringify(metadata));
      
      // Add image (required)
      if (formData.image) {
        uploadData.append('image', formData.image);
      }
      
      // Add video (optional)
      if (formData.video) {
        uploadData.append('video', formData.video);
      }

      // Call API to create AR content
      const response = await arContentAPI.create(formData.companyId, finalProjectId, uploadData);
      const responseData = response.data as CreationResponse;
      
      setCreationResponse(responseData);
      addToast('AR content created successfully!', 'success');
      
    } catch (err: any) {
      console.error('AR content creation error:', err);
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to create AR content';
      setError(`Creation failed: ${errorMsg}`);
      addToast(`Creation failed: ${errorMsg}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // If creation was successful, show success screen
  if (creationResponse) {
    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Button
            startIcon={<BackIcon />}
            onClick={() => {
              if (companyId && projectId) {
                navigate(`/companies/${companyId}/projects/${projectId}/ar-content`);
              } else if (companyId) {
                navigate(`/companies/${companyId}/projects`);
              } else {
                navigate('/ar-content');
              }
            }}
            sx={{ mr: 2 }}
          >
            Back
          </Button>
          <Typography variant="h4">AR Content Created Successfully!</Typography>
        </Box>

        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <CheckIcon sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
          
          <Typography variant="h5" gutterBottom>
            Your AR content is now live
          </Typography>
          
          <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
            Share the unique link or QR code below with your customers
          </Typography>
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Unique Link</Typography>
                  <TextField
                    fullWidth
                    value={creationResponse.unique_link}
                    InputProps={{
                      readOnly: true,
                    }}
                    sx={{ mb: 2 }}
                  />
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => {
                      navigator.clipboard.writeText(creationResponse.unique_link);
                      addToast('Link copied to clipboard!', 'success');
                    }}
                  >
                    Copy Link
                  </Button>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>QR Code</Typography>
                  {creationResponse.qr_code_url && (
                    <Box sx={{ mb: 2, textAlign: 'center' }}>
                      <img 
                        src={creationResponse.qr_code_url} 
                        alt="QR Code" 
                        style={{ maxWidth: '200px', maxHeight: '200px' }}
                      />
                    </Box>
                  )}
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => {
                      if (creationResponse.qr_code_url) {
                        const link = document.createElement('a');
                        link.href = creationResponse.qr_code_url;
                        link.download = 'qr-code.png';
                        link.click();
                      }
                    }}
                  >
                    Download QR Code
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          
          <Box sx={{ mt: 4 }}>
            <Button
              variant="contained"
              size="large"
              onClick={() => {
                if (companyId && projectId) {
                  navigate(`/companies/${companyId}/projects/${projectId}/ar-content`);
                } else if (companyId) {
                  navigate(`/companies/${companyId}/projects`);
                } else {
                  navigate('/ar-content');
                }
              }}
            >
              Continue to Content List
            </Button>
          </Box>
        </Paper>
      </Box>
    );
  }

  // If no companies exist, show empty state
  if (companies.length === 0 && !loading) {
    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Button
            startIcon={<BackIcon />}
            onClick={() => navigate('/ar-content')}
            sx={{ mr: 2 }}
          >
            Back
          </Button>
          <Typography variant="h4">Create New AR Content</Typography>
        </Box>

        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>No Companies Available</Typography>
          <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
            You need to create a company before you can create AR content.
          </Typography>
          <Button
            variant="contained"
            onClick={() => navigate('/companies/new')}
          >
            Create Company
          </Button>
        </Paper>
      </Box>
    );
  }

  // If no projects exist for selected company, show empty state
  if (formData.companyId && projects.length === 0 && !loading && !formData.creatingNewProject) {
    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Button
            startIcon={<BackIcon />}
            onClick={() => navigate('/ar-content')}
            sx={{ mr: 2 }}
          >
            Back
          </Button>
          <Typography variant="h4">Create New AR Content</Typography>
        </Box>

        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>No Projects Available</Typography>
          <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
            You need to create a project for the selected company before you can create AR content.
          </Typography>
          <Button
            variant="contained"
            onClick={() => setFormData({ ...formData, creatingNewProject: true })}
          >
            Create New Project
          </Button>
          <Button
            variant="outlined"
            onClick={() => navigate('/companies')}
            sx={{ ml: 2 }}
          >
            Choose Different Company
          </Button>
        </Paper>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<BackIcon />}
          onClick={() => {
            if (companyId && projectId) {
              navigate(`/companies/${companyId}/projects/${projectId}/ar-content`);
            } else {
              navigate('/ar-content');
            }
          }}
          sx={{ mr: 2 }}
        >
          Back
        </Button>
        <Typography variant="h4">Create New AR Content</Typography>
      </Box>

      <Paper sx={{ p: 3 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* Company Selection */}
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>Company Selection</Typography>
            <FormControl fullWidth margin="normal" required>
              <InputLabel>Select Company</InputLabel>
              <Select
                value={formData.companyId || ''}
                onChange={(e) => handleCompanyChange(String(e.target.value))}
                disabled={loading}
                label="Select Company"
              >
                {companies.map((company) => (
                  <MenuItem key={company.id} value={company.id}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <BusinessIcon sx={{ mr: 1 }} fontSize="small" />
                      {company.name}
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
          </Grid>

          {/* Project Selection */}
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>Project Selection</Typography>
            <FormControl component="fieldset" sx={{ width: '100%', mb: 2 }}>
              <RadioGroup
                value={formData.creatingNewProject ? 'new' : 'existing'}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  creatingNewProject: e.target.value === 'new',
                  projectId: null,
                  newProjectName: ''
                })}
              >
                <FormControlLabel 
                  value="existing" 
                  control={<Radio />} 
                  label="Select Existing Project" 
                  disabled={loading} 
                />
                <FormControlLabel 
                  value="new" 
                  control={<Radio />} 
                  label="Create New Project" 
                  disabled={loading} 
                />
              </RadioGroup>
            </FormControl>
            
            {!formData.creatingNewProject ? (
              <FormControl fullWidth margin="normal" required>
                <InputLabel>Select Project</InputLabel>
                <Select
                  value={formData.projectId || ''}
                  onChange={(e) => setFormData({ ...formData, projectId: String(e.target.value) })}
                  disabled={loading}
                  label="Select Project"
                >
                  {projects.map((project) => (
                    <MenuItem key={project.id} value={project.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <FolderIcon sx={{ mr: 1 }} fontSize="small" />
                        {project.name}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
                
                {projects.length === 0 && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No projects found for this company. Please create a new project.
                  </Alert>
                )}
              </FormControl>
            ) : (
              <TextField
                fullWidth
                label="New Project Name"
                value={formData.newProjectName}
                onChange={(e) => setFormData({ ...formData, newProjectName: e.target.value })}
                margin="normal"
                required
                disabled={loading}
                helperText="Enter a name for your new project"
              />
            )}
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Customer Information */}
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>Customer Information</Typography>
            
            <TextField
              fullWidth
              label="Customer Name"
              value={formData.customerName}
              onChange={(e) => setFormData({ ...formData, customerName: e.target.value })}
              margin="normal"
              required
              disabled={loading}
            />
            
            <TextField
              fullWidth
              label="Customer Phone"
              value={formData.customerPhone}
              onChange={(e) => setFormData({ ...formData, customerPhone: e.target.value })}
              margin="normal"
              disabled={loading}
            />
            
            <TextField
              fullWidth
              label="Customer Email"
              type="email"
              value={formData.customerEmail}
              onChange={(e) => setFormData({ ...formData, customerEmail: e.target.value })}
              margin="normal"
              required
              disabled={loading}
            />
          </Grid>

          {/* Content Information */}
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>Content Details</Typography>
            
            <TextField
              fullWidth
              label="Content Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              margin="normal"
              required
              disabled={loading}
            />
            
            <TextField
              fullWidth
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              margin="normal"
              multiline
              rows={3}
              disabled={loading}
            />
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Upload Media */}
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>Upload Media</Typography>
            
            {/* Image Upload */}
            <Typography variant="subtitle1" gutterBottom>Image</Typography>
            {formData.image ? (
              <Card sx={{ mb: 2 }}>
                <CardMedia
                  component="img"
                  height="200"
                  image={imagePreviewUrl || ''}
                  alt="Image preview"
                />
                <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle2">{formData.image.name}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      {(formData.image.size / 1024 / 1024).toFixed(2)} MB
                    </Typography>
                  </Box>
                  <IconButton
                    color="error"
                    onClick={() => setFormData(prev => ({ ...prev, image: null }))}
                    disabled={loading}
                  >
                    <DeleteIcon />
                  </IconButton>
                </CardContent>
              </Card>
            ) : (
              <Box
                sx={{
                  border: '2px dashed grey',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  mb: 2,
                }}
              >
                <input
                  accept="image/*"
                  type="file"
                  onChange={handleImageChange}
                  style={{ display: 'none' }}
                  id="image-upload"
                  disabled={loading}
                />
                <label htmlFor="image-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<ImageIcon />}
                    disabled={loading}
                  >
                    Select Image
                  </Button>
                </label>
              </Box>
            )}
          </Grid>

          {/* Video Upload */}
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>&nbsp;</Typography>
            
            <Typography variant="subtitle1" gutterBottom>Video</Typography>
            {formData.video ? (
              <Card sx={{ mb: 2 }}>
                <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="subtitle2">{formData.video.name}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      {(formData.video.size / 1024 / 1024).toFixed(2)} MB
                    </Typography>
                  </Box>
                  <IconButton
                    color="error"
                    onClick={() => setFormData(prev => ({ ...prev, video: null }))}
                    disabled={loading}
                  >
                    <DeleteIcon />
                  </IconButton>
                </CardContent>
              </Card>
            ) : (
              <Box
                sx={{
                  border: '2px dashed grey',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  mb: 2,
                }}
              >
                <input
                  accept="video/*"
                  type="file"
                  onChange={handleVideoChange}
                  style={{ display: 'none' }}
                  id="video-upload"
                  disabled={loading}
                />
                <label htmlFor="video-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<VideoIcon />}
                    disabled={loading}
                  >
                    Select Video
                  </Button>
                </label>
              </Box>
            )}
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Generate Marker */}
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>Generate Marker</Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              The AR marker will be automatically generated after content creation. 
              You can also manually regenerate it later if needed.
            </Alert>
            <Box sx={{ textAlign: 'center', py: 2 }}>
              <QrCodeIcon sx={{ fontSize: 60, color: 'primary.main' }} />
              <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                Marker generation happens in the background and may take a few minutes to complete.
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Video Schedule */}
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>Video Schedule</Typography>
            
            <FormControl component="fieldset" sx={{ width: '100%', mb: 3 }}>
              <FormLabel component="legend">Schedule Type</FormLabel>
              <RadioGroup
                value={formData.scheduleType}
                onChange={(e) => setFormData({ ...formData, scheduleType: e.target.value as any })}
              >
                <FormControlLabel value="daily" control={<Radio />} label="Daily" />
                <FormControlLabel value="weekly" control={<Radio />} label="Weekly" />
                <FormControlLabel value="monthly" control={<Radio />} label="Monthly" />
                <FormControlLabel value="custom" control={<Radio />} label="Custom (Cron)" />
              </RadioGroup>
            </FormControl>
            
            {formData.scheduleType !== 'custom' ? (
              <TextField
                fullWidth
                label="Schedule Time"
                type="time"
                value={formData.scheduleTime}
                onChange={(e) => setFormData({ ...formData, scheduleTime: e.target.value })}
                margin="normal"
                InputLabelProps={{
                  shrink: true,
                }}
                inputProps={{
                  step: 300, // 5 min
                }}
              />
            ) : (
              <TextField
                fullWidth
                label="Cron Expression"
                value={formData.scheduleTime}
                onChange={(e) => setFormData({ ...formData, scheduleTime: e.target.value })}
                margin="normal"
                helperText="Enter a cron expression (e.g., 0 9 * * 1 for every Monday at 9 AM)"
              />
            )}
          </Grid>

          {/* Playback Duration */}
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>Playback Duration</Typography>
            
            <FormControl component="fieldset" sx={{ width: '100%' }}>
              <RadioGroup
                value={formData.playbackDuration}
                onChange={(e) => setFormData({ ...formData, playbackDuration: e.target.value as any })}
              >
                <FormControlLabel 
                  value="1_year" 
                  control={<Radio />} 
                  label={
                    <Box>
                      <Typography variant="body1">1 Year</Typography>
                      <Typography variant="body2" color="textSecondary">Standard duration</Typography>
                    </Box>
                  } 
                />
                <FormControlLabel 
                  value="3_years" 
                  control={<Radio />} 
                  label={
                    <Box>
                      <Typography variant="body1">3 Years</Typography>
                      <Typography variant="body2" color="textSecondary">Recommended for most clients</Typography>
                    </Box>
                  } 
                />
                <FormControlLabel 
                  value="5_years" 
                  control={<Radio />} 
                  label={
                    <Box>
                      <Typography variant="body1">5 Years</Typography>
                      <Typography variant="body2" color="textSecondary">Extended enterprise license</Typography>
                    </Box>
                  } 
                />
              </RadioGroup>
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Status */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Checkbox
                checked={formData.isActive}
                onChange={(e) => setFormData({ ...formData, isActive: e.target.checked })}
                id="publish-checkbox"
              />
              <label htmlFor="publish-checkbox" style={{ marginLeft: 8 }}>
                Publish and activate immediately
              </label>
            </Box>
          </Grid>

          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
              <Button
                variant="outlined"
                onClick={() => {
                 if (companyId && projectId) {
                    navigate(`/companies/${companyId}/projects/${projectId}/ar-content`);
                  } else {
                    navigate('/ar-content');
                  }
                }}
                disabled={loading}
              >
                Cancel
              </Button>
              
              <Button
                variant="contained"
                color="primary"
                onClick={handleSubmit}
                startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
                disabled={loading}
                size="large"
              >
                {loading ? 'Creating...' : 'Create AR Content'}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
}