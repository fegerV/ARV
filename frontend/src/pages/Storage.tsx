import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Button,
  LinearProgress,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import { CloudUpload as UploadIcon, Settings as SettingsIcon, Close as CloseIcon } from '@mui/icons-material';
import { useState } from 'react';

const storageConnections = [
  { id: 1, provider: 'Local Storage', company: 'Vertex AR', status: 'active', usage: '85GB', limit: '500GB' },
  { id: 2, provider: 'MinIO', company: 'Company A', status: 'active', usage: '120GB', limit: '1TB' },
  { id: 3, provider: 'Yandex Disk', company: 'Company B', status: 'active', usage: '45GB', limit: '500GB' },
  { id: 4, provider: 'MinIO', company: 'Company C', status: 'inactive', usage: '0GB', limit: '1TB' },
];

const storageStats = [
  { title: 'Total Storage', value: '250GB', limit: '2.5TB' },
  { title: 'Used Storage', value: '250GB', percent: 10 },
  { title: 'Active Connections', value: '3' },
  { title: 'Backup Status', value: 'OK', status: 'success' },
];

export default function Storage() {
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<any>(null);
  const [newConnectionDialog, setNewConnectionDialog] = useState(false);
  const [newConnection, setNewConnection] = useState({
    name: '',
    provider: 'minio',
    credentials: '',
  });

  const handleConfigureStorage = () => {
    setNewConnectionDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setSelectedConnection(null);
  };

  const handleCloseNewConnectionDialog = () => {
    setNewConnectionDialog(false);
    setNewConnection({ name: '', provider: 'minio', credentials: '' });
  };

  const handleSettingsClick = (connection: any) => {
    setSelectedConnection(connection);
    setOpenDialog(true);
  };

  const handleSaveNewConnection = () => {
    // TODO: Call API to create new storage connection
    console.log('Creating new storage connection:', newConnection);
    handleCloseNewConnectionDialog();
  };

  const handleSaveSettings = () => {
    // TODO: Call API to update storage connection
    console.log('Updating storage connection:', selectedConnection);
    handleCloseDialog();
  };

  return (
    <>
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              Storage Management
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Manage storage connections and usage
            </Typography>
          </Box>
          <Button variant="contained" startIcon={<SettingsIcon />} onClick={handleConfigureStorage}>
            Configure Storage
          </Button>
        </Box>

      {/* Storage Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {storageStats.map((stat, idx) => (
          <Grid item xs={12} sm={6} md={3} key={idx}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {stat.title}
                </Typography>
                <Typography variant="h5" sx={{ mb: 1 }}>
                  {stat.value}
                </Typography>
                {stat.percent !== undefined && (
                  <Box>
                    <LinearProgress variant="determinate" value={stat.percent} sx={{ mb: 1 }} />
                    <Typography variant="caption" color="textSecondary">
                      {stat.percent}% of {stat.limit}
                    </Typography>
                  </Box>
                )}
                {stat.status && (
                  <Chip
                    label={stat.status}
                    size="small"
                    color={stat.status === 'success' ? 'success' : 'default'}
                    variant="outlined"
                  />
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Storage Connections Table */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Storage Connections
        </Typography>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell>Provider</TableCell>
              <TableCell>Company</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Usage</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {storageConnections.map((connection) => (
              <TableRow key={connection.id} hover>
                <TableCell>{connection.provider}</TableCell>
                <TableCell>{connection.company}</TableCell>
                <TableCell>
                  <Chip
                    label={connection.status}
                    size="small"
                    color={connection.status === 'active' ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell>
                  <Box>
                    <Typography variant="body2">{connection.usage}</Typography>
                    <Typography variant="caption" color="textSecondary">
                      Limit: {connection.limit}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Button size="small" variant="outlined" onClick={() => handleSettingsClick(connection)}>
                    Settings
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>

    <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
      <DialogTitle>
        Storage Connection Settings
        <Button
          onClick={handleCloseDialog}
          sx={{ position: 'absolute', right: 8, top: 8, minWidth: 'auto' }}
        >
          <CloseIcon />
        </Button>
      </DialogTitle>
      <DialogContent>
        {selectedConnection && (
          <Box sx={{ pt: 2 }}>
            <TextField
              fullWidth
              label="Connection Name"
              value={selectedConnection.provider + ' - ' + selectedConnection.company}
              margin="normal"
              disabled
            />
            <TextField
              fullWidth
              label="Provider"
              value={selectedConnection.provider}
              margin="normal"
              disabled
            />
            <TextField
              fullWidth
              label="Status"
              value={selectedConnection.status}
              margin="normal"
              disabled
            />
            <TextField
              fullWidth
              label="Usage"
              value={`${selectedConnection.usage} of ${selectedConnection.limit}`}
              margin="normal"
              disabled
            />
            <TextField
              fullWidth
              label="Credentials"
              placeholder="Enter credentials"
              margin="normal"
              multiline
              rows={3}
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCloseDialog}>Cancel</Button>
        <Button onClick={handleSaveSettings} variant="contained">Save Changes</Button>
      </DialogActions>
    </Dialog>

    <Dialog open={newConnectionDialog} onClose={handleCloseNewConnectionDialog} maxWidth="sm" fullWidth>
      <DialogTitle>
        Create New Storage Connection
        <Button
          onClick={handleCloseNewConnectionDialog}
          sx={{ position: 'absolute', right: 8, top: 8, minWidth: 'auto' }}
        >
          <CloseIcon />
        </Button>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <TextField
            fullWidth
            label="Connection Name"
            value={newConnection.name}
            onChange={(e) => setNewConnection({...newConnection, name: e.target.value})}
            margin="normal"
            required
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Provider</InputLabel>
            <Select
              value={newConnection.provider}
              onChange={(e) => setNewConnection({...newConnection, provider: e.target.value as string})}
              label="Provider"
            >
              <MenuItem value="minio">MinIO</MenuItem>
              <MenuItem value="yandex_disk">Yandex Disk</MenuItem>
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="Credentials"
            placeholder="Enter credentials (JSON format)"
            value={newConnection.credentials}
            onChange={(e) => setNewConnection({...newConnection, credentials: e.target.value})}
            margin="normal"
            multiline
            rows={4}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCloseNewConnectionDialog}>Cancel</Button>
        <Button onClick={handleSaveNewConnection} variant="contained">Create Connection</Button>
      </DialogActions>
    </Dialog>
    </>
  );
}
