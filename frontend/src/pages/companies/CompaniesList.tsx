import { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Chip,
  TextField,
  InputAdornment,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert
} from '@mui/material';
import { 
  Add as AddIcon,
  Search as SearchIcon,
  Clear as ClearIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { companiesAPI } from '../../services/api';
import { companiesApi } from '../../services/companies';

interface Company {
  id: number;
  name: string;
  slug: string;
  is_default: boolean;
  is_active: boolean;
  storage_connection_id: number;
  storage_path: string;
  created_at: string;
  updated_at: string;
  contact_email?: string;
  contact_phone?: string;
  storage_quota_gb?: number;
  storage_used_gb?: number;
}

interface StorageConnection {
  id: number;
  name: string;
  provider: 'local_disk' | 'minio' | 'yandex_disk';
  is_active: boolean;
}

// Mapping for storage providers
const getStorageProvider = (connectionId: number, storageConnections: StorageConnection[]): string => {
  const connection = storageConnections.find(conn => conn.id === connectionId);
  if (!connection) return 'Unknown';
  
  switch (connection.provider) {
    case 'local_disk':
      return 'Local Disk';
    case 'minio':
      return 'MinIO';
    case 'yandex_disk':
      return 'Yandex Disk';
    default:
      return connection.provider;
  }
};

export default function CompaniesList() {
  const navigate = useNavigate();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [storageConnections, setStorageConnections] = useState<StorageConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [typeFilter, setTypeFilter] = useState<'all' | 'default' | 'client'>('all');

  // Fetch storage connections
  useEffect(() => {
    const fetchStorageConnections = async () => {
      try {
        const response = await companiesApi.storageConnections();
        setStorageConnections(response.data);
      } catch (err) {
        console.error('Failed to fetch storage connections:', err);
      }
    };

    fetchStorageConnections();
  }, []);

  // Fetch companies
  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await companiesAPI.list({ include_default: true });
        setCompanies(response.data);
      } catch (err) {
        console.error('Failed to fetch companies:', err);
        setError('Failed to load companies. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchCompanies();
  }, []);

  // Filter companies based on search term and filters
  const filteredCompanies = companies.filter(company => {
    // Search filter
    const matchesSearch = !searchTerm || 
      company.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      company.slug.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (company.contact_email && company.contact_email.toLowerCase().includes(searchTerm.toLowerCase()));
    
    // Status filter
    const matchesStatus = statusFilter === 'all' || 
      (statusFilter === 'active' && company.is_active) ||
      (statusFilter === 'inactive' && !company.is_active);
    
    // Type filter
    const matchesType = typeFilter === 'all' ||
      (typeFilter === 'default' && company.is_default) ||
      (typeFilter === 'client' && !company.is_default);
    
    return matchesSearch && matchesStatus && matchesType;
  });

  const handleSearchClear = () => {
    setSearchTerm('');
  };

  const handleStatusFilterChange = (value: 'all' | 'active' | 'inactive') => {
    setStatusFilter(value);
  };

  const handleTypeFilterChange = (value: 'all' | 'default' | 'client') => {
    setTypeFilter(value);
  };

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

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Search */}
          <TextField
            size="small"
            placeholder="Search companies..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
              endAdornment: searchTerm ? (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={handleSearchClear}>
                    <ClearIcon />
                  </IconButton>
                </InputAdornment>
              ) : null,
            }}
            sx={{ minWidth: 250 }}
          />

          {/* Status Filter */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => handleStatusFilterChange(e.target.value as any)}
            >
              <MenuItem value="all">All Statuses</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="inactive">Inactive</MenuItem>
            </Select>
          </FormControl>

          {/* Type Filter */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Type</InputLabel>
            <Select
              value={typeFilter}
              label="Type"
              onChange={(e) => handleTypeFilterChange(e.target.value as any)}
            >
              <MenuItem value="all">All Types</MenuItem>
              <MenuItem value="default">Default</MenuItem>
              <MenuItem value="client">Client</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* Companies Table */}
      <Paper sx={{ p: 3 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : filteredCompanies.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 5 }}>
            <Typography>No companies found.</Typography>
            {searchTerm && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                No companies match your search criteria.
              </Typography>
            )}
          </Box>
        ) : (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Showing {filteredCompanies.length} of {companies.length} companies
            </Typography>
            
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Slug</TableCell>
                    <TableCell>Contact</TableCell>
                    <TableCell>Storage</TableCell>
                    <TableCell>Usage</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Created</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredCompanies.map((company) => (
                    <TableRow 
                      key={company.id} 
                      hover 
                      onClick={() => navigate(`/companies/${company.id}`)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell>
                        <Typography fontWeight="medium">{company.name}</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {company.slug}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {company.contact_email ? (
                          <Typography variant="body2">{company.contact_email}</Typography>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            No contact
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {getStorageProvider(company.storage_connection_id, storageConnections)}
                      </TableCell>
                      <TableCell>
                        {company.storage_used_gb !== undefined && company.storage_quota_gb ? (
                          <Typography variant="body2">
                            {company.storage_used_gb.toFixed(1)} GB / {company.storage_quota_gb} GB
                          </Typography>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            N/A
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={company.is_active ? 'Active' : 'Inactive'} 
                          color={company.is_active ? 'success' : 'default'} 
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={company.is_default ? 'Default' : 'Client'} 
                          color={company.is_default ? 'primary' : 'secondary'} 
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {new Date(company.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </Paper>
    </Box>
  );
}