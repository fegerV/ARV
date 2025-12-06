// components/(forms)/ScheduleEditor.tsx
import React from 'react';
import {
  Box,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  IconButton
} from '@mui/material';
import { Add, Delete } from '@mui/icons-material';
import { VideoRotationRule } from '../../types/ar-content';

interface ScheduleEditorProps {
  rotationType: 'fixed' | 'daily' | 'date_specific' | 'random';
  rotationRule: VideoRotationRule;
  onChange: (rule: VideoRotationRule) => void;
}

export const ScheduleEditor: React.FC<ScheduleEditorProps> = ({ rotationType, rotationRule, onChange }) => {
  // Mock list of videos for selection
  const mockVideos = [
    { id: '1', title: 'Видео 1' },
    { id: '2', title: 'Видео 2' },
    { id: '3', title: 'Видео 3' }
  ];

  const handleDefaultVideoChange = (videoId: string) => {
    onChange({
      ...rotationRule,
      default_video_id: videoId
    });
  };

  const handleAddDateRule = () => {
    const newDateRule = {
      date: new Date().toISOString().split('T')[0],
      video_id: ''
    };
    
    onChange({
      ...rotationRule,
      date_rules: [...(rotationRule.date_rules || []), newDateRule]
    });
  };

  const handleDateRuleChange = (index: number, field: string, value: string) => {
    const updatedRules = [...(rotationRule.date_rules || [])];
    updatedRules[index] = { ...updatedRules[index], [field]: value };
    
    onChange({
      ...rotationRule,
      date_rules: updatedRules
    });
  };

  const handleRemoveDateRule = (index: number) => {
    const updatedRules = [...(rotationRule.date_rules || [])];
    updatedRules.splice(index, 1);
    
    onChange({
      ...rotationRule,
      date_rules: updatedRules
    });
  };

  return (
    <Box>
      {/* Default video selector */}
      <FormControl fullWidth sx={{ mb: 3 }}>
        <InputLabel>Видео по умолчанию</InputLabel>
        <Select
          value={rotationRule.default_video_id || ''}
          label="Видео по умолчанию"
          onChange={(e) => handleDefaultVideoChange(e.target.value)}
        >
          {mockVideos.map((video) => (
            <MenuItem key={video.id} value={video.id}>
              {video.title}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Date-specific schedule */}
      {rotationType === 'date_specific' && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Специальное расписание
          </Typography>
          
          {(rotationRule.date_rules || []).map((rule, index) => (
            <Box key={index} sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
              <TextField
                type="date"
                value={rule.date}
                onChange={(e) => handleDateRuleChange(index, 'date', e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
              
              <FormControl sx={{ minWidth: 200 }}>
                <InputLabel>Видео</InputLabel>
                <Select
                  value={rule.video_id}
                  label="Видео"
                  onChange={(e) => handleDateRuleChange(index, 'video_id', e.target.value)}
                >
                  {mockVideos.map((video) => (
                    <MenuItem key={video.id} value={video.id}>
                      {video.title}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <IconButton onClick={() => handleRemoveDateRule(index)}>
                <Delete />
              </IconButton>
            </Box>
          ))}
          
          <Button
            startIcon={<Add />}
            onClick={handleAddDateRule}
            variant="outlined"
          >
            Добавить правило
          </Button>
        </Box>
      )}

      {/* Video sequence for daily rotation */}
      {rotationType === 'daily' && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Порядок ежедневной ротации
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Выберите порядок воспроизведения видео (будет повторяться циклически)
          </Typography>
          {/* In a real implementation, this would be a drag-and-drop list */}
          <Typography>Функционал настройки последовательности будет реализован в следующих версиях</Typography>
        </Box>
      )}

      {/* Random playback info */}
      {rotationType === 'random' && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Случайное воспроизведение
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Видео будут воспроизводиться в случайном порядке
          </Typography>
        </Box>
      )}
    </Box>
  );
};