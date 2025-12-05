import { Box, Typography, Paper } from '@mui/material';

export default function CompanyDetails() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Company Details</Typography>
      <Paper sx={{ p: 3 }}>
        <Typography>Company details будут здесь...</Typography>
      </Paper>
    </Box>
  );
}
