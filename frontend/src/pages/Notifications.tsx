import { Box, Typography, Paper } from '@mui/material';

export default function Notifications() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Notifications</Typography>
      <Paper sx={{ p: 3 }}>
        <Typography>Notifications settings будут здесь...</Typography>
      </Paper>
    </Box>
  );
}
