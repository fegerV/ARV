import React, { useEffect, useState } from 'react';
import { Alert as MuiAlert, Chip, Box, Stack, Typography } from '@mui/material';

export type Alert = {
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  services?: string[];
};

const wsUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}/ws/alerts`;
};

const SystemAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    const ws = new WebSocket(wsUrl());

    ws.onopen = () => {
      // Request permission for desktop notifications
      if (Notification.permission === 'default') {
        Notification.requestPermission();
      }
    };

    ws.onmessage = (event) => {
      try {
        const newAlert: Alert = JSON.parse(event.data);
        setAlerts((prev) => [newAlert, ...prev].slice(0, 10));

        if (Notification.permission === 'granted') {
          new Notification(newAlert.title, { body: newAlert.message });
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      // optional: show connection error
    };

    return () => {
      ws.close();
    };
  }, []);

  if (alerts.length === 0) {
    return null;
  }

  const latest = alerts[0];

  return (
    <Box sx={{ mb: 2 }}>
      <MuiAlert severity={latest.severity === 'critical' ? 'error' : latest.severity === 'warning' ? 'warning' : 'info'}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Typography component="span">🚨 {alerts.length} Active Alerts</Typography>
          <Chip label={latest.title} size="small" />
        </Stack>
      </MuiAlert>
    </Box>
  );
};

export default SystemAlerts;
