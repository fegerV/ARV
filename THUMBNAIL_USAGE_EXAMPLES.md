# 📸 Примеры использования компонентов превью

Практические примеры интеграции VideoPreview и ImagePreview в реальные страницы админ-панели.

---

## 🎬 VideoPreview - Примеры использования

### 1. Список видео в AR контенте

**Страница**: `frontend/src/pages/ar-content/ARContentDetail.tsx`

```tsx
import React, { useState, useEffect } from 'react';
import { Grid, Box, Typography, Button } from '@mui/material';
import { Plus } from 'lucide-react';
import { VideoPreview } from '@/components/(media)';
import api from '@/services/api';

interface ARContentDetailProps {
  arContentId: number;
}

const ARContentDetail: React.FC<ARContentDetailProps> = ({ arContentId }) => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadVideos();
  }, [arContentId]);

  const loadVideos = async () => {
    try {
      const response = await api.get(`/ar-content/${arContentId}/videos`);
      setVideos(response.data);
    } finally {
      setLoading(false);
    }
  };

  const handleVideoClick = (videoId: number) => {
    // Открыть модальное окно с превью/плеером
    console.log('Play video:', videoId);
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" mb={3}>
        <Typography variant="h5">Видео</Typography>
        <Button startIcon={<Plus />} variant="contained">
          Загрузить видео
        </Button>
      </Box>

      <Grid container spacing={2}>
        {videos.map((video) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={video.id}>
            <VideoPreview
              video={video}
              size="medium"
              onClick={() => handleVideoClick(video.id)}
              showDuration={true}
              showPlayIcon={true}
            />
            <Typography variant="body2" mt={1} noWrap>
              {video.title}
            </Typography>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default ARContentDetail;
```

### 2. Карточка видео с действиями

```tsx
import React from 'react';
import { Card, CardContent, CardActions, Button, IconButton, Menu, MenuItem } from '@mui/material';
import { MoreVertical, Edit, Trash2, Calendar } from 'lucide-react';
import { VideoPreview } from '@/components/(media)';

const VideoCard: React.FC<{ video: Video }> = ({ video }) => {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  return (
    <Card>
      <VideoPreview
        video={video}
        size="medium"
        onClick={() => console.log('Open video player')}
      />
      
      <CardContent>
        <Typography variant="h6" noWrap>
          {video.title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {video.width}x{video.height} • {(video.size_bytes / 1024 / 1024).toFixed(2)} MB
        </Typography>
      </CardContent>

      <CardActions>
        <Button size="small" startIcon={<Calendar />}>
          Расписание
        </Button>
        <IconButton 
          size="small" 
          onClick={(e) => setAnchorEl(e.currentTarget)}
        >
          <MoreVertical size={20} />
        </IconButton>
        
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={() => setAnchorEl(null)}
        >
          <MenuItem onClick={() => console.log('Edit')}>
            <Edit size={16} style={{ marginRight: 8 }} />
            Редактировать
          </MenuItem>
          <MenuItem onClick={() => console.log('Delete')}>
            <Trash2 size={16} style={{ marginRight: 8 }} />
            Удалить
          </MenuItem>
        </Menu>
      </CardActions>
    </Card>
  );
};
```

### 3. Компактный список (small размер)

```tsx
import React from 'react';
import { List, ListItem, ListItemAvatar, ListItemText, IconButton } from '@mui/material';
import { Trash2 } from 'lucide-react';
import { VideoPreview } from '@/components/(media)';

const VideoListCompact: React.FC<{ videos: Video[] }> = ({ videos }) => {
  return (
    <List>
      {videos.map((video) => (
        <ListItem
          key={video.id}
          secondaryAction={
            <IconButton edge="end" onClick={() => handleDelete(video.id)}>
              <Trash2 size={20} />
            </IconButton>
          }
        >
          <ListItemAvatar sx={{ width: 120, height: 68, mr: 2 }}>
            <VideoPreview
              video={video}
              size="small"
              showPlayIcon={false}
              showDuration={true}
            />
          </ListItemAvatar>
          <ListItemText
            primary={video.title}
            secondary={`${video.duration}s • ${video.mime_type}`}
          />
        </ListItem>
      ))}
    </List>
  );
};
```

---

## 🖼️ ImagePreview - Примеры использования

### 1. Галерея AR контента

**Страница**: `frontend/src/pages/ar-content/ARContentList.tsx`

```tsx
import React, { useState, useEffect } from 'react';
import { Grid, Box, Typography, Chip } from '@mui/material';
import { ImagePreview } from '@/components/(media)';
import api from '@/services/api';

const ARContentList: React.FC<{ projectId: number }> = ({ projectId }) => {
  const [contents, setContents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadContents();
  }, [projectId]);

  const loadContents = async () => {
    try {
      const response = await api.get(`/projects/${projectId}/ar-content`);
      setContents(response.data.items);
    } finally {
      setLoading(false);
    }
  };

  const handleContentClick = (contentId: number) => {
    // Перейти на детальную страницу
    window.location.href = `/ar-content/${contentId}`;
  };

  return (
    <Grid container spacing={3}>
      {loading ? (
        // Skeleton loaders
        Array.from({ length: 6 }).map((_, idx) => (
          <Grid item xs={12} sm={6} md={4} key={idx}>
            <ImagePreview
              arContent={{} as any}
              loading={true}
            />
          </Grid>
        ))
      ) : (
        contents.map((content) => (
          <Grid item xs={12} sm={6} md={4} key={content.id}>
            <Box>
              <ImagePreview
                arContent={content}
                size="medium"
                onClick={() => handleContentClick(content.id)}
                showStatus={true}
              />
              
              <Box mt={1}>
                <Typography variant="h6" noWrap>
                  {content.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  ID: {content.unique_id.slice(0, 8)}
                </Typography>
              </Box>
            </Box>
          </Grid>
        ))
      )}
    </Grid>
  );
};
```

### 2. Карточка AR контента с метаданными

```tsx
import React from 'react';
import { Card, CardContent, CardActions, Button, Box, Chip } from '@mui/material';
import { QrCode, Eye, Settings } from 'lucide-react';
import { ImagePreview } from '@/components/(media)';

const ARContentCard: React.FC<{ content: ARContent }> = ({ content }) => {
  return (
    <Card>
      <ImagePreview
        arContent={content}
        size="medium"
        onClick={() => window.open(`/ar/${content.unique_id}`, '_blank')}
        showStatus={true}
      />
      
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {content.title}
        </Typography>
        
        <Box display="flex" gap={1} flexWrap="wrap">
          <Chip
            label={`Просмотры: ${content.views_count || 0}`}
            size="small"
            icon={<Eye size={14} />}
          />
          {content.expires_at && (
            <Chip
              label={`До: ${new Date(content.expires_at).toLocaleDateString()}`}
              size="small"
              color={new Date(content.expires_at) < new Date() ? 'error' : 'default'}
            />
          )}
        </Box>
      </CardContent>

      <CardActions>
        <Button size="small" startIcon={<QrCode />}>
          QR код
        </Button>
        <Button size="small" startIcon={<Settings />}>
          Настройки
        </Button>
      </CardActions>
    </Card>
  );
};
```

### 3. Таблица с превью

```tsx
import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
} from '@mui/material';
import { Edit, Trash2 } from 'lucide-react';
import { ImagePreview } from '@/components/(media)';

const ARContentTable: React.FC<{ contents: ARContent[] }> = ({ contents }) => {
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell width={200}>Превью</TableCell>
            <TableCell>Название</TableCell>
            <TableCell>Статус</TableCell>
            <TableCell>Просмотры</TableCell>
            <TableCell align="right">Действия</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {contents.map((content) => (
            <TableRow key={content.id}>
              <TableCell>
                <Box width={150}>
                  <ImagePreview
                    arContent={content}
                    size="small"
                    showStatus={false}
                  />
                </Box>
              </TableCell>
              <TableCell>
                <Typography variant="body1">{content.title}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {content.unique_id}
                </Typography>
              </TableCell>
              <TableCell>
                <Chip
                  label={content.marker_status}
                  size="small"
                  color={content.marker_status === 'completed' ? 'success' : 'default'}
                />
              </TableCell>
              <TableCell>{content.views_count || 0}</TableCell>
              <TableCell align="right">
                <IconButton size="small">
                  <Edit size={18} />
                </IconButton>
                <IconButton size="small" color="error">
                  <Trash2 size={18} />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};
```

---

## 🎨 Стилизация и кастомизация

### Пример с кастомными стилями

```tsx
import { VideoPreview } from '@/components/(media)';

<VideoPreview
  video={video}
  size="large"
  className="custom-video-preview"
  sx={{
    // Дополнительные MUI sx props
    border: '2px solid',
    borderColor: 'primary.main',
    boxShadow: 4,
  }}
/>
```

### Темная тема

```tsx
import { useTheme } from '@mui/material/styles';

const VideoGallery = () => {
  const theme = useTheme();
  
  return (
    <VideoPreview
      video={video}
      style={{
        backgroundColor: theme.palette.mode === 'dark' ? '#1a1a1a' : '#fff',
      }}
    />
  );
};
```

---

## 🚀 Best Practices

### 1. Lazy Loading списков

```tsx
import React from 'react';
import { FixedSizeGrid } from 'react-window';
import { VideoPreview } from '@/components/(media)';

const VideoGrid: React.FC<{ videos: Video[] }> = ({ videos }) => {
  const Cell = ({ columnIndex, rowIndex, style }) => {
    const index = rowIndex * 4 + columnIndex;
    const video = videos[index];
    
    if (!video) return null;
    
    return (
      <div style={style}>
        <VideoPreview video={video} size="small" />
      </div>
    );
  };

  return (
    <FixedSizeGrid
      columnCount={4}
      columnWidth={200}
      height={600}
      rowCount={Math.ceil(videos.length / 4)}
      rowHeight={150}
      width={1000}
    >
      {Cell}
    </FixedSizeGrid>
  );
};
```

### 2. Оптимизация рендера

```tsx
import React, { memo } from 'react';
import { VideoPreview } from '@/components/(media)';

const VideoCard = memo<{ video: Video }>(({ video }) => {
  return <VideoPreview video={video} />;
}, (prev, next) => {
  // Ре-рендер только если изменился URL превью
  return prev.video.thumbnail_url === next.video.thumbnail_url;
});
```

### 3. Error Boundaries

```tsx
import React from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { VideoPreview } from '@/components/(media)';

const SafeVideoPreview: React.FC<{ video: Video }> = ({ video }) => {
  return (
    <ErrorBoundary
      fallback={
        <Box
          sx={{
            aspectRatio: '16/9',
            bgcolor: 'grey.200',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Typography color="error">Ошибка загрузки превью</Typography>
        </Box>
      }
    >
      <VideoPreview video={video} />
    </ErrorBoundary>
  );
};
```

---

## 📱 Адаптивность

### Mobile-first подход

```tsx
import { useMediaQuery, useTheme } from '@mui/material';

const ResponsiveGallery: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.between('sm', 'md'));
  
  const videoSize = isMobile ? 'small' : isTablet ? 'medium' : 'large';
  
  return (
    <Grid container spacing={isMobile ? 1 : 2}>
      {videos.map(video => (
        <Grid item xs={12} sm={6} md={4} lg={3}>
          <VideoPreview video={video} size={videoSize} />
        </Grid>
      ))}
    </Grid>
  );
};
```

---

## ✅ Чеклист интеграции

- [ ] Импортировать компонент из `@/components/(media)`
- [ ] Добавить типы `Video` или `ARContent`
- [ ] Обработать состояние `loading` (skeleton)
- [ ] Добавить обработчик `onClick` (опционально)
- [ ] Проверить fallback для отсутствующих превью
- [ ] Добавить error boundary
- [ ] Протестировать на мобильных устройствах
- [ ] Проверить lazy loading изображений
- [ ] Оптимизировать ре-рендеры (memo)

---

**Готовые к использованию компоненты!** 🚀
