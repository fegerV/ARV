// pages/Projects/ARContent/Step4Schedule.tsx
import React, { useState } from 'react';
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import { ScheduleEditor } from '../../components';
import { useWizard } from './useWizard';
import { VideoRotationRule } from '../../types/ar-content';

export const Step4Schedule: React.FC = () => {
  const { data, setData } = useWizard();
  const [rotationType, setRotationType] = useState<'fixed' | 'daily' | 'date_specific' | 'random'>('daily');

  const handleRotationRuleChange = (rule: VideoRotationRule) => {
    setData(prev => ({
      ...prev,
      rotationRule: rule
    }));
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom align="center">
        Настройте расписание
      </Typography>
      <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 4 }}>
        Определите, как будут воспроизводиться ваши видео
      </Typography>
      
      <FormControl fullWidth sx={{ mb: 3 }}>
        <InputLabel>Тип ротации</InputLabel>
        <Select
          value={rotationType}
          label="Тип ротации"
          onChange={(e) => setRotationType(e.target.value as any)}
        >
          <MenuItem value="fixed">Фиксированное видео</MenuItem>
          <MenuItem value="daily">Ежедневная ротация</MenuItem>
          <MenuItem value="date_specific">Специальное расписание</MenuItem>
          <MenuItem value="random">Случайное воспроизведение</MenuItem>
        </Select>
      </FormControl>
      
      <ScheduleEditor
        rotationType={rotationType}
        rotationRule={data.rotationRule || {
          type: 'daily',
          default_video_id: '',
          date_rules: [],
          video_sequence: []
        }}
        onChange={handleRotationRuleChange}
      />
    </Box>
  );
};