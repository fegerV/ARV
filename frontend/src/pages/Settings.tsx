import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Button,
  TextField,
  FormControlLabel,
  Switch,
  Divider,
  Alert,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Notifications as NotificationsIcon,
  Storage as StorageIcon,
} from '@mui/icons-material';

const settingsSections = [
  {
    id: 1,
    title: 'General Settings',
    icon: <SettingsIcon />,
    items: [
      { label: 'Platform Name', value: 'Vertex AR B2B' },
      { label: 'Support Email', value: 'support@vertexar.com' },
      { label: 'Admin Email', value: 'admin@vertexar.com' },
    ],
  },
  {
    id: 2,
    title: 'Security Settings',
    icon: <SecurityIcon />,
    items: [
      { label: 'Session Timeout (minutes)', value: '30' },
      { label: 'Max Login Attempts', value: '5' },
      { label: 'Password Expiry (days)', value: '90' },
    ],
  },
  {
    id: 3,
    title: 'Notification Settings',
    icon: <NotificationsIcon />,
    items: [
      { label: 'Enable Email Notifications', type: 'switch', value: true },
      { label: 'Enable Telegram Notifications', type: 'switch', value: false },
      { label: 'Daily Digest', type: 'switch', value: true },
    ],
  },
  {
    id: 4,
    title: 'Storage Settings',
    icon: <StorageIcon />,
    items: [
      { label: 'Auto Backup Enabled', type: 'switch', value: true },
      { label: 'Backup Frequency (hours)', value: '24' },
      { label: 'Retention Period (days)', value: '30' },
    ],
  },
];

export default function Settings() {
  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Settings
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Manage system configuration and preferences
        </Typography>
      </Box>

      {/* Settings Sections */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {settingsSections.map((section) => (
          <Paper key={section.id} sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Box sx={{ mr: 2, color: 'primary.main' }}>{section.icon}</Box>
              <Typography variant="h6">{section.title}</Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {section.items.map((item, idx) => (
                <Box key={idx}>
                  {item.type === 'switch' ? (
                    <FormControlLabel
                      control={<Switch defaultChecked={item.value} />}
                      label={item.label}
                    />
                  ) : (
                    <TextField
                      fullWidth
                      label={item.label}
                      defaultValue={item.value}
                      size="small"
                    />
                  )}
                </Box>
              ))}
            </Box>
          </Paper>
        ))}
      </Box>

      {/* Save Button */}
      <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
        <Button variant="contained">Save Changes</Button>
        <Button variant="outlined">Reset to Defaults</Button>
      </Box>

      {/* Danger Zone */}
      <Paper sx={{ p: 3, mt: 4, backgroundColor: '#fff3cd' }}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Dangerous Actions - Use with caution!
        </Alert>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" color="error">
            Clear Cache
          </Button>
          <Button variant="outlined" color="error">
            Reset System
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}
