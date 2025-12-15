import { useState, useEffect, useCallback, type ChangeEvent } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  Table, 
  TableHead, 
  TableBody, 
  TableRow, 
  TableCell, 
  Chip, 
  IconButton,
  TableContainer,
  TablePagination,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  OutlinedInput,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  Avatar,
  CircularProgress,
  Alert,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import { 
  Add as AddIcon, 
  Search as SearchIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  QrCode as QrCodeIcon,
  ContentCopy as CopyIcon,
  OpenInNew as OpenIcon,
  CheckCircle as CheckCircleIcon,
  HourglassEmpty as HourglassEmptyIcon,
  Error as ErrorIcon,
  CloudDownload as ExportIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import QRCode from 'qrcode.react';
import { arContentAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

interface ARContentItem {
  id: string;
  order_number: string;
  company_name: string;
  company_id: string;
  project_id: string;
  project_name: string;
  created_at: string;
  status: string;
  customer_name?: string;
  customer_phone?: string;
  customer_email?: string;
  thumbnail_url?: string;
  active_video_title?: string | null;
  views_count: number;
  views_30_days?: number;
  public_url?: string;
  has_qr_code?: boolean;
  qr_code_url?: string;
}

// No mock data needed - using real API

export default function ARContentList() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [contentList, setContentList] = useState<ARContentItem[]>([]);
  const [filteredContentList, setFilteredContentList] = useState<ARContentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [qrDialogOpen, setQrDialogOpen] = useState(false);
  const [selectedContent, setSelectedContent] = useState<ARContentItem | null>(null);
  
  const fetchContentList = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await arContentAPI.listAll({ page: 1, page_size: 200 });
      setContentList(response.data.items || []);
      setFilteredContentList(response.data.items || []);
    } catch (error) {
      console.error('Error fetching AR content:', error);
      const msg = (error as any)?.response?.data?.detail || (error as any)?.response?.data?.message || 'Failed to load AR content';
      setError(msg);
      addToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  // Load data
  useEffect(() => {
    fetchContentList();
  }, [fetchContentList]);

  // Filter content based on search term, selected companies, and statuses
  useEffect(() => {
    let filtered = contentList;
    
    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter((item: ARContentItem) => 
        item.order_number.toLowerCase().includes(term) ||
        (item.customer_name && item.customer_name.toLowerCase().includes(term)) ||
        (item.customer_email && item.customer_email.toLowerCase().includes(term)) ||
        (item.customer_phone && item.customer_phone.toLowerCase().includes(term)) ||
        item.company_name.toLowerCase().includes(term) ||
        item.project_name.toLowerCase().includes(term) ||
        ((item.active_video_title || '').toLowerCase().includes(term))
      );
    }
    
    // Apply company filter
    if (selectedCompanies.length > 0) {
      filtered = filtered.filter((item: ARContentItem) => selectedCompanies.includes(item.company_name));
    }
    
    // Apply status filter
    if (selectedStatuses.length > 0) {
      filtered = filtered.filter((item: ARContentItem) => selectedStatuses.includes(item.status));
    }
    
    setFilteredContentList(filtered);
    setPage(0); // Reset to first page when filters change
  }, [searchTerm, selectedCompanies, selectedStatuses, contentList]);

  const handleNewContent = () => {
    navigate(`/ar-content/new`);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleCopyLink = async (url: string) => {
    if (!url) {
      addToast('Link is missing', 'error');
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      addToast('Link copied to clipboard', 'success');
    } catch {
      addToast('Failed to copy link', 'error');
    }
  };

  const handleOpenLink = (url: string) => {
    if (!url) {
      addToast('Link is missing', 'error');
      return;
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleShowQR = (content: ARContentItem) => {
    if (!content.public_url) {
      addToast('Link is missing — QR cannot be shown', 'error');
      return;
    }
    setSelectedContent(content);
    setQrDialogOpen(true);
  };

  const handleCloseQR = () => {
    setQrDialogOpen(false);
    setSelectedContent(null);
  };

  const handleEdit = (id: string) => {
    navigate(`/ar-content/${id}`);
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this AR content? This action cannot be undone.')) {
      try {
        addToast('Delete is not wired yet (no DELETE endpoint for flat AR content in UI)', 'warning');
      } catch (error) {
        console.error('Error deleting AR content:', error);
        addToast('Failed to delete AR content', 'error');
      }
    }
  };

  const handleExport = () => {
    // TODO: Implement export functionality
    addToast('Export functionality not implemented yet', 'warning');
  };

  const handleRefresh = async () => {
    await fetchContentList();
  };

  // Get unique companies and statuses for filters
  const uniqueCompanies = Array.from(new Set(contentList.map((item: ARContentItem) => item.company_name)));
  const uniqueStatuses = Array.from(new Set(contentList.map((item: ARContentItem) => item.status)));

  // Status chip rendering
  const getStatusChip = (status: string) => {
    switch (status) {
      case 'ready':
      case 'generated':
        return <Chip icon={<CheckCircleIcon />} label={status} color="success" size="small" />;
      case 'processing':
      case 'pending':
        return <Chip icon={<HourglassEmptyIcon />} label={status} color="warning" size="small" />;
      case 'failed':
        return <Chip icon={<ErrorIcon />} label={status} color="error" size="small" />;
      default:
        return <Chip label={status} size="small" />;
    }
  };

  // Pagination
  const paginatedContent = filteredContentList.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">All AR Content</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={loading ? <CircularProgress size={18} /> : <RefreshIcon />}
            onClick={handleRefresh}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleNewContent}
            disabled={loading}
          >
            New AR Content
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Filters and Search */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Search */}
          <TextField
            placeholder="Search..."
            value={searchTerm}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ minWidth: 250 }}
          />
          
          {/* Company Filter */}
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Companies</InputLabel>
            <Select
              multiple
              value={selectedCompanies}
              onChange={(e: SelectChangeEvent<typeof selectedCompanies>) => setSelectedCompanies(e.target.value as string[])}
              input={<OutlinedInput label="Companies" />}
              renderValue={(selected: any) => (selected as string[]).join(', ')}
            >
              {uniqueCompanies.map((company) => (
                <MenuItem key={company} value={company}>
                  <Checkbox checked={selectedCompanies.indexOf(company) > -1} />
                  <ListItemText primary={company} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          {/* Status Filter */}
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Statuses</InputLabel>
            <Select
              multiple
              value={selectedStatuses}
              onChange={(e: SelectChangeEvent<typeof selectedStatuses>) => setSelectedStatuses(e.target.value as string[])}
              input={<OutlinedInput label="Statuses" />}
              renderValue={(selected: any) => (selected as string[]).join(', ')}
            >
              {uniqueStatuses.map((status) => (
                <MenuItem key={status} value={status}>
                  <Checkbox checked={selectedStatuses.indexOf(status) > -1} />
                  <ListItemText primary={status} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          {/* Export Button */}
          <Button
            variant="outlined"
            startIcon={<ExportIcon />}
            onClick={handleExport}
          >
            Export
          </Button>
        </Box>
      </Paper>

      {/* Content Table */}
      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Company</TableCell>
                <TableCell>Order Number</TableCell>
                <TableCell>Created At</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Thumbnail</TableCell>
                <TableCell>Active Video</TableCell>
                <TableCell>Customer</TableCell>
                <TableCell>Views</TableCell>
                <TableCell>Link</TableCell>
                <TableCell>QR Code</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedContent.map((item: ARContentItem) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.company_name}</TableCell>
                  <TableCell>
                    <Typography variant="subtitle2">{item.order_number}</Typography>
                  </TableCell>
                  <TableCell>{new Date(item.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>{getStatusChip(item.status)}</TableCell>
                  <TableCell>
                    <Avatar
                      variant="rounded"
                      src={item.thumbnail_url}
                      sx={{ width: 40, height: 40 }}
                    />
                  </TableCell>
                  <TableCell>{item.active_video_title || '—'}</TableCell>
                  <TableCell>
                    <Typography variant="body2">{item.customer_name || '—'}</Typography>
                    <Typography variant="caption" color="textSecondary">{item.customer_phone || ''}</Typography>
                    <Typography variant="caption" color="textSecondary" sx={{ display: 'block' }}>{item.customer_email || ''}</Typography>
                  </TableCell>
                  <TableCell>{item.views_30_days ?? item.views_count}</TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => handleCopyLink(item.public_url || '')} disabled={!item.public_url}>
                      <CopyIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => handleOpenLink(item.public_url || '')} disabled={!item.public_url}>
                      <OpenIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => handleShowQR(item)} disabled={!item.public_url}>
                      <QrCodeIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Edit">
                      <IconButton size="small" onClick={() => handleEdit(item.id)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton size="small" onClick={() => handleDelete(item.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
              
              {paginatedContent.length === 0 && (
                <TableRow>
                  <TableCell colSpan={13} align="center">
                    <Typography>No AR content found</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        
        {/* Pagination */}
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={filteredContentList.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
        )}
      </Paper>

      {/* QR Code Dialog */}
      <Dialog open={qrDialogOpen} onClose={handleCloseQR} maxWidth="sm" fullWidth>
        <DialogTitle>QR Code</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, py: 3 }}>
          {selectedContent && (
            <>
              <QRCode value={selectedContent.public_url || ''} size={200} />
              <Typography variant="body2" color="textSecondary">{selectedContent.public_url}</Typography>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => handleCopyLink(selectedContent?.public_url || '')}
            disabled={!selectedContent?.public_url}
          >
            Copy Link
          </Button>
          <Button onClick={handleCloseQR}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}