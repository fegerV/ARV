import { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  TextField,
  Button,
  Card,
  CardContent,
  Grid,
  FormControlLabel,
  Switch,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TablePagination,
  Chip,
  IconButton,
  TextareaAutosize,
} from '@mui/material';
import {
  Send as SendIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  VisibilityOutlined as PreviewIcon,
} from '@mui/icons-material';
import { PageHeader, PageContent } from '@/components';
import { useToast } from '@/store/useToast';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function Notifications() {
  const { showToast } = useToast();
  const [tabValue, setTabValue] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState('');

  // Email Settings State
  const [emailSettings, setEmailSettings] = useState({
    enabled: true,
    host: 'smtp.yandex.ru',
    port: 587,
    username: 'noreply@vertexar.io',
    password: '',
    from_name: 'Vertex AR',
    from_email: 'noreply@vertexar.io',
  });

  // Telegram Settings State
  const [telegramSettings, setTelegramSettings] = useState({
    enabled: true,
    bot_token: 'YOUR_BOT_TOKEN_HERE',
    admin_chat_id: '-123456789',
    dev_channel_id: '-987654321',
    error_channel_id: '-111111111',
  });

  // Templates
  const [templates, setTemplates] = useState([
    {
      id: 'expiry_warning',
      name: 'Expiry Warning (7 days)',
      subject: 'Your subscription expires in 7 days',
      body: 'Your Vertex AR subscription will expire on {expiry_date}. Please renew to continue using our service.',
    },
    {
      id: 'video_rotation',
      name: 'Video Rotation Notice',
      subject: 'New video rotation activated',
      body: 'Video rotation for project {project_name} has been activated.',
    },
    {
      id: 'marker_failed',
      name: 'Marker Generation Failed',
      subject: 'AR marker generation failed',
      body: 'Failed to generate AR marker for {content_name}. Error: {error_message}',
    },
    {
      id: 'quota_exceeded',
      name: 'Quota Exceeded',
      subject: 'Storage quota exceeded',
      body: 'Your storage quota has been exceeded. Current usage: {usage}GB / {limit}GB',
    },
  ]);

  // History Mock Data
  const historyData = [
    { id: 1, date: '2025-01-08', type: 'Expiry Warning', company: 'ООО Артём', recipient: 'info@art-studio.ru', status: 'sent' },
    { id: 2, date: '2025-01-08', type: 'Marker Failed', company: 'МегаПринт', recipient: 'admin@megaprint.ru', status: 'failed' },
    { id: 3, date: '2025-01-07', type: 'Video Rotation', company: 'СтудияХК', recipient: 'contact@studiohk.ru', status: 'sent' },
  ];

  const handleChangeTab = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSaveEmailSettings = async () => {
    try {
      // TODO: Call API to save email settings
      showToast('Email settings saved', 'success');
    } catch (err: any) {
      showToast('Error saving settings', 'error');
    }
  };

  const handleTestEmail = async () => {
    try {
      // TODO: Call API to test email
      showToast('Test email sent to ' + emailSettings.from_email, 'success');
    } catch (err: any) {
      showToast('Error sending test email', 'error');
    }
  };

  const handleSaveTelegramSettings = async () => {
    try {
      // TODO: Call API to save telegram settings
      showToast('Telegram settings saved', 'success');
    } catch (err: any) {
      showToast('Error saving settings', 'error');
    }
  };

  const handleTestTelegram = async () => {
    try {
      // TODO: Call API to test telegram
      showToast('Test message sent', 'success');
    } catch (err: any) {
      showToast('Error sending test message', 'error');
    }
  };

  const handleSaveTemplate = (templateId: string, newBody: string) => {
    setTemplates(templates.map(t => t.id === templateId ? { ...t, body: newBody } : t));
    showToast('Template updated', 'success');
  };

  const handleResendNotification = (id: number) => {
    showToast('Notification resent', 'success');
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <PageContent>
      <PageHeader
        title="Уведомления"
        subtitle="Настройка Email, Telegram и шаблонов уведомлений"
      />

      <Paper>
        <Tabs value={tabValue} onChange={handleChangeTab}>
          <Tab label="📧 Email" />
          <Tab label="🤖 Telegram" />
          <Tab label="📝 Templates" />
          <Tab label="📋 History" />
        </Tabs>
      </Paper>

      {/* Tab 1: Email Settings */}
      <TabPanel value={tabValue} index={0}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              ✉️ Email Settings
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={emailSettings.enabled}
                      onChange={(e) =>
                        setEmailSettings({ ...emailSettings, enabled: e.target.checked })
                      }
                    />
                  }
                  label="Enable Email Notifications"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="SMTP Host"
                  value={emailSettings.host}
                  onChange={(e) => setEmailSettings({ ...emailSettings, host: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="SMTP Port"
                  type="number"
                  value={emailSettings.port}
                  onChange={(e) =>
                    setEmailSettings({ ...emailSettings, port: parseInt(e.target.value) })
                  }
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Username"
                  value={emailSettings.username}
                  onChange={(e) =>
                    setEmailSettings({ ...emailSettings, username: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Password"
                  type="password"
                  value={emailSettings.password}
                  onChange={(e) =>
                    setEmailSettings({ ...emailSettings, password: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="From Name"
                  value={emailSettings.from_name}
                  onChange={(e) =>
                    setEmailSettings({ ...emailSettings, from_name: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="From Email"
                  type="email"
                  value={emailSettings.from_email}
                  onChange={(e) =>
                    setEmailSettings({ ...emailSettings, from_email: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Button variant="contained" onClick={handleSaveEmailSettings}>
                    Save Settings
                  </Button>
                  <Button variant="outlined" startIcon={<SendIcon />} onClick={handleTestEmail}>
                    Send Test Email
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </TabPanel>

      {/* Tab 2: Telegram Settings */}
      <TabPanel value={tabValue} index={1}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🤖 Telegram Bot
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={telegramSettings.enabled}
                      onChange={(e) =>
                        setTelegramSettings({ ...telegramSettings, enabled: e.target.checked })
                      }
                    />
                  }
                  label="Enable Telegram Alerts"
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Bot Token"
                  value={telegramSettings.bot_token}
                  onChange={(e) =>
                    setTelegramSettings({ ...telegramSettings, bot_token: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Admin Chat ID"
                  value={telegramSettings.admin_chat_id}
                  onChange={(e) =>
                    setTelegramSettings({ ...telegramSettings, admin_chat_id: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Dev Channel ID"
                  value={telegramSettings.dev_channel_id}
                  onChange={(e) =>
                    setTelegramSettings({ ...telegramSettings, dev_channel_id: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Error Channel ID"
                  value={telegramSettings.error_channel_id}
                  onChange={(e) =>
                    setTelegramSettings({ ...telegramSettings, error_channel_id: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Button variant="contained" onClick={handleSaveTelegramSettings}>
                    Save Settings
                  </Button>
                  <Button variant="outlined" startIcon={<SendIcon />} onClick={handleTestTelegram}>
                    Send Test Message
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </TabPanel>

      {/* Tab 3: Templates */}
      <TabPanel value={tabValue} index={2}>
        <Grid container spacing={2}>
          {templates.map((template) => (
            <Grid item xs={12} key={template.id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">{template.name}</Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setPreviewTemplate(template.body);
                          setPreviewOpen(true);
                        }}
                        title="Preview"
                      >
                        <PreviewIcon />
                      </IconButton>
                    </Box>
                  </Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Subject:
                  </Typography>
                  <TextField fullWidth size="small" defaultValue={template.subject} disabled />
                  <Typography variant="subtitle2" sx={{ mt: 2 }} gutterBottom>
                    Body:
                  </Typography>
                  <TextareaAutosize
                    minRows={4}
                    defaultValue={template.body}
                    style={{
                      width: '100%',
                      padding: '8px',
                      fontFamily: 'monospace',
                      fontSize: '12px',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                    }}
                  />
                  <Button
                    sx={{ mt: 2 }}
                    variant="contained"
                    onClick={() => handleSaveTemplate(template.id, template.body)}
                  >
                    Save Template
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* Tab 4: History */}
      <TabPanel value={tabValue} index={3}>
        <Paper sx={{ overflow: 'auto' }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Date</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Company</TableCell>
                <TableCell>Recipient</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {historyData.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.date}</TableCell>
                  <TableCell>{item.type}</TableCell>
                  <TableCell>{item.company}</TableCell>
                  <TableCell>{item.recipient}</TableCell>
                  <TableCell>
                    <Chip
                      label={item.status === 'sent' ? '✅ Sent' : '❌ Failed'}
                      color={item.status === 'sent' ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">
                    {item.status === 'failed' && (
                      <Button
                        size="small"
                        onClick={() => handleResendNotification(item.id)}
                      >
                        Resend
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            rowsPerPageOptions={[5, 10, 25]}
            component="div"
            count={historyData.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </Paper>
      </TabPanel>

      {/* Template Preview Dialog */}
      <Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Template Preview</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mt: 2, whiteSpace: 'pre-wrap' }}>
            {previewTemplate}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </PageContent>
  );
}
