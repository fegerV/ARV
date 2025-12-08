/**
 * ProjectForm - 5-шаговый wizard для создания/редактирования проектов
 * Steps: 1) Info → 2) Folder → 3) Timeline → 4) Quotas → 5) Review
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
  Chip,
  FormGroup,
  Checkbox,
} from '@mui/material';
import { ArrowBack as BackIcon, ArrowForward as ForwardIcon } from '@mui/icons-material';
import { projectsAPI } from '@/services/api';
import { PageHeader, PageContent } from '@/components';
import { useToast } from '@/store/useToast';

const PROJECT_TYPES = [
  'Posters',
  'Souvenirs',
  'Badges',
  'Stands',
  'Other',
];

interface FormData {
  // Step 1: Project Info
  name: string;
  type: string;
  description: string;
  tags: string[];
  // Step 2: Folder
  folder_path?: string;
  auto_create_folder: boolean;
  // Step 3: Timeline
  start_date: string;
  end_date: string;
  auto_renew: boolean;
  auto_renew_interval: number;
  // Step 4: Quotas
  max_ar_content: number;
  max_videos_per_content: number;
  max_storage_gb: number;
}

export default function ProjectFormWizard() {
  const navigate = useNavigate();
  const { companyId, id } = useParams<{ companyId: string; id?: string }>();
  const { showToast } = useToast();
  const [activeStep, setActiveStep] = useState(0);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [tagInput, setTagInput] = useState('');

  const [formData, setFormData] = useState<FormData>({
    name: '',
    type: 'Posters',
    description: '',
    tags: [],
    folder_path: `/companies/${companyId}/projects/new`,
    auto_create_folder: true,
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    auto_renew: false,
    auto_renew_interval: 12,
    max_ar_content: 50,
    max_videos_per_content: 10,
    max_storage_gb: 50,
  });

  const steps = [
    'Информация о проекте',
    'Папка хранилища',
    'Сроки действия',
    'Квоты',
    'Обзор',
  ];

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData((prev) => ({
        ...prev,
        tags: [...prev.tags, tagInput.trim()],
      }));
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setFormData((prev) => ({
      ...prev,
      tags: prev.tags.filter((t) => t !== tag),
    }));
  };

  const handleNext = () => {
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
      if (id && companyId) {
        // await projectsAPI.update(parseInt(id), formData);
        showToast('Проект обновлен', 'success');
      } else if (companyId) {
        await projectsAPI.create(parseInt(companyId), formData);
        showToast('Проект создан', 'success');
      }
      navigate(`/companies/${companyId}/projects`);
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Ошибка сохранения', 'error');
    } finally {
      setSubmitLoading(false);
    }
  };

  // Step 1: Project Info
  const renderStep1 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Название проекта"
              placeholder="например: Новый год 2025"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
            />
          </Grid>
          <Grid item xs={12}>
            <FormControl fullWidth>
              <InputLabel>Тип проекта</InputLabel>
              <Select
                value={formData.type}
                label="Тип проекта"
                onChange={(e) => handleChange('type', e.target.value)}
              >
                {PROJECT_TYPES.map((type) => (
                  <MenuItem key={type} value={type}>
                    {type}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Описание"
              placeholder="Опишите этот проект"
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              multiline
              rows={3}
            />
          </Grid>
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>Теги</Typography>
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <TextField
                size="small"
                placeholder="Добавить тег"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleAddTag();
                  }
                }}
                sx={{ flex: 1 }}
              />
              <Button variant="outlined" onClick={handleAddTag}>
                Добавить
              </Button>
            </Box>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {formData.tags.map((tag) => (
                <Chip
                  key={tag}
                  label={tag}
                  onDelete={() => handleRemoveTag(tag)}
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  // Step 2: Folder
  const renderStep2 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.auto_create_folder}
                  onChange={(e) => handleChange('auto_create_folder', e.target.checked)}
                />
              }
              label="Автоматически создать папку"
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Путь папки"
              value={formData.folder_path}
              onChange={(e) => handleChange('folder_path', e.target.value)}
              disabled={formData.auto_create_folder}
              helperText="Путь в хранилище проекта"
            />
          </Grid>
          <Grid item xs={12}>
            <Alert severity="info">
              📁 Папка будет создана в: /companies/{companyId}/projects/{formData.name.replace(/\s+/g, '-').toLowerCase()}
            </Alert>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  // Step 3: Timeline
  const renderStep3 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Дата начала"
              type="date"
              value={formData.start_date}
              onChange={(e) => handleChange('start_date', e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Дата окончания"
              type="date"
              value={formData.end_date}
              onChange={(e) => handleChange('end_date', e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
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
          {formData.auto_renew && (
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Интервал продления (месяцы)"
                type="number"
                value={formData.auto_renew_interval}
                onChange={(e) => handleChange('auto_renew_interval', parseInt(e.target.value) || 0)}
              />
            </Grid>
          )}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>Уведомления об истечении:</Typography>
            <FormGroup row>
              {[7, 14, 30].map((days) => (
                <FormControlLabel
                  key={days}
                  control={<Checkbox />}
                  label={`${days} дней`}
                />
              ))}
            </FormGroup>
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
              label="Макс. AR контента"
              type="number"
              value={formData.max_ar_content}
              onChange={(e) => handleChange('max_ar_content', parseInt(e.target.value) || 0)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Видео на контент"
              type="number"
              value={formData.max_videos_per_content}
              onChange={(e) => handleChange('max_videos_per_content', parseInt(e.target.value) || 0)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Макс. хранилище (GB)"
              type="number"
              value={formData.max_storage_gb}
              onChange={(e) => handleChange('max_storage_gb', parseInt(e.target.value) || 0)}
            />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  // Step 5: Review
  const renderStep5 = () => (
    <Card>
      <CardContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>📋 Обзор</Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
              <Typography variant="subtitle2" gutterBottom>Информация</Typography>
              <Typography><strong>Название:</strong> {formData.name}</Typography>
              <Typography><strong>Тип:</strong> {formData.type}</Typography>
              <Typography><strong>Теги:</strong> {formData.tags.join(', ') || 'нет'}</Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
              <Typography variant="subtitle2" gutterBottom>Сроки</Typography>
              <Typography><strong>С:</strong> {formData.start_date}</Typography>
              <Typography><strong>По:</strong> {formData.end_date}</Typography>
              <Typography><strong>Авто-продление:</strong> {formData.auto_renew ? '✓' : '✗'}</Typography>
            </Paper>
          </Grid>
          <Grid item xs={12}>
            <Paper sx={{ p: 2, backgroundColor: '#f5f5f5' }}>
              <Typography variant="subtitle2" gutterBottom>Квоты</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Typography><strong>AR контента:</strong> {formData.max_ar_content}</Typography>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Typography><strong>Видео/контент:</strong> {formData.max_videos_per_content}</Typography>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Typography><strong>Хранилище:</strong> {formData.max_storage_gb} GB</Typography>
                </Grid>
              </Grid>
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
  ];

  return (
    <PageContent>
      <PageHeader
        title={id ? 'Редактирование проекта' : 'Новый проект'}
        subtitle="5-шаговый процесс создания/редактирования"
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
          <Button onClick={() => navigate(`/companies/${companyId}/projects`)} variant="outlined">
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
