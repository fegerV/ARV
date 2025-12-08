/**
 * CompanyDetails - Детальная информация о компании с табами
 * Tabs: Overview | Projects | Storage | Team | Activity
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Tabs,
  Tab,
  Paper,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  LinearProgress,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  ArrowBack as BackIcon,
} from '@mui/icons-material';
import { companiesAPI } from '@/services/api';
import { PageHeader, PageContent } from '@/components';
import { useToast } from '@/store/useToast';

interface Company {
  id: number;
  name: string;
  slug: string;
  status: 'active' | 'expiring' | 'expired';
  subscription_tier: string;
  expiry_date: string;
  contact_email: string;
  storage_used_gb: number;
  storage_limit_gb: number;
  projects_count: number;
  ar_content_count: number;
  total_views: number;
}

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

export default function CompanyDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  // Mock data
  const [company] = useState<Company>({
    id: parseInt(id || '1'),
    name: 'ООО Артём',
    slug: 'art-studio',
    status: 'active',
    subscription_tier: 'pro',
    expiry_date: '2025-06-30',
    contact_email: 'info@art-studio.ru',
    storage_used_gb: 85,
    storage_limit_gb: 100,
    projects_count: 12,
    ar_content_count: 45,
    total_views: 25892,
  });

  const projects = [
    { id: 1, name: 'Новый год 2025', type: 'Posters', ar_items: 8, status: 'active' },
    { id: 2, name: 'Летняя кампания', type: 'Souvenirs', ar_items: 5, status: 'draft' },
    { id: 3, name: 'Рождество', type: 'Posters', ar_items: 12, status: 'expired' },
  ];

  const team = [
    { id: 1, name: 'Иван Петров', email: 'ivan@art-studio.ru', role: 'Admin', joined: '2024-01-15' },
    { id: 2, name: 'Мария Сидорова', email: 'maria@art-studio.ru', role: 'Editor', joined: '2024-03-20' },
  ];

  const activityLog = [
    { date: '2025-01-08', action: 'Created AR Content', details: 'Portrait #45', user: 'ivan@art-studio.ru' },
    { date: '2025-01-07', action: 'Updated Project', details: 'Summer Campaign', user: 'maria@art-studio.ru' },
    { date: '2025-01-06', action: 'Extended Subscription', details: 'Pro tier +12 months', user: 'ivan@art-studio.ru' },
  ];

  useEffect(() => {
    // TODO: Fetch actual company data
    setLoading(false);
  }, [id]);

  const handleChangeTab = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleDeleteCompany = async () => {
    try {
      await companiesAPI.delete(company.id);
      showToast('Компания удалена', 'success');
      navigate('/companies');
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Ошибка удаления', 'error');
    }
    setDeleteConfirm(false);
  };

  const getStatusChip = (status: string) => {
    const statusMap: { [key: string]: { label: string; color: any } } = {
      active: { label: '⭐ Active', color: 'success' },
      expiring: { label: '⚠️ Expiring', color: 'warning' },
      expired: { label: '❌ Expired', color: 'error' },
    };
    const s = statusMap[status] || { label: status, color: 'default' };
    return <Chip label={s.label} color={s.color} size="small" />;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('ru-RU');
  };

  if (loading) {
    return (
      <PageContent>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
          <CircularProgress />
        </Box>
      </PageContent>
    );
  }

  return (
    <PageContent>
      <PageHeader
        title={company.name}
        subtitle={`${company.slug} • ${company.subscription_tier.toUpperCase()}`}
        actions={
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              startIcon={<BackIcon />}
              onClick={() => navigate('/companies')}
              variant="outlined"
            >
              Назад
            </Button>
            <Button
              startIcon={<EditIcon />}
              onClick={() => navigate(`/companies/${company.id}/edit`)}
              variant="contained"
            >
              Редактировать
            </Button>
            <Button
              startIcon={<DeleteIcon />}
              onClick={() => setDeleteConfirm(true)}
              color="error"
              variant="outlined"
            >
              Удалить
            </Button>
          </Box>
        }
      />

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Paper>
        <Tabs value={tabValue} onChange={handleChangeTab}>
          <Tab label="📋 Обзор" />
          <Tab label="📁 Проекты" />
          <Tab label="💾 Хранилище" />
          <Tab label="👥 Команда" />
          <Tab label="📝 История" />
        </Tabs>
      </Paper>

      {/* Tab 1: Overview */}
      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          {/* Company Info Cards */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Основная информация
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box>
                    <Typography variant="body2" color="textSecondary">Статус</Typography>
                    {getStatusChip(company.status)}
                  </Box>
                  <Box>
                    <Typography variant="body2" color="textSecondary">Email</Typography>
                    <Typography>{company.contact_email}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="textSecondary">Срок действия</Typography>
                    <Typography>{formatDate(company.expiry_date)}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="textSecondary">Подписка</Typography>
                    <Typography sx={{ textTransform: 'uppercase' }}>{company.subscription_tier}</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Statistics */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Статистика
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box>
                    <Typography variant="body2" color="textSecondary">Проектов</Typography>
                    <Typography variant="h5">{company.projects_count}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="textSecondary">AR контента</Typography>
                    <Typography variant="h5">{company.ar_content_count}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="textSecondary">Всего просмотров</Typography>
                    <Typography variant="h5">{company.total_views.toLocaleString('ru-RU')}</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Storage Usage */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Хранилище
                </Typography>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">Использовано</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {company.storage_used_gb} GB / {company.storage_limit_gb} GB
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(company.storage_used_gb / company.storage_limit_gb) * 100}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                  {((company.storage_used_gb / company.storage_limit_gb) * 100).toFixed(1)}% заполнено
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Tab 2: Projects */}
      <TabPanel value={tabValue} index={1}>
        <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="h6">Проекты компании</Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate(`/companies/${company.id}/projects/new`)}
          >
            Новый проект
          </Button>
        </Box>
        <Paper sx={{ overflow: 'auto' }}>
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Название</TableCell>
                <TableCell>Тип</TableCell>
                <TableCell align="center">AR элементов</TableCell>
                <TableCell>Статус</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {projects.map((project) => (
                <TableRow key={project.id} hover>
                  <TableCell>{project.name}</TableCell>
                  <TableCell>{project.type}</TableCell>
                  <TableCell align="center">
                    <Chip label={project.ar_items} size="small" />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={project.status}
                      color={project.status === 'active' ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      </TabPanel>

      {/* Tab 3: Storage */}
      <TabPanel value={tabValue} index={2}>
        <Typography variant="h6" gutterBottom>Хранилище данных</Typography>
        <Alert severity="info" sx={{ mb: 2 }}>
          Компания использует Local Disk для хранения всех данных (портреты, видео, маркеры).
        </Alert>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>Путь хранилища</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                  /companies/{company.id}/
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>Статус синхронизации</Typography>
                <Chip label="✅ Синхронизирован" color="success" />
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Tab 4: Team */}
      <TabPanel value={tabValue} index={3}>
        <Typography variant="h6" gutterBottom>Члены команды</Typography>
        <Paper sx={{ overflow: 'auto' }}>
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Имя</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Роль</TableCell>
                <TableCell>Присоединился</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {team.map((member) => (
                <TableRow key={member.id} hover>
                  <TableCell>{member.name}</TableCell>
                  <TableCell>{member.email}</TableCell>
                  <TableCell>{member.role}</TableCell>
                  <TableCell>{formatDate(member.joined)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      </TabPanel>

      {/* Tab 5: Activity Log */}
      <TabPanel value={tabValue} index={4}>
        <Typography variant="h6" gutterBottom>История активности</Typography>
        <Paper>
          {activityLog.map((log, idx) => (
            <Box
              key={idx}
              sx={{
                p: 2,
                borderBottom: idx < activityLog.length - 1 ? '1px solid #e0e0e0' : 'none',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                  {log.action}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {log.details} • {log.user}
                </Typography>
              </Box>
              <Typography variant="caption">{log.date}</Typography>
            </Box>
          ))}
        </Paper>
      </TabPanel>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirm} onClose={() => setDeleteConfirm(false)}>
        <DialogTitle>Удалить компанию?</DialogTitle>
        <DialogContent>
          <Typography>
            ⚠️ Это действие невозможно отменить. Все проекты, контент и данные будут удалены.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(false)}>Отмена</Button>
          <Button onClick={handleDeleteCompany} color="error" variant="contained">
            Удалить
          </Button>
        </DialogActions>
      </Dialog>
    </PageContent>
  );
}
