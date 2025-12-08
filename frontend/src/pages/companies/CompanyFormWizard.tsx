/**
 * CompanyForm - 6-шаговый wizard для создания/редактирования компаний
 * Steps: 1) Basic Info → 2) Storage → 3) Subscription → 4) Quotas → 5) Notifications → 6) Review
 */

import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  Card,
  CardContent,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormControlLabel,
  Switch,
  Typography,
  Paper,
  Grid,
  CircularProgress,
  Alert,
} from '@mui/material';
import { ArrowBack as BackIcon, ArrowForward as ForwardIcon } from '@mui/icons-material';
import { companiesAPI } from '@/services/api';
import { PageHeader, PageContent } from '@/components';
import { useToast } from '@/store/useToast';

const SUBSCRIPTION_TIERS = [
  { value: 'basic', label: 'Basic', storage: '10GB', projects: '50', email: '✓', telegram: '' },
  { value: 'pro', label: 'Pro', storage: '100GB', projects: '500', email: '✓', telegram: '✓' },
  { value: 'enterprise', label: 'Enterprise', storage: 'Unlimited', projects: 'Unlimited', email: '✓', telegram: '✓' },
];

interface FormData {
  // Step 1: Basic Info
  name: string;
  slug: string;
  description: string;
  contact_email: string;
  // Step 2: Storage
  storage_provider: 'local' | 'minio' | 'yandex_disk';
  storage_folder_id?: string;
  // Step 3: Subscription
  subscription_tier: 'basic' | 'pro' | 'enterprise';
  subscription_period: '1' | '3' | '6' | '12';
  auto_renew: boolean;
  discount_percent: number;
  // Step 4: Quotas
  storage_quota_gb: number;
  max_projects: number;
  max_videos_per_content: number;
  max_team_members: number;
  // Step 5: Notifications
  enable_email_notifications: boolean;
  notification_email: string;
  enable_telegram_notifications: boolean;
  telegram_chat_id: string;
  expiry_warning_days: number[];
}

