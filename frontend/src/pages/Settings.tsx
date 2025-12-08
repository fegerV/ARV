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
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  ContentCopy as CopyIcon,
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

export default function Settings() {
  const { showToast } = useToast();
  const [tabValue, setTabValue] = useState(0);
  const [openNewToken, setOpenNewToken] = useState(false);
  const [tokens, setTokens] = useState([
    { id: 1, name: 'token-1', value: 'sk-12345***', created: '2025-01-01', lastUsed: '2025-01-08' },
    { id: 2, name: 'token-2', value: 'sk-67890***', created: '2024-12-15', lastUsed: '2025-01-05' },
  ]);
  const [newTokenName, setNewTokenName] = useState('');

  const handleChangeTab = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleGenerateToken = async () => {
    if (!newTokenName.trim()) return;
    setTokens([
      ...tokens,
      {
        id: tokens.length + 1,
        name: newTokenName,
        value: 'sk-' + Math.random().toString(36).substr(2, 9) + '***',
        created: new Date().toISOString().split('T')[0],
        lastUsed: '-',
      },
    ]);
    setOpenNewToken(false);
    setNewTokenName('');
    showToast('Токен генерирован', 'success');
  };

  const handleRevokeToken = (id: number) => {
    setTokens(tokens.filter((t) => t.id !== id));
    showToast('Токен аннулирован', 'success');
  };

  const handleCopyToken = (value: string) => {
    navigator.clipboard.writeText(value);
    showToast('Токен скопирован', 'success');
  };

  return (
    <PageContent>
      <PageHeader
        title="Настройки системы"
        subtitle="Управление профилем, параметрами токенами"
      />

      <Paper>
        <Tabs value={tabValue} onChange={handleChangeTab}>
          <Tab label="Профиль" />
          <Tab label="API токены" />
          <Tab label="Параметры системы" />
        </Tabs>
      </Paper>

      {/* Tab 1: Profile */}
      <TabPanel value={tabValue} index={0}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              сменить пароль
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="текущий пароль"
                  type="password"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Новый пароль"
                  type="password"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Подтвердить пароль"
                  type="password"
                />
              </Grid>
              <Grid item xs={12}>
                <Button variant="contained">
                  Обновить пароль
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </TabPanel>

      {/* Tab 2: API Tokens */}
      <TabPanel value={tabValue} index={1}>
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Это мои токены</Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenNewToken(true)}
          >
            Новый токен
          </Button>
        </Box>

        <Paper sx={{ overflow: 'auto' }}>
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Имя</TableCell>
                <TableCell>Токен</TableCell>
                <TableCell>Создан</TableCell>
                <TableCell>Последнее использование</TableCell>
                <TableCell align="right">Действия</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tokens.map((token) => (
                <TableRow key={token.id}>
                  <TableCell>{token.name}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                        {token.value}
                      </Typography>
                      <Button
                        size="small"
                        startIcon={<CopyIcon />}
                        onClick={() => handleCopyToken(token.value)}
                      >
                        Копия
                      </Button>
                    </Box>
                  </TableCell>
                  <TableCell>{token.created}</TableCell>
                  <TableCell>{token.lastUsed}</TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      color="error"
                      onClick={() => handleRevokeToken(token.id)}
                    >
                      Ревокировать
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      </TabPanel>

      {/* Tab 3: System Settings */}
      <TabPanel value={tabValue} index={2}>
        <Card>
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Ограничения дрансфера
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="API запросы в минуту"
                  type="number"
                  defaultValue={1000}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Макс. размер видео (MB)"
                  type="number"
                  defaultValue={50}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Макс. размер изображения (MB)"
                  type="number"
                  defaultValue={10}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Дней хранения аналитики"
                  type="number"
                  defaultValue={90}
                />
              </Grid>
              <Grid item xs={12}>
                <Button variant="contained">
                  Сохранить параметры
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </TabPanel>

      {/* New Token Dialog */}
      <Dialog open={openNewToken} onClose={() => setOpenNewToken(false)}>
        <DialogTitle>Новый API токен</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="u041dаименование токена"
            placeholder="напр. my-api-token"
            value={newTokenName}
            onChange={(e) => setNewTokenName(e.target.value)}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenNewToken(false)}>Отмена</Button>
          <Button onClick={handleGenerateToken} variant="contained">
            Генерировать
          </Button>
        </DialogActions>
      </Dialog>
    </PageContent>
  );
}
