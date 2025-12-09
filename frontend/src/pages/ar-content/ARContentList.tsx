import { useState, useEffect } from 'react';
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
  Avatar
} from '@mui/material';
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
  CloudDownload as ExportIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import QRCode from 'qrcode.react';
import { arContentAPI } from '../../services/api';
import { useToast } from '../../store/useToast';

interface ARContentItem {
  id: number;
  unique_id: string;
  order_number: string;
  title: string;
  marker_status: string;
  image_url: string;
  created_at: string;
  is_active: boolean;
  client_name: string;
  client_phone: string;
  client_email: string;
  views: number;
  project: {
    id: number;
    name: string;
  };
  company: {
    id: number;
    name: string;
  };
  active_video: {
    id: number;
    title: string;
  };
}

// Mock data for testing
const mockData: ARContentItem[] = [
  {
    id: 1,
    unique_id: 'abc123',
    order_number: '000001',
    title: 'Постер #1 - Санта с подарками',
    marker_status: 'ready',
    image_url: '/api/portraits/santa-poster.jpg',
    created_at: '2025-12-05T14:30:00',
    is_active: true,
    client_name: 'Светлана',
    client_phone: '+7 (999) 123-45-67',
    client_email: 'svetlana@example.com',
    views: 5,
    project: {
      id: 10,
      name: 'Новогодние постеры 2025'
    },
    company: {
      id: 1,
      name: 'Vertex AR'
    },
    active_video: {
      id: 1,
      title: 'Анимация 1'
    }
  },
  {
    id: 2,
    unique_id: 'def456',
    order_number: '000002',
    title: 'Постер #2 - Дед Мороз',
    marker_status: 'processing',
    image_url: '/api/portraits/ded-moroz-poster.jpg',
    created_at: '2025-12-06T10:15:00',
    is_active: true,
    client_name: 'Иван',
    client_phone: '+7 (999) 765-43-21',
    client_email: 'ivan@example.com',
    views: 12,
    project: {
      id: 10,
      name: 'Новогодние постеры 2025'
    },
    company: {
      id: 1,
      name: 'Vertex AR'
    },
    active_video: {
      id: 2,
      title: 'Анимация 2'
    }
  }
];

export default function ARContentList() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [contentList, setContentList] = useState<ARContentItem[]>(mockData);
  const [filteredContentList, setFilteredContentList] = useState<ARContentItem[]>(mockData);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [qrDialogOpen, setQrDialogOpen] = useState(false);
  const [selectedContent, setSelectedContent] = useState<ARContentItem | null>(null);
  
  // Load data
  useEffect(() => {
    fetchContentList();
  }, []);

  const fetchContentList = async () => {
    try {
      setLoading(true);
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // In a real implementation, we would use:
      // const response = await arContentAPI.listAll();
      // setContentList(response.data.items || []);
      // setFilteredContentList(response.data.items || []);
      
      // For now, we're using mock data
      setContentList(mockData);
      setFilteredContentList(mockData);
      
      if (mockData.length > 0) {
        addToast('AR content loaded successfully', 'success');
      }
    } catch (error) {
      console.error('Error fetching AR content:', error);
      addToast('Failed to load AR content', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Filter content based on search term, selected companies, and statuses
  useEffect(() => {
    let filtered = contentList;
    
    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(item => 
        item.order_number.toLowerCase().includes(term) ||
        item.title.toLowerCase().includes(term) ||
        (item.client_name && item.client_name.toLowerCase().includes(term)) ||
        (item.client_email && item.client_email.toLowerCase().includes(term)) ||
        item.client_phone.includes(term) ||
        item.company.name.toLowerCase().includes(term) ||
        item.project.name.toLowerCase().includes(term) ||
        (item.active_video.title && item.active_video.title.toLowerCase().includes(term))
      );
    }
    
    // Apply company filter
    if (selectedCompanies.length > 0) {
      filtered = filtered.filter(item => selectedCompanies.includes(item.company.name));
    }
    
    // Apply status filter
    if (selectedStatuses.length > 0) {
      filtered = filtered.filter(item => selectedStatuses.includes(item.marker_status));
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

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleCopyLink = (uniqueId: string) => {
    const link = `${window.location.origin}/ar/${uniqueId}`;
    navigator.clipboard.writeText(link);
    addToast('Link copied to clipboard', 'success');
  };

  const handleOpenLink = (uniqueId: string) => {
    const link = `${window.location.origin}/ar/${uniqueId}`;
    window.open(link, '_blank');
  };

  const handleShowQR = (content: ARContentItem) => {
    setSelectedContent(content);
    setQrDialogOpen(true);
  };

  const handleCloseQR = () => {
    setQrDialogOpen(false);
    setSelectedContent(null);
  };

  const handleEdit = (id: number) => {
    navigate(`/ar-content/${id}`);
  };

  const handleDelete = (id: number) => {
    // TODO: Implement delete functionality
    console.log('Delete content with ID:', id);
    addToast('Delete functionality not implemented yet', 'warning');
  };

  const handleExport = () => {
    // TODO: Implement export functionality
    addToast('Export functionality not implemented yet', 'warning');
  };

  // Get unique companies and statuses for filters
  const uniqueCompanies = Array.from(new Set(contentList.map(item => item.company.name)));
  const uniqueStatuses = Array.from(new Set(contentList.map(item => item.marker_status)));

  // Status chip rendering
  const getStatusChip = (status: string) => {
    switch (status) {
      case 'ready':
        return <Chip icon={<CheckCircleIcon />} label="Ready" color="success" size="small" />;
      case 'processing':
        return <Chip icon={<HourglassEmptyIcon />} label="Processing" color="warning" size="small" />;
      case 'failed':
        return <Chip icon={<ErrorIcon />} label="Failed" color="error" size="small" />;
      default:
        return <Chip label={status} size="small" />;
    }
  };

  // Pagination
  const paginatedContent = filteredContentList.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Typography>Loading AR content...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">All AR Content</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleNewContent}
        >
          New AR Content
        </Button>
      </Box>

      {/* Filters and Search */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Search */}
          <TextField
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
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
              onChange={(e) => setSelectedCompanies(e.target.value as string[])}
              input={<OutlinedInput label="Companies" />}
              renderValue={(selected) => (selected as string[]).join(', ')}
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
              onChange={(e) => setSelectedStatuses(e.target.value as string[])}
              input={<OutlinedInput label="Statuses" />}
              renderValue={(selected) => (selected as string[]).join(', ')}
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
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Компания</TableCell>
                <TableCell>Номер заказа</TableCell>
                <TableCell>Дата создания</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Фото</TableCell>
                <TableCell>Активное видео</TableCell>
                <TableCell>Имя заказчика</TableCell>
                <TableCell>Телефон</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Просмотры</TableCell>
                <TableCell>Ссылка</TableCell>
                <TableCell>QR-код</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedContent.map((content) => (
                <TableRow key={content.id} hover>
                  <TableCell>
                    <Chip label={content.company.name} size="small" />
                  </TableCell>
                  <TableCell>{content.order_number}</TableCell>
                  <TableCell>
                    {content.created_at 
                      ? new Date(content.created_at).toLocaleDateString('ru-RU') 
                      : 'N/A'}
                  </TableCell>
                  <TableCell>{getStatusChip(content.marker_status)}</TableCell>
                  <TableCell>
                    {content.image_url ? (
                      <Avatar 
                        src={content.image_url} 
                        variant="rounded" 
                        sx={{ width: 50, height: 50 }} 
                      />
                    ) : (
                      <Avatar variant="rounded" sx={{ width: 50, height: 50 }}>
                        ?
                      </Avatar>
                    )}
                  </TableCell>
                  <TableCell>
                    {content.active_video.title || 'Не выбрано'}
                  </TableCell>
                  <TableCell>{content.client_name || 'N/A'}</TableCell>
                  <TableCell>{content.client_phone || 'N/A'}</TableCell>
                  <TableCell>{content.client_email || 'N/A'}</TableCell>
                  <TableCell>{content.views}</TableCell>
                  <TableCell>
                    <Tooltip title="Copy link">
                      <IconButton 
                        size="small" 
                        onClick={() => handleCopyLink(content.unique_id)}
                      >
                        <CopyIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Open link">
                      <IconButton 
                        size="small" 
                        onClick={() => handleOpenLink(content.unique_id)}
                      >
                        <OpenIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Show QR code">
                      <IconButton 
                        size="small" 
                        onClick={() => handleShowQR(content)}
                      >
                        <QrCodeIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Edit">
                      <IconButton 
                        size="small" 
                        onClick={() => handleEdit(content.id)}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton 
                        size="small" 
                        onClick={() => handleDelete(content.id)}
                        color="error"
                      >
                        <DeleteIcon />
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
      </Paper>

      {/* QR Code Dialog */}
      {selectedContent && (
        <Dialog open={qrDialogOpen} onClose={handleCloseQR} maxWidth="sm" fullWidth>
          <DialogTitle>QR Code for {selectedContent.title}</DialogTitle>
          <DialogContent sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <QRCode 
              value={`${window.location.origin}/ar/${selectedContent.unique_id}`} 
              size={256}
              level="H"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseQR}>Close</Button>
          </DialogActions>
        </Dialog>
      )}
    </Box>
  );
}