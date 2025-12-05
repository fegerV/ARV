import { Box, Typography, Button, Paper } from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

export default function CompaniesList() {
  const navigate = useNavigate();

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Companies</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/companies/new')}
        >
          New Company
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Typography>Companies list будет здесь...</Typography>
      </Paper>
    </Box>
  );
}
