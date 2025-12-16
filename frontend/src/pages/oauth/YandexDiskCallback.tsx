import { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  CircularProgress,
  Alert,
} from '@mui/material';
import { CloudQueue as CloudIcon } from '@mui/icons-material';

interface OAuthMessageData {
  connectionId?: number;
  error?: string;
}

export default function YandexDiskCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const success = searchParams.get('success');
    const connectionId = searchParams.get('connectionId');
    const error = searchParams.get('error');

    // Function to send message to opener window
    const sendMessage = (type: string, data: OAuthMessageData) => {
      if (window.opener && !window.opener.closed) {
        try {
          window.opener.postMessage(
            {
              type,
              data,
            },
            window.location.origin
          );
        } catch (err) {
          console.error('Failed to send message to opener:', err);
        }
      }
    };

    // Process the callback result
    if (success === 'true' && connectionId) {
      sendMessage('YANDEX_OAUTH_SUCCESS', {
        connectionId: parseInt(connectionId, 10),
      });

      // Show success message briefly before closing
      setTimeout(() => {
        window.close();
      }, 2000);

    } else if (error) {
      sendMessage('YANDEX_OAUTH_ERROR', {
        error: decodeURIComponent(error),
      });

      // Show error message briefly before closing
      setTimeout(() => {
        window.close();
      }, 3000);

    } else {
      // Handle unexpected callback parameters
      sendMessage('YANDEX_OAUTH_ERROR', {
        error: 'Invalid callback parameters received',
      });

      setTimeout(() => {
        window.close();
      }, 3000);
    }
  }, [searchParams, navigate]);

  const success = searchParams.get('success');
  const error = searchParams.get('error');

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f5f5f5',
        p: 2,
      }}
    >
      <Paper
        elevation={3}
        sx={{
          p: 4,
          maxWidth: 400,
          width: '100%',
          textAlign: 'center',
        }}
      >
        <CloudIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />

        {success === 'true' ? (
          <>
            <Typography variant="h5" gutterBottom color="success.main">
              Authorization Successful!
            </Typography>
            <Typography variant="body1" color="textSecondary" paragraph>
              Your Yandex Disk has been successfully connected.
            </Typography>
            <Typography variant="body2" color="textSecondary">
              This window will close automatically...
            </Typography>
          </>
        ) : error ? (
          <>
            <Typography variant="h5" gutterBottom color="error.main">
              Authorization Failed
            </Typography>
            <Alert severity="error" sx={{ mb: 2 }}>
              {decodeURIComponent(error)}
            </Alert>
            <Typography variant="body2" color="textSecondary">
              This window will close automatically...
            </Typography>
          </>
        ) : (
          <>
            <CircularProgress size={40} sx={{ mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              Processing Authorization...
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Please wait while we process your authorization.
            </Typography>
          </>
        )}

        <Box mt={3}>
          <Typography variant="caption" color="textSecondary">
            If this window doesn't close automatically, you can close it manually.
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
}