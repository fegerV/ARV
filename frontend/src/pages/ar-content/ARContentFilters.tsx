// pages/Projects/ARContent/ARContentFilters.tsx
import React from 'react';
import {
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Stack,
  IconButton
} from '@mui/material';
import { RestartAlt as RestartAltIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { useARContentList } from '../../hooks/useARContentList';

export const ARContentFilters: React.FC = () => {
  const { filters, updateFilters, resetFilters, refetch } = useARContentList();

  // Mock companies data
  const companies = [
    { id: 1, name: 'Креативное агентство' },
    { id: 2, name: 'Арт-студия' },
    { id: 3, name: 'БрендПро' }
  ];

  // Mock projects data
  const projects = [
    { id: 1, name: 'Новогодняя кампания' },
    { id: 2, name: 'Выставка современного искусства' },
    { id: 3, name: 'Промо нового продукта' }
  ];

  return (
    <Box sx={{ mb: 3, p: 3, bgcolor: 'background.paper', borderRadius: 2 }}>
      <Stack direction="row" spacing={2} flexWrap="wrap" alignItems="center">
        {/* Поиск */}
        <TextField
          size="small"
          label="Поиск по названию"
          value={filters.search}
          onChange={(e) => updateFilters({ search: e.target.value })}
          sx={{ minWidth: 250 }}
        />
        
        {/* Компания */}
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Компания</InputLabel>
          <Select
            value={filters.company_id || ''}
            label="Компания"
            onChange={(e) => updateFilters({ company_id: Number(e.target.value) || undefined })}
          >
            <MenuItem value="">Все компании</MenuItem>
            {companies.map((company) => (
              <MenuItem key={company.id} value={company.id}>
                {company.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        {/* Проект */}
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Проект</InputLabel>
          <Select
            value={filters.project_id || ''}
            label="Проект"
            onChange={(e) => updateFilters({ project_id: Number(e.target.value) || undefined })}
          >
            <MenuItem value="">Все проекты</MenuItem>
            {projects.map((project) => (
              <MenuItem key={project.id} value={project.id}>
                {project.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        {/* Статус маркера */}
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Статус маркера</InputLabel>
          <Select
            value={filters.marker_status || ''}
            label="Статус маркера"
            onChange={(e) => updateFilters({ marker_status: e.target.value as any || undefined })}
          >
            <MenuItem value="">Все</MenuItem>
            <MenuItem value="pending">⏳ Ожидание</MenuItem>
            <MenuItem value="processing">🔄 Генерация</MenuItem>
            <MenuItem value="ready">✅ Готово</MenuItem>
            <MenuItem value="failed">❌ Ошибка</MenuItem>
          </Select>
        </FormControl>
        
        {/* Активность */}
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Статус</InputLabel>
          <Select
            value={filters.is_active?.toString() || ''}
            label="Статус"
            onChange={(e) => updateFilters({ is_active: e.target.value === 'true' })}
          >
            <MenuItem value="">Все</MenuItem>
            <MenuItem value="true">✅ Активно</MenuItem>
            <MenuItem value="false">⏸️ Неактивно</MenuItem>
          </Select>
        </FormControl>
        
        {/* Быстрые действия */}
        <Box sx={{ ml: 'auto' }}>
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              size="small"
              onClick={resetFilters}
              startIcon={<RestartAltIcon />}
            >
              Сбросить
            </Button>
            <Button
              variant="contained"
              size="small"
              onClick={() => refetch()}
              startIcon={<RefreshIcon />}
            >
              Обновить
            </Button>
          </Stack>
        </Box>
      </Stack>
    </Box>
  );
};