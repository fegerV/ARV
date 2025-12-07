// components/media/VideoListVirtualizedUsageExample.tsx
// Пример использования VideoListVirtualized в ARContentDetailPage

import React from 'react';
import { Paper, Typography } from '@mui/material';
import { VideoListVirtualized } from './VideoListVirtualized';

// Пример использования в ARContentDetailPage:
/*
// Вместо текущего блока с видео (строки 184-205):
<Paper sx={{ p: 2, mb: 2 }}>
  <Typography variant="h6" gutterBottom>
    Видеоанимации
  </Typography>
  {content.videos.length === 0 ? (
    <Typography variant="body2" color="text.secondary">
      Видео ещё не загружены
    </Typography>
  ) : (
    <VideoListVirtualized
      videos={content.videos}
      onVideoClick={(video) => setVideoLightbox(video.id)}
    />
  )}
</Paper>
*/

// Это улучшение позволяет:
// 1. Лениво загружать превью видео через LazyImage
// 2. Виртуализировать список для лучшей производительности при большом количестве видео
// 3. Сохранить весь существующий функционал (лайтбоксы, клики и т.д.)

export const VideoListVirtualizedUsageExample = () => {
  return (
    <div>
      <Typography variant="h6" gutterBottom>
        Пример использования VideoListVirtualized
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Этот компонент следует использовать в ARContentDetailPage для отображения списка видео.
      </Typography>
    </div>
  );
};