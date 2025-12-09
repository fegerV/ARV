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
} from '@mui/material';
import { Delete as DeleteIcon, Mail as MailIcon, Send as SendIcon } from '@mui/icons-material';

const notifications = [
  {
    id: 1,
    type: 'Expiry Warning',
    message: 'Company A - Project expires in 7 days',
    status: 'unread',
    date: '2025-01-08 10:30',
    channel: 'email',
  },
  {
    id: 2,
    type: 'Storage Alert',
    message: 'Storage usage exceeds 80% threshold',
    status: 'unread',
    date: '2025-01-07 15:45',
    channel: 'email',
  },
  {
    id: 3,
    type: 'System Update',
    message: 'New AR marker generation feature available',
    status: 'read',
    date: '2025-01-06 09:20',
    channel: 'web',
  },
  {
    id: 4,
    type: 'New Company',
    message: 'New company registered: Tech Innovations Inc',
    status: 'read',
    date: '2025-01-05 14:00',
    channel: 'email',
  },
];

const notificationSettings = [
  { id: 1, title: 'Expiry Warnings', description: 'Notify when subscriptions are about to expire', enabled: true },
  { id: 2, title: 'Storage Alerts', description: 'Alert when storage usage exceeds threshold', enabled: true },
  { id: 3, title: 'System Updates', description: 'Notify about system updates and new features', enabled: true },
  { id: 4, title: 'User Activity', description: 'Alert on unusual user activity', enabled: false },
];

export default function Notifications() {
  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Notifications
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Manage notifications and alerts
        </Typography>
      </Box>

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
                    control={<Switch checked={setting.enabled} />}
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
            {notifications.map((notif) => (
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
                  <Typography variant="caption">{notif.date}</Typography>
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
                  <Button size="small" startIcon={<DeleteIcon />} color="error">
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
