import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Chip,
  Card,
  CardContent,
  FormControlLabel,
  Switch,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Delete as DeleteIcon, Mail as MailIcon, Send as SendIcon } from '@mui/icons-material';
import { notificationsAPI } from '../services/api';
import { useToast } from '../store/useToast';

const notificationSettings = [
  { id: 1, title: 'Expiry Warnings', description: 'Notify when subscriptions are about to expire', enabled: true },
  { id: 2, title: 'Storage Alerts', description: 'Alert when storage usage exceeds threshold', enabled: true },
  { id: 3, title: 'System Updates', description: 'Notify about system updates and new features', enabled: true },
  { id: 4, title: 'User Activity', description: 'Alert on unusual user activity', enabled: false },
];

interface NotificationItem {
  id: number;
  company_id?: number | null;
  project_id?: number | null;
  ar_content_id?: number | null;
  type: string;
  email_sent: boolean;
  telegram_sent: boolean;
  subject?: string | null;
  message: string;
  created_at?: string | null;
  is_read?: boolean;
  read_at?: string | null;
}

type NotificationRow = NotificationItem & {
  channel: string;
  status: 'read' | 'unread';
};

export default function Notifications() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<NotificationItem[]>([]);

  const [settingsState, setSettingsState] = useState(() =>
    notificationSettings.reduce<Record<number, boolean>>((acc, s) => {
      acc[s.id] = s.enabled;
      return acc;
    }, {})
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await notificationsAPI.list(50);
      setItems(res.data || []);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to load notifications';
      setError(msg);
      addToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleMarkRead = useCallback(async (id: number) => {
    try {
      await notificationsAPI.markRead([id]);
      setItems((prev: NotificationItem[]) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      );
      addToast('Marked as read', 'success');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to mark as read';
      addToast(msg, 'error');
    }
  }, [addToast]);

  const handleDelete = useCallback(async (id: number) => {
    const ok = window.confirm('Delete this notification?');
    if (!ok) return;
    try {
      await notificationsAPI.delete(id);
      setItems((prev: NotificationItem[]) => prev.filter((n) => n.id !== id));
      addToast('Deleted', 'success');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to delete notification';
      addToast(msg, 'error');
    }
  }, [addToast]);

  const notificationRows = useMemo((): NotificationRow[] => {
    return items.map((n: NotificationItem) => {
      const channel = n.email_sent ? 'email' : n.telegram_sent ? 'telegram' : 'web';
      const isRead = Boolean(n.is_read);
      return { ...n, channel, status: isRead ? 'read' : 'unread' };
    });
  }, [items]);

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Notifications
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Manage notifications and alerts
        </Typography>
        <Box sx={{ mt: 2 }}>
          <Button variant="outlined" onClick={load} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Notification Settings */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Notification Preferences
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {notificationSettings.map((setting) => (
            <Card key={setting.id} variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <Box>
                    <Typography variant="subtitle1">{setting.title}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      {setting.description}
                    </Typography>
                  </Box>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={Boolean(settingsState[setting.id])}
                        onChange={(e: ChangeEvent<HTMLInputElement>) =>
                          setSettingsState((prev: Record<number, boolean>) => ({
                            ...prev,
                            [setting.id]: e.target.checked,
                          }))
                        }
                      />
                    }
                    label=""
                  />
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Paper>

      {/* Notification List */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Recent Notifications
        </Typography>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        ) : notificationRows.length === 0 ? (
          <Typography color="textSecondary">No notifications</Typography>
        ) : (
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Type</TableCell>
                <TableCell>Message</TableCell>
                <TableCell>Channel</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {notificationRows.map((notif: NotificationRow) => (
                <TableRow key={notif.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {notif.type}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{notif.message}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={notif.channel === 'email' ? <MailIcon /> : <SendIcon />}
                      label={notif.channel}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {notif.created_at ? new Date(notif.created_at).toLocaleString() : '—'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={notif.status}
                      size="small"
                      color={notif.status === 'unread' ? 'warning' : 'default'}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => handleMarkRead(notif.id)}
                      disabled={notif.status === 'read'}
                      sx={{ mr: 1 }}
                    >
                      Mark read
                    </Button>
                    <Button
                      size="small"
                      startIcon={<DeleteIcon />}
                      color="error"
                      onClick={() => handleDelete(notif.id)}
                    >
                      Delete
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Box>
  );
}
