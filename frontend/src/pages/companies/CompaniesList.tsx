import { Box, Typography, Button, Paper, Table, TableHead, TableBody, TableRow, TableCell, Chip } from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

// Mock data for companies including the default Vertex AR company
const mockCompanies = [
  {
    id: 1,
    name: 'Vertex AR',
    slug: 'vertex-ar',
    contact_email: 'admin@vertexar.com',
    storage_provider: 'Local Storage',
    is_default: true,
    status: 'active',
    projects_count: 5,
    created_at: '2025-01-01',
  },
];

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
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Contact Email</TableCell>
              <TableCell>Storage Provider</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Projects</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {mockCompanies.map((company) => (
              <TableRow key={company.id} hover>
                <TableCell>
                  <Typography variant="subtitle2">
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
                  </Typography>
                </TableCell>
                <TableCell>{company.contact_email}</TableCell>
                <TableCell>{company.storage_provider}</TableCell>
                <TableCell>
                  <Chip 
                    label={company.status} 
                    size="small" 
                    color={company.status === 'active' ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell>{company.projects_count}</TableCell>
                <TableCell>{company.created_at}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
