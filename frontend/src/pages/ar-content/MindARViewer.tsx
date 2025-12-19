import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Box, Typography, Paper, Button, CircularProgress, Alert, IconButton } from '@mui/material';
import { useToast } from '../../store/useToast';
import { arContentAPI } from '../../services/api';
import { Close as CloseIcon } from '@mui/icons-material';

interface ARContentData {
  id: number;
  order_number: string;
  marker_url?: string | null;
  marker_status?: string | null;
  photo_url?: string;
  thumbnail_url?: string;
  video_url?: string;
  company_name?: string;
  project_name?: string;
  customer_name?: string;
}

const MindARViewer = () => {
  const { uniqueId } = useParams<{ uniqueId: string }>();
  const { addToast } = useToast();
  const [content, setContent] = useState<ARContentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
    const [arReady, setArReady] = useState(false);
    const [arSupported, setArSupported] = useState(true);
    
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
  
    // Fetch AR content data
    useEffect(() => {
      const fetchContent = async () => {
        try {
          if (!uniqueId) {
            throw new Error('Unique ID not provided');
          }
          
          // Use the existing getDetail API but with the uniqueId
          // We'll need to create a new API endpoint for this, for now using a direct API call
          const response = await arContentAPI.getDetail(uniqueId);
          setContent(response.data);
          
          // Check if this is actually a valid AR content with marker
          if (!response.data.marker_url) {
            if (response.data.marker_status === 'pending') {
              addToast('AR marker is being generated. Please try again later.', 'info');
            } else {
              throw new Error('AR marker not available');
            }
          }
        } catch (err: any) {
          console.error('Error fetching AR content:', err);
          setError(err.message || 'Failed to load AR content');
          addToast('Failed to load AR content', 'error');
        } finally {
          setLoading(false);
        }
      };
  
      fetchContent();
    }, [uniqueId, addToast]);

  // Initialize MindAR when content is loaded
  useEffect(() => {
    if (!content || !content.marker_url || loading) return;

    const initAR = async () => {
      try {
        // Check if MindAR is available
        if (typeof window !== 'undefined' && !(window as any).MINDAR) {
          // Dynamically load MindAR if not available
          const script = document.createElement('script');
          script.src = 'https://cdn.jsdelivr.net/gh/hiukim/mind-ar-js@1.2.5/dist/mindar-image.prod.js';
          script.async = true;
          document.head.appendChild(script);

          script.onload = () => {
            initializeMindAR();
          };
          
          script.onerror = () => {
            setArSupported(false);
            setError('Failed to load AR library');
          };
        } else {
          initializeMindAR();
        }
      } catch (err) {
        console.error('Error initializing AR:', err);
        setError('Error initializing AR viewer');
      }
    };

    const initializeMindAR = () => {
      // MindAR initialization would go here
      // For now, we'll just simulate the initialization
      setTimeout(() => {
        setArReady(true);
      }, 1000);
    };

    initAR();
  }, [content, loading]);

  if (loading) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        backgroundColor: '#000',
        color: '#fff'
      }}>
        <CircularProgress color="primary" />
        <Typography sx={{ ml: 2 }}>Loading AR experience...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        backgroundColor: '#000',
        color: '#fff',
        p: 2
      }}>
        <Alert severity="error" sx={{ width: '100%', maxWidth: 600 }}>
          <Typography variant="h6">Error loading AR experience</Typography>
          <Typography>{error}</Typography>
          <Button 
            variant="outlined" 
            sx={{ mt: 2 }} 
            onClick={() => window.history.back()}
          >
            Go Back
          </Button>
        </Alert>
      </Box>
    );
  }

  if (!arSupported) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        backgroundColor: '#000',
        color: '#fff',
        p: 2
      }}>
        <Alert severity="error" sx={{ width: '100%', maxWidth: 600 }}>
          <Typography variant="h6">AR Not Supported</Typography>
          <Typography>AR features are not supported on this device or browser.</Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            Please try using Chrome on Android or Safari on iOS for the best experience.
          </Typography>
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      position: 'relative',
      width: '100vw',
      height: '100vh',
      backgroundColor: '#000',
      overflow: 'hidden'
    }}>
      {/* AR Canvas */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 1
        }}
      >
        {!arReady ? (
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            height: '100%',
            backgroundColor: '#000',
            color: '#fff'
          }}>
            <CircularProgress color="primary" />
            <Typography sx={{ ml: 2 }}>Initializing AR experience...</Typography>
          </Box>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        )}
      </Box>

      {/* Content Info Overlay */}
      <Box sx={{ 
        position: 'absolute', 
        top: 16, 
        left: 16, 
        right: 16,
        zIndex: 10,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start'
      }}>
        <Paper 
          sx={{ 
            p: 2, 
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            color: '#fff',
            borderRadius: 2
          }}
        >
          <Typography variant="h6" sx={{ color: '#fff' }}>
            {content?.order_number || 'AR Experience'}
          </Typography>
          {content?.company_name && (
            <Typography variant="body2" sx={{ color: '#ccc' }}>
              {content.company_name}
            </Typography>
          )}
        </Paper>
        
        <IconButton
          onClick={() => window.history.back()}
          sx={{ 
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            color: '#fff',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.2)'
            }
          }}
        >
          <CloseIcon />
        </IconButton>
      </Box>

      {/* AR Ready Overlay */}
      {arReady && (
        <Box sx={{ 
          position: 'absolute', 
          bottom: 32, 
          left: '50%', 
          transform: 'translateX(-50%)',
          zIndex: 10,
          textAlign: 'center'
        }}>
          <Paper 
            sx={{ 
              p: 2, 
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              color: '#fff',
              borderRadius: 2
            }}
          >
            <Typography variant="body1">
              Point your camera at the AR marker to begin
            </Typography>
            <Typography variant="caption" sx={{ color: '#ccc', mt: 1, display: 'block' }}>
              Make sure your environment is well lit
            </Typography>
          </Paper>
        </Box>
      )}

      {/* Camera Permission Prompt */}
      {!arReady && (
        <Box sx={{ 
          position: 'absolute', 
          top: '50%', 
          left: '50%', 
          transform: 'translate(-50%, -50%)',
          zIndex: 10,
          textAlign: 'center',
          color: '#fff'
        }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Camera Permission Required
          </Typography>
          <Typography variant="body2" sx={{ mb: 2, color: '#ccc' }}>
            This AR experience requires access to your camera
          </Typography>
          <Button 
            variant="contained" 
            onClick={() => {
              // In a real implementation, this would trigger camera access
              // For now, we'll just simulate it
              setArReady(true);
            }}
          >
            Enable Camera
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default MindARViewer;