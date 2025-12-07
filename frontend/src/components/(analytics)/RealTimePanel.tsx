// src/components/(analytics)/RealTimePanel.tsx
import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  Divider,
  Box,
  Chip,
} from '@mui/material';
import { useWebSocket } from '@/hooks/useWebSocket';

interface AnalyticsEvent {
  event_type: string;
  ar_content_id: number;
  company_id: number;
  project_id: number;
  device_type: string;
  browser: string;
  duration_seconds: number;
  avg_fps: number;
  tracking_quality: string;
  timestamp: string;
}

export const RealTimePanel: React.FC = () => {
  const [events, setEvents] = useState<AnalyticsEvent[]>([]);
  const [onlineCount, setOnlineCount] = useState(0);

  // Connect to WebSocket for real-time analytics
  const { lastMessage } = useWebSocket('/ws/analytics');

  useEffect(() => {
    if (lastMessage) {
      try {
        const eventData: AnalyticsEvent = JSON.parse(lastMessage);
        setEvents(prev => [eventData, ...prev.slice(0, 9)]); // Keep only last 10 events
        
        // Update online count based on event type
        if (eventData.event_type === 'ar_session_created') {
          setOnlineCount(prev => prev + 1);
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    }
  }, [lastMessage]);

  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Real-Time Analytics</Typography>
        <Chip 
          label={`${onlineCount} online`} 
          color="primary" 
          variant="outlined" 
        />
      </Box>

      <Divider sx={{ mb: 2 }} />

      {events.length === 0 ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="200px">
          <Typography color="textSecondary">No real-time events yet</Typography>
        </Box>
      ) : (
        <List>
          {events.map((event, index) => (
            <React.Fragment key={index}>
              <ListItem alignItems="flex-start">
                <ListItemText
                  primary={
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" fontWeight="medium">
                        {event.event_type.replace('_', ' ')}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </Typography>
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography
                        component="span"
                        variant="body2"
                        color="textPrimary"
                      >
                        Device: {event.device_type || 'Unknown'} | Browser: {event.browser || 'Unknown'}
                      </Typography>
                      <br />
                      <Typography
                        component="span"
                        variant="body2"
                        color="textPrimary"
                      >
                        Duration: {event.duration_seconds || 0}s | FPS: {event.avg_fps || 0}
                      </Typography>
                      <br />
                      <Chip 
                        label={event.tracking_quality || 'unknown'} 
                        size="small" 
                        color={event.tracking_quality === 'good' ? 'success' : 'warning'}
                        variant="outlined"
                      />
                    </Box>
                  }
                />
              </ListItem>
              {index < events.length - 1 && <Divider component="li" />}
            </React.Fragment>
          ))}
        </List>
      )}
    </Paper>
  );
};