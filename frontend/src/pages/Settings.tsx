import { Box, Typography, Paper } from '@mui/material';

export default function Settings() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Settings</Typography>
      <Paper sx={{ p: 3 }}>
        <Typography>System settings будут здесь...</Typography>
      </Paper>
    </Box>
  );
}
