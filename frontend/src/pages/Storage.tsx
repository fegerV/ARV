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
  Divider,
  CircularProgress,
  Alert,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import { Settings as SettingsIcon, Close as CloseIcon } from '@mui/icons-material';
import { useState, useEffect, type ChangeEvent } from 'react';
import { storageAPI, StorageConnection, StorageConnectionCreate, StorageConnectionUpdate } from '../services/api';
import { useToast } from '../store/useToast';

export default function Storage() {
  const { addToast } = useToast();
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<StorageConnection | null>(null);
  const [newConnectionDialog, setNewConnectionDialog] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [storageConnections, setStorageConnections] = useState<StorageConnection[]>([]);
  const [newConnection, setNewConnection] = useState({
    name: '',
    provider: 'minio' as StorageConnectionCreate['provider'],
    base_path: '',
    is_default: false,
    credentials: '', // JSON string
  });

  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);

  const handleConfigureStorage = () => {
    setNewConnectionDialog(true);
  };

  const loadStorageConnections = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await storageAPI.list();
      setStorageConnections(response.data);
    } catch (error) {
      console.error('Failed to load storage connections:', error);
      const msg = (error as any)?.response?.data?.detail || 'Failed to load storage connections';
      setError(msg);
      addToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Load connections on component mount
  useEffect(() => {
    loadStorageConnections();
  }, []);

  // Yandex OAuth UI/component is not present in this repository.

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setSelectedConnection(null);
  };

  const handleCloseNewConnectionDialog = () => {
    setNewConnectionDialog(false);
    setNewConnection({ name: '', provider: 'minio', base_path: '', is_default: false, credentials: '' });
  };

  const handleSettingsClick = (connection: StorageConnection) => {
    setSelectedConnection(connection);
    setOpenDialog(true);
  };

  const tryParseCredentials = (credentialsJson: string): Record<string, any> | undefined => {
    const trimmed = credentialsJson.trim();
    if (!trimmed) return undefined;
    return JSON.parse(trimmed);
  };

  const handleSaveNewConnection = async () => {
    if (!newConnection.name.trim()) {
      addToast('Connection name is required', 'error');
      return;
    }

    if (newConnection.provider === 'yandex_disk') {
      addToast('Для Yandex Disk используйте OAuth кнопку ниже', 'info');
      return;
    }

    setSaving(true);
    try {
      const payload: StorageConnectionCreate = {
        name: newConnection.name,
        provider: newConnection.provider,
        base_path: newConnection.base_path || undefined,
        is_default: newConnection.is_default,
        credentials: tryParseCredentials(newConnection.credentials),
      };
      await storageAPI.create(payload);
      addToast('Storage connection created', 'success');
      handleCloseNewConnectionDialog();
      await loadStorageConnections();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to create storage connection';
      addToast(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!selectedConnection) return;
    setSaving(true);
    try {
      const payload: StorageConnectionUpdate = {
        name: selectedConnection.name,
        is_active: selectedConnection.is_active,
        metadata: selectedConnection.metadata,
      };
      await storageAPI.update(selectedConnection.id, payload);
      addToast('Storage connection updated', 'success');
      handleCloseDialog();
      await loadStorageConnections();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to update storage connection';
      addToast(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async (id: number) => {
    setTestingId(id);
    try {
      const res = await storageAPI.test(id);
      addToast(res.data?.message || 'Test completed', res.data?.status === 'success' ? 'success' : 'warning');
      await loadStorageConnections();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to test connection';
      addToast(msg, 'error');
    } finally {
      setTestingId(null);
    }
  };

  const storageStats = [
    {
      title: 'Connections',
      value: String(storageConnections.length),
    },
    {
      title: 'Active',
      value: String(storageConnections.filter((c: StorageConnection) => c.is_active).length),
    },
    {
      title: 'Default',
      value: storageConnections.find((c: StorageConnection) => c.is_default)?.name || '—',
    },
    {
      title: 'Providers',
      value: String(new Set(storageConnections.map((c: StorageConnection) => c.provider)).size),
    },
  ];

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

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

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
                <Box>
                  <LinearProgress variant="determinate" value={100} sx={{ opacity: 0, height: 0, mt: 1 }} />
                </Box>
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
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : storageConnections.length === 0 ? (
          <Typography color="text.secondary">No storage connections</Typography>
        ) : (
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell>Name</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell>Active</TableCell>
              <TableCell>Base Path</TableCell>
              <TableCell>Default</TableCell>
              <TableCell>Test</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {storageConnections.map((connection: StorageConnection) => (
              <TableRow key={connection.id} hover>
                <TableCell>{connection.name}</TableCell>
                <TableCell>{connection.provider}</TableCell>
                <TableCell>
                  <Chip
                    label={connection.is_active ? 'active' : 'inactive'}
                    size="small"
                    color={connection.is_active ? 'success' : 'default'}
                  />
                </TableCell>
                <TableCell>{connection.base_path || '—'}</TableCell>
                <TableCell>
                  {connection.is_default ? (
                    <Chip label="default" size="small" color="primary" variant="outlined" />
                  ) : (
                    '—'
                  )}
                </TableCell>
                <TableCell>
                  {connection.test_status ? (
                    <Chip
                      label={connection.test_status}
                      size="small"
                      color={connection.test_status === 'success' ? 'success' : 'default'}
                      variant="outlined"
                    />
                  ) : (
                    '—'
                  )}
                </TableCell>
                <TableCell>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => handleTestConnection(connection.id)}
                    disabled={testingId === connection.id}
                    sx={{ mr: 1 }}
                  >
                    {testingId === connection.id ? 'Testing...' : 'Test'}
                  </Button>
                  <Button size="small" variant="outlined" onClick={() => handleSettingsClick(connection)}>
                    Edit
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        )}
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
              value={selectedConnection.name}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setSelectedConnection({ ...selectedConnection, name: e.target.value })
              }
              margin="normal"
            />
            <TextField
              fullWidth
              label="Provider"
              value={selectedConnection.provider}
              margin="normal"
              disabled
            />
            <FormControl fullWidth margin="normal">
              <InputLabel>Status</InputLabel>
              <Select
                label="Status"
                value={selectedConnection.is_active ? 'active' : 'inactive'}
                onChange={(e: SelectChangeEvent) =>
                  setSelectedConnection({ ...selectedConnection, is_active: String(e.target.value) === 'active' })
                }
              >
                <MenuItem value="active">active</MenuItem>
                <MenuItem value="inactive">inactive</MenuItem>
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Base Path"
              value={selectedConnection.base_path || ''}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setSelectedConnection({ ...selectedConnection, base_path: e.target.value || undefined })
              }
              margin="normal"
              helperText="Optional"
            />
            {selectedConnection.test_error ? (
              <Alert severity="warning" sx={{ mt: 2 }}>
                {selectedConnection.test_error}
              </Alert>
            ) : null}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCloseDialog} disabled={saving}>Cancel</Button>
        <Button onClick={handleSaveSettings} variant="contained" disabled={saving}>
          {saving ? 'Saving...' : 'Save Changes'}
        </Button>
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
            onChange={(e: ChangeEvent<HTMLInputElement>) => setNewConnection({ ...newConnection, name: e.target.value })}
            margin="normal"
            required
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Provider</InputLabel>
            <Select
              value={newConnection.provider}
              onChange={(e: SelectChangeEvent) =>
                setNewConnection({ ...newConnection, provider: e.target.value as 'local_disk' | 'minio' | 'yandex_disk' })
              }
              label="Provider"
            >
              <MenuItem value="local_disk">Local Disk</MenuItem>
              <MenuItem value="minio">MinIO</MenuItem>
              <MenuItem value="yandex_disk">Yandex Disk</MenuItem>
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="Base Path"
            value={newConnection.base_path}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setNewConnection({ ...newConnection, base_path: e.target.value })}
            margin="normal"
            helperText="Optional"
          />

          {newConnection.provider === 'yandex_disk' ? (
            <Alert severity="info" sx={{ mt: 2 }}>
              Интеграция Yandex Disk OAuth в этой сборке не подключена (нет UI-компонента).
              Используйте другой provider или подключите OAuth-компонент/flow.
            </Alert>
          ) : (
            <TextField
              fullWidth
              label="Credentials"
              placeholder="Enter credentials (JSON format)"
              value={newConnection.credentials}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setNewConnection({ ...newConnection, credentials: e.target.value })
              }
              margin="normal"
              multiline
              rows={4}
              helperText="For MinIO, provide access key, secret key, and endpoint"
            />
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCloseNewConnectionDialog} disabled={saving}>Cancel</Button>
        <Button onClick={handleSaveNewConnection} variant="contained" disabled={saving}>
          {saving ? 'Creating...' : 'Create Connection'}
        </Button>
      </DialogActions>
    </Dialog>
    </>
  );
}