export default function CompanyFormWizard() {
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();
  const { showToast } = useToast();
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);

  const [formData, setFormData] = useState<FormData>({
    name: '',
    slug: '',
    description: '',
    contact_email: '',
    storage_provider: 'local',
    subscription_tier: 'pro',
    subscription_period: '12',
    auto_renew: true,
    discount_percent: 0,
    storage_quota_gb: 100,
    max_projects: 500,
    max_videos_per_content: 10,
    max_team_members: 5,
    enable_email_notifications: true,
    notification_email: '',
    enable_telegram_notifications: false,
    telegram_chat_id: '',
    expiry_warning_days: [7, 14, 30],
  });

  const steps = [
    'Основная информация',
    'Хранилище',
    'Подписка',
    'Квоты',
    'Уведомления',
    'Обзор',
  ];

  // Generate slug from name
  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  };

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => {
      const updated = { ...prev, [field]: value };
      // Auto-generate slug
      if (field === 'name') {
        updated.slug = generateSlug(value);
      }
      return updated;
    });
  };

  const handleNext = () => {
    // TODO: Add validation for current step
    if (activeStep < steps.length - 1) {
      setActiveStep(activeStep + 1);
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep(activeStep - 1);
    }
  };

  const handleSubmit = async () => {
    setSubmitLoading(true);
    try {
      if (id) {
        await companiesAPI.update(parseInt(id), formData);
        showToast('Компания обновлена', 'success');
      } else {
        await companiesAPI.create(formData);
        showToast('Компания создана', 'success');
      }
      navigate('/companies');
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Ошибка сохранения', 'error');
    } finally {
      setSubmitLoading(false);
    }
  };

  // Step 1: Basic Info
  const renderStep1 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Название компании"
              placeholder="например: ООО Артём"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Slug (уникальный идентификатор)"
              placeholder="auto-generated"
              value={formData.slug}
              onChange={(e) => handleChange('slug', e.target.value)}
              helperText="Автоматически генерируется из названия"
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Описание"
              placeholder="Что делает эта компания?"
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              multiline
              rows={3}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Email контактного лица"
              type="email"
              placeholder="contact@company.com"
              value={formData.contact_email}
              onChange={(e) => handleChange('contact_email', e.target.value)}
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  // Step 2: Storage
  const renderStep2 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <FormControl fullWidth>
              <InputLabel>Тип хранилища</InputLabel>
              <Select
                value={formData.storage_provider}
                label="Тип хранилища"
                onChange={(e) => handleChange('storage_provider', e.target.value)}
              >
                <MenuItem value="local">Local Disk</MenuItem>
                <MenuItem value="minio">MinIO</MenuItem>
                <MenuItem value="yandex_disk">Yandex Disk</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12}>
            <Alert severity="info">
              {formData.storage_provider === 'local' && 'Local disk storage для Vertex AR'}
              {formData.storage_provider === 'minio' && 'Подключите MinIO S3 credentials'}
              {formData.storage_provider === 'yandex_disk' && 'Используется OAuth для Yandex Disk'}
            </Alert>
          </Grid>
          {formData.storage_provider === 'yandex_disk' && (
            <Grid item xs={12}>
              <Button variant="outlined" fullWidth>
                🔗 Подключить с Yandex Disk
              </Button>
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  );

  // Step 3: Subscription
  const renderStep3 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Пакет подписки</InputLabel>
              <Select
                value={formData.subscription_tier}
                label="Пакет подписки"
                onChange={(e) => handleChange('subscription_tier', e.target.value)}
              >
                {SUBSCRIPTION_TIERS.map((tier) => (
                  <MenuItem key={tier.value} value={tier.value}>
                    {tier.label} ({tier.storage}, {tier.projects} проектов)
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Период подписки</InputLabel>
              <Select
                value={formData.subscription_period}
                label="Период подписки"
                onChange={(e) => handleChange('subscription_period', e.target.value)}
              >
                <MenuItem value="1">1 месяц</MenuItem>
                <MenuItem value="3">3 месяца</MenuItem>
                <MenuItem value="6">6 месяцев</MenuItem>
                <MenuItem value="12">12 месяцев</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.auto_renew}
                  onChange={(e) => handleChange('auto_renew', e.target.checked)}
                />
              }
              label="Автоматическое продление при истечении"
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Скидка (%)"
              type="number"
              inputProps={{ min: 0, max: 100 }}
              value={formData.discount_percent}
              onChange={(e) => handleChange('discount_percent', parseInt(e.target.value) || 0)}
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  // Step 4: Quotas
  const renderStep4 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Лимит хранилища (GB)"
              type="number"
              value={formData.storage_quota_gb}
              onChange={(e) => handleChange('storage_quota_gb', parseInt(e.target.value) || 0)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Макс. количество проектов"
              type="number"
              value={formData.max_projects}
              onChange={(e) => handleChange('max_projects', parseInt(e.target.value) || 0)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Макс. видео на контент"
              type="number"
              value={formData.max_videos_per_content}
              onChange={(e) => handleChange('max_videos_per_content', parseInt(e.target.value) || 0)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Макс. членов команды"
              type="number"
              value={formData.max_team_members}
              onChange={(e) => handleChange('max_team_members', parseInt(e.target.value) || 0)}
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  // Step 5: Notifications
  const renderStep5 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.enable_email_notifications}
                  onChange={(e) => handleChange('enable_email_notifications', e.target.checked)}
                />
              }
              label="Email уведомления"
            />
          </Grid>
          {formData.enable_email_notifications && (
            <>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Email для уведомлений"
                  type="email"
                  value={formData.notification_email}
                  onChange={(e) => handleChange('notification_email', e.target.value)}
                />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="subtitle2">Предупреждение об истечении за (дней):</Typography>
                <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                  {[7, 14, 30].map((days) => (
                    <Button
                      key={days}
                      variant={formData.expiry_warning_days.includes(days) ? 'contained' : 'outlined'}
                      onClick={() => {
                        const updated = formData.expiry_warning_days.includes(days)
                          ? formData.expiry_warning_days.filter((d) => d !== days)
                          : [...formData.expiry_warning_days, days];
                        handleChange('expiry_warning_days', updated);
                      }}
                    >
                      {days}д
                    </Button>
                  ))}
                </Box>
              </Grid>
            </>
          )}
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.enable_telegram_notifications}
                  onChange={(e) => handleChange('enable_telegram_notifications', e.target.checked)}
                />
              }
              label="Telegram уведомления"
            />
          </Grid>
          {formData.enable_telegram_notifications && (
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Telegram Chat ID"
                value={formData.telegram_chat_id}
                onChange={(e) => handleChange('telegram_chat_id', e.target.value)}
                placeholder="-123456789"
              />
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  );

  // Step 6: Review
  const renderStep6 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>📋 Обзор</Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
              <Typography variant="subtitle2" gutterBottom>Компания</Typography>
              <Typography><strong>Название:</strong> {formData.name}</Typography>
              <Typography><strong>Slug:</strong> {formData.slug}</Typography>
              <Typography><strong>Email:</strong> {formData.contact_email}</Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
              <Typography variant="subtitle2" gutterBottom>Подписка</Typography>
              <Typography><strong>Пакет:</strong> {formData.subscription_tier.toUpperCase()}</Typography>
              <Typography><strong>Период:</strong> {formData.subscription_period} месяцев</Typography>
              <Typography><strong>Авто-продление:</strong> {formData.auto_renew ? '✓' : '✗'}</Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
              <Typography variant="subtitle2" gutterBottom>Хранилище</Typography>
              <Typography><strong>Лимит:</strong> {formData.storage_quota_gb} GB</Typography>
              <Typography><strong>Провайдер:</strong> {formData.storage_provider}</Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
              <Typography variant="subtitle2" gutterBottom>Квоты</Typography>
              <Typography><strong>Проектов:</strong> {formData.max_projects}</Typography>
              <Typography><strong>Видео/контент:</strong> {formData.max_videos_per_content}</Typography>
              <Typography><strong>Команда:</strong> {formData.max_team_members}</Typography>
            </Paper>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  const stepRenderers = [
    renderStep1,
    renderStep2,
    renderStep3,
    renderStep4,
    renderStep5,
    renderStep6,
  ];

  return (
    <PageContent>
      <PageHeader
        title={id ? 'Редактирование компании' : 'Новая компания'}
        subtitle="6-шаговый процесс создания/редактирования"
      />

      <Box sx={{ mb: 4 }}>
        <Stepper activeStep={activeStep}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Box>

      <Box sx={{ mb: 4 }}>
        {stepRenderers[activeStep]()}
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button
          disabled={activeStep === 0}
          onClick={handleBack}
          startIcon={<BackIcon />}
        >
          Назад
        </Button>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button onClick={() => navigate('/companies')} variant="outlined">
            Отмена
          </Button>
          {activeStep < steps.length - 1 ? (
            <Button
              variant="contained"
              onClick={handleNext}
              endIcon={<ForwardIcon />}
            >
              Далее
            </Button>
          ) : (
            <Button
              variant="contained"
              color="success"
              onClick={handleSubmit}
              disabled={submitLoading}
            >
              {submitLoading ? <CircularProgress size={24} /> : 'Сохранить'}
            </Button>
          )}
        </Box>
      </Box>
    </PageContent>
  );
}
