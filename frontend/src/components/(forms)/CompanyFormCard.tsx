// components/(forms)/CompanyFormCard.tsx
import React from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  CardActions, 
  Typography, 
  TextField, 
  Button, 
  CircularProgress,
  Alert,
  useTheme
} from '@mui/material';
import { StorageConnectionForm } from './StorageConnectionForm';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { companiesAPI } from '@/services/api';
import { Company } from '@/types/company';
import { useNavigate } from 'react-router-dom';
import { useToast } from '@/store/useToast';

const companySchema = z.object({
  name: z.string().min(2, 'Название не менее 2 символов').max(255),
  slug: z.string().min(3, 'Слаг не менее 3 символов').regex(/^[a-z0-9-]+$/, 'Только латиница, цифры, дефис'),
  contact_email: z.string().email('Неверный email').optional().or(z.literal('')),
  contact_phone: z.string().optional().or(z.literal('')),
  storage_connection_id: z.number().min(1),
  storage_path: z.string().min(1, 'Укажите путь к папке'),
  storage_quota_gb: z.number().min(1).max(1000).optional(),
});

type CompanyFormData = z.infer<typeof companySchema>;

interface CompanyFormCardProps {
  existingCompany?: Company;
}

export const CompanyFormCard: React.FC<CompanyFormCardProps> = ({ existingCompany }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [connectionId, setConnectionId] = React.useState(1);
  const [storagePath, setStoragePath] = React.useState('/demo');
  
  const {
    control,
    handleSubmit,
    formState: { errors, isValid, isSubmitting },
    watch,
    setValue
  } = useForm<CompanyFormData>({
    resolver: zodResolver(companySchema),
    defaultValues: existingCompany || {
      name: '',
      slug: '',
      contact_email: '',
      contact_phone: '',
      storage_connection_id: 1,
      storage_path: '/demo',
      storage_quota_gb: undefined
    }
  });

  const name = watch('name');
  
  React.useEffect(() => {
    // Автогенерация slug из name
    if (name) {
      const slug = name
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .trim()
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-');
      setValue('slug', slug);
    }
  }, [name, setValue]);

  const onSubmit = async (data: CompanyFormData) => {
    try {
      // Prepare company data
      const companyData: any = {
        name: data.name,
        slug: data.slug,
        storage_connection_id: data.storage_connection_id,
        storage_path: data.storage_path,
        ...(data.contact_email && { contact_email: data.contact_email }),
        ...(data.contact_phone && { contact_phone: data.contact_phone }),
        ...(data.storage_quota_gb && { storage_quota_gb: data.storage_quota_gb }),
      };
      
      const response = await companiesAPI.create(companyData);
      const company: Company = response.data;
      
      showToast(`Компания "${company.name}" создана!`, 'success');
      navigate(`/companies/${company.id}`);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Ошибка создания компании';
      showToast(errorMessage, 'error');
    }
  };

  return (
    <Card sx={{ maxWidth: 600, mx: 'auto' }}>
      <CardContent sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          {existingCompany ? 'Редактировать компанию' : 'Новая компания'}
        </Typography>
        
        <form onSubmit={handleSubmit(onSubmit)}>
          <Controller
            name="name"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                fullWidth
                label="Название компании *"
                error={!!errors.name}
                helperText={errors.name?.message}
                sx={{ mb: 3 }}
                data-testid="company-name"
              />
            )}
          />
          
          <Controller
            name="slug"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                fullWidth
                label="URL slug *"
                placeholder="company-name"
                error={!!errors.slug}
                helperText={errors.slug?.message || 'Используется в ссылках'}
                sx={{ mb: 3 }}
                data-testid="company-slug"
              />
            )}
          />
          
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom sx={{ mb: 1 }}>
              Контакты
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <Controller
                name="contact_email"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Email"
                    type="email"
                    error={!!errors.contact_email}
                    helperText={errors.contact_email?.message}
                    data-testid="contact-email"
                  />
                )}
              />
              
              <Controller
                name="contact_phone"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Телефон"
                    error={!!errors.contact_phone}
                    helperText={errors.contact_phone?.message}
                    data-testid="contact-phone"
                  />
                )}
              />
            </Box>
          </Box>
          
          <StorageConnectionForm 
            onConnectionSelect={(id, path) => {
              setConnectionId(id);
              setStoragePath(path);
              setValue('storage_connection_id', id);
              setValue('storage_path', path);
            }}
          />
          
          <Controller
            name="storage_quota_gb"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                fullWidth
                label="Квота хранилища (ГБ)"
                type="number"
                InputProps={{ inputProps: { min: 1, max: 1000 } }}
                error={!!errors.storage_quota_gb}
                helperText={errors.storage_quota_gb?.message || 'Максимум 1000 ГБ'}
                sx={{ mb: 3 }}
                data-testid="storage-quota"
              />
            )}
          />
          
          <CardActions sx={{ justifyContent: 'flex-end', gap: 2 }}>
            <Button 
              variant="outlined" 
              onClick={() => navigate('/companies')}
              disabled={isSubmitting}
            >
              Отмена
            </Button>
            <Button 
              type="submit" 
              variant="contained" 
              disabled={!isValid || isSubmitting}
              startIcon={isSubmitting ? <CircularProgress size={20} /> : null}
              data-testid="create-company-button"
            >
              {isSubmitting ? 'Создание...' : 'Создать компанию'}
            </Button>
          </CardActions>
        </form>
      </CardContent>
    </Card>
  );
};