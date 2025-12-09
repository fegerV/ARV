import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Stepper,
  Step,
  StepLabel,
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
  FormGroup,
} from '@mui/material';
import { 
  ArrowBack as BackIcon, 
  Save as SaveIcon,
  Upload as UploadIcon,
  PlayArrow as PlayIcon,
  Schedule as ScheduleIcon,
  QrCode as QrCodeIcon,
  CheckCircle as CheckIcon,
  Add as AddIcon,
  Business as BusinessIcon,
  Folder as FolderIcon,
} from '@mui/icons-material';
import { arContentAPI, companiesAPI, projectsAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

// Define step types
const steps = [
  'Company & Customer',
  'Project Selection',
  'Upload Media',
  'Generate Marker',
  'Video Schedule',
  'Playback Duration',
  'Publish'
];

// Wizard form data interface
interface ARContentFormData {
  // Customer info
  customerName: string;
  customerPhone: string;
  customerEmail: string;
  
  // Company info
  companyId: number | null;
  
  // Project info
  projectId: number | null;
  newProjectName: string;
  creatingNewProject: boolean;
  
  // Media
  portrait: File | null;
  videos: File[];
  
  // Schedule
  scheduleType: 'daily' | 'weekly' | 'monthly' | 'custom';
  scheduleTime: string;
  
  // Playback duration
  playbackDuration: '1_year' | '3_years' | '5_years';
  
  // Content
  title: string;
  description: string;
  isActive: boolean;
}

// Company interface
interface Company {
  id: number;
  name: string;
  contact_email: string;
  is_default?: boolean;
}

// Project interface
interface Project {
  id: number;
  name: string;
  slug: string;
}

export default function ARContentForm() {
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();
  const { addToast } = useToast();
  
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Data for dropdowns
  const [companies, setCompanies] = useState<Company[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  
  const [formData, setFormData] = useState<ARContentFormData>({
    // Customer info
    customerName: '',
    customerPhone: '',
    customerEmail: '',
    
    // Company info
    companyId: 1, // Default to Vertex AR
    
    // Project info
    projectId: projectId ? parseInt(projectId) : null,
    newProjectName: '',
    creatingNewProject: false,
    
    // Media
    portrait: null,
    videos: [],
    
    // Schedule
    scheduleType: 'daily',
    scheduleTime: '09:00',
    
    // Playback duration
    playbackDuration: '3_years',
    
    // Content
    title: '',
    description: '',
    isActive: true,
  });

  // Fetch companies and projects
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch companies
        const companiesResponse = await companiesAPI.list();
        setCompanies(companiesResponse.data);
        
        // If we have a company ID, fetch its projects
        if (formData.companyId) {
          const projectsResponse = await projectsAPI.list(formData.companyId);
          setProjects(projectsResponse.data.projects || []);
        }
      } catch (err) {
        console.error('Failed to fetch data:', err);
        addToast('Failed to load companies and projects', 'error');
      }
    };
    
    fetchData();
  }, [formData.companyId]);

  // Handle company change
  const handleCompanyChange = (companyId: number) => {
    setFormData({
      ...formData,
      companyId,
      projectId: null, // Reset project when company changes
      newProjectName: '',
      creatingNewProject: false,
    });
  };

  // Handle portrait file change
  const handlePortraitChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData({ ...formData, portrait: e.target.files[0] });
      setError(null);
    }
  };

  // Handle videos file change
  const handleVideosChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newVideos = Array.from(e.target.files);
      setFormData({ ...formData, videos: [...formData.videos, ...newVideos] });
      setError(null);
    }
  };

  // Remove a video
  const removeVideo = (index: number) => {
    const newVideos = [...formData.videos];
    newVideos.splice(index, 1);
    setFormData({ ...formData, videos: newVideos });
  };

  // Handle next step
  const handleNext = () => {
    // Validate current step before proceeding
    if (activeStep === 0) {
      // Validate customer info
      if (!formData.customerName.trim()) {
        setError('Customer name is required');
        return;
      }
      if (!formData.customerEmail.trim()) {
        setError('Customer email is required');
        return;
      }
      if (!formData.companyId) {
        setError('Please select a company');
        return;
      }
    }
    
    if (activeStep === 1) {
      // Validate project selection
      if (formData.creatingNewProject) {
        if (!formData.newProjectName.trim()) {
          setError('Project name is required');
          return;
        }
      } else {
        if (!formData.projectId) {
          setError('Please select a project or create a new one');
          return;
        }
      }
    }
    
    if (activeStep === 2) {
      // Validate media upload
      if (!formData.portrait) {
        setError('Please upload a portrait image');
        return;
      }
      
      if (formData.videos.length === 0) {
        setError('Please upload at least one video');
        return;
      }
    }
    
    setError(null);
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  // Handle back step
  const handleBack = () => {
    setError(null);
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  // Handle form submission
  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Validate required fields
      if (!formData.title.trim()) {
        setError('Title is required');
        setLoading(false);
        return;
      }
      
      if (!formData.portrait) {
        setError('Portrait image is required');
        setLoading(false);
        return;
      }
      
      if (formData.videos.length === 0) {
        setError('At least one video is required');
        setLoading(false);
        return;
      }
      
      // Ensure we have a companyId
      if (!formData.companyId) {
        setError('Company information is missing');
        setLoading(false);
        return;
      }
      
      // If creating a new project, do that first
      let finalProjectId = formData.projectId;
      if (formData.creatingNewProject && formData.newProjectName.trim() && formData.companyId) {
        try {
          const projectResponse = await projectsAPI.create(formData.companyId, {
            name: formData.newProjectName,
            description: `Project for ${formData.customerName}`,
            slug: formData.newProjectName.toLowerCase().replace(/\s+/g, '-'),
          });
          finalProjectId = projectResponse.data.id;
        } catch (projectErr) {
          const errorMsg = (projectErr as any)?.response?.data?.detail || 'Failed to create project';
          setError(`Project creation failed: ${errorMsg}`);
          setLoading(false);
          return;
        }
      }

      // Prepare form data for upload
      const uploadData = new FormData();
      uploadData.append('title', formData.title);
      uploadData.append('description', formData.description);
      
      // Add company_id
      uploadData.append('company_id', formData.companyId.toString());
      
      // Add project_id if available
      if (finalProjectId) {
        uploadData.append('project_id', finalProjectId.toString());
      }
      
      // Add customer info
      uploadData.append('customer_name', formData.customerName);
      uploadData.append('customer_phone', formData.customerPhone);
      uploadData.append('customer_email', formData.customerEmail);
      
      // Add portrait
      if (formData.portrait) {
        uploadData.append('portrait', formData.portrait);
      }
      
      // Add videos
      formData.videos.forEach((video, index) => {
        uploadData.append(`videos`, video);
      });
      
      // Add schedule info
      uploadData.append('schedule_type', formData.scheduleType);
      uploadData.append('schedule_time', formData.scheduleTime);
      
      // Add playback duration (convert to days)
      const durationDays = {
        '1_year': 365,
        '3_years': 1095,
        '5_years': 1825,
      }[formData.playbackDuration];
      uploadData.append('playback_duration_days', durationDays.toString());
      
      // Add active status
      uploadData.append('is_active', formData.isActive.toString());

      // Call API to create AR content
      await arContentAPI.create(uploadData);
      
      addToast('AR content created successfully!', 'success');
      
      // Navigate back to the appropriate list
      if (finalProjectId) {
        navigate(`/projects/${finalProjectId}/content`);
      } else if (formData.companyId) {
        navigate(`/companies/${formData.companyId}/projects`);
      } else {
        navigate('/ar-content');
      }
    } catch (err: any) {
      console.error('AR content creation error:', err);
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to create AR content';
      setError(`Creation failed: ${errorMsg}`);
      addToast(`Creation failed: ${errorMsg}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Get step content
  const getStepContent = (step: number) => {
    switch (step) {
      case 0: // Company & Customer Info
        return (
          <Box>
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
            
            <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>Company Selection</Typography>
            
            <FormControl fullWidth margin="normal" required>
              <InputLabel>Select Company</InputLabel>
              <Select
                value={formData.companyId || ''}
                onChange={(e) => handleCompanyChange(Number(e.target.value))}
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
          </Box>
        );
      
      case 1: // Project Selection
        return (
          <Box>
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
              <Box>
                <FormControl fullWidth margin="normal" required>
                  <InputLabel>Select Project</InputLabel>
                  <Select
                    value={formData.projectId || ''}
                    onChange={(e) => setFormData({ ...formData, projectId: Number(e.target.value) })}
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
                </FormControl>
                
                {projects.length === 0 && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No projects found for this company. Please create a new project.
                  </Alert>
                )}
              </Box>
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
          </Box>
        );
      
      case 2: // Upload Media
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Upload Portrait Image</Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
              Upload a high-quality image for AR recognition. Supported formats: JPG, PNG (recommended 1920x1080)
            </Typography>
            
            {formData.portrait ? (
              <Card sx={{ mb: 2 }}>
                <CardMedia
                  component="img"
                  height="200"
                  image={URL.createObjectURL(formData.portrait)}
                  alt="Portrait preview"
                />
                <CardContent>
                  <Typography variant="subtitle2">{formData.portrait.name}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    {(formData.portrait.size / 1024 / 1024).toFixed(2)} MB
                  </Typography>
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
                  onChange={handlePortraitChange}
                  style={{ display: 'none' }}
                  id="portrait-upload"
                  disabled={loading}
                />
                <label htmlFor="portrait-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<UploadIcon />}
                    disabled={loading}
                  >
                    Select Portrait Image
                  </Button>
                </label>
              </Box>
            )}
            
            <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>Upload Videos</Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
              Upload one or more videos for AR playback. Supported formats: MP4, MOV, AVI
            </Typography>
            
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
                onChange={handleVideosChange}
                style={{ display: 'none' }}
                id="videos-upload"
                multiple
                disabled={loading}
              />
              <label htmlFor="videos-upload">
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<UploadIcon />}
                  disabled={loading}
                >
                  Select Videos
                </Button>
              </label>
            </Box>
            
            {formData.videos.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Selected Videos ({formData.videos.length})
                </Typography>
                {formData.videos.map((video, index) => (
                  <Card key={index} sx={{ mb: 1 }}>
                    <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="subtitle2">{video.name}</Typography>
                        <Typography variant="body2" color="textSecondary">
                          {(video.size / 1024 / 1024).toFixed(2)} MB
                        </Typography>
                      </Box>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => removeVideo(index)}
                        disabled={loading}
                      >
                        Remove
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}
          </Box>
        );
      
      case 3: // Generate Marker
        return (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <QrCodeIcon sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />
            <Typography variant="h6" gutterBottom>Marker Generation</Typography>
            <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
              The AR marker will be automatically generated after content creation. 
              You can also manually regenerate it later if needed.
            </Typography>
            <Alert severity="info">
              Marker generation happens in the background and may take a few minutes to complete.
            </Alert>
          </Box>
        );
      
      case 4: // Video Schedule
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Video Rotation Schedule</Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
              Configure when and how your videos should play in the AR experience.
            </Typography>
            
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
          </Box>
        );
      
      case 5: // Playback Duration
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Playback Duration</Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
              Select how long the AR content should remain active and playable.
            </Typography>
            
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
          </Box>
        );
      
      case 6: // Publish
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Review & Publish</Typography>
            
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Content Details</Typography>
                <Typography variant="body1"><strong>Title:</strong> {formData.title || 'Not set'}</Typography>
                <Typography variant="body1"><strong>Description:</strong> {formData.description || 'Not set'}</Typography>
              </CardContent>
            </Card>
            
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Customer Information</Typography>
                <Typography variant="body1"><strong>Name:</strong> {formData.customerName || 'Not set'}</Typography>
                <Typography variant="body1"><strong>Email:</strong> {formData.customerEmail || 'Not set'}</Typography>
                <Typography variant="body1"><strong>Phone:</strong> {formData.customerPhone || 'Not set'}</Typography>
              </CardContent>
            </Card>
            
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Company & Project</Typography>
                <Typography variant="body1">
                  <strong>Company:</strong> {companies.find(c => c.id === formData.companyId)?.name || 'Not set'}
                </Typography>
                {formData.creatingNewProject ? (
                  <Typography variant="body1"><strong>New Project:</strong> {formData.newProjectName}</Typography>
                ) : (
                  <Typography variant="body1">
                    <strong>Project:</strong> {projects.find(p => p.id === formData.projectId)?.name || 'Not set'}
                  </Typography>
                )}
              </CardContent>
            </Card>
            
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Media</Typography>
                <Typography variant="body1"><strong>Portrait:</strong> {formData.portrait ? 'Selected' : 'Not selected'}</Typography>
                <Typography variant="body1"><strong>Videos:</strong> {formData.videos.length} selected</Typography>
              </CardContent>
            </Card>
            
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Schedule</Typography>
                <Typography variant="body1"><strong>Type:</strong> {formData.scheduleType}</Typography>
                <Typography variant="body1"><strong>Time:</strong> {formData.scheduleTime}</Typography>
                <Typography variant="body1"><strong>Duration:</strong> {
                  formData.playbackDuration === '1_year' ? '1 Year' :
                  formData.playbackDuration === '3_years' ? '3 Years' : '5 Years'
                }</Typography>
              </CardContent>
            </Card>
            
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Checkbox
                checked={formData.isActive}
                onChange={(e) => setFormData({ ...formData, isActive: e.target.checked })}
                id="publish-checkbox"
              />
              <label htmlFor="publish-checkbox" style={{ marginLeft: 8 }}>
                Publish and activate immediately
              </label>
            </Box>
          </Box>
        );
      
      default:
        return 'Unknown step';
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<BackIcon />}
          onClick={() => {
            if (projectId) {
              navigate(`/projects/${projectId}/content`);
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
        <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {getStepContent(activeStep)}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
          <Button
            disabled={activeStep === 0 || loading}
            onClick={handleBack}
          >
            Back
          </Button>
          
          {activeStep === steps.length - 1 ? (
            <Button
              variant="contained"
              color="primary"
              onClick={handleSubmit}
              startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create AR Content'}
            </Button>
          ) : (
            <Button
              variant="contained"
              color="primary"
              onClick={handleNext}
              endIcon={<BackIcon style={{ transform: 'rotate(180deg)' }} />}
            >
              Next
            </Button>
          )}
        </Box>
      </Paper>
    </Box>
  );
}