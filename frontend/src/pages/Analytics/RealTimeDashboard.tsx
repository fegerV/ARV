// src/pages/Analytics/RealTimeDashboard.tsx
import React from 'react';
import {
  Container,
  Grid,
  Typography,
  Box,
} from '@mui/material';
import { RealTimePanel } from '@/components/(analytics)/RealTimePanel';

const RealTimeDashboard: React.FC = () => {
  return (
    <Container maxWidth={false}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Real-Time Analytics</Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <RealTimePanel />
        </Grid>
      </Grid>
    </Container>
  );
};

export default RealTimeDashboard;