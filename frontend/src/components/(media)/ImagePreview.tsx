/**
 * ImagePreview - Компонент для отображения превью портретов/изображений
 * Используется для AR контента
 */
import React from 'react';
import { Box, Chip, Skeleton } from '@mui/material';
import { Image as ImageIcon } from 'lucide-react';
import { LazyImage } from './LazyImage';

export interface ARContent {
  id: number;
  unique_id: string;
  title: string;
  image_url: string;
  thumbnail_url?: string;
  marker_status?: 'pending' | 'processing' | 'completed' | 'failed';
  is_active?: boolean;
}

interface ImagePreviewProps {
  arContent: ARContent;
  size?: 'small' | 'medium' | 'large';
  onClick?: () => void;
  showStatus?: boolean;
  loading?: boolean;
  className?: string;
}

/**
 * Получает цвет badge в зависимости от статуса маркера
 */
const getMarkerStatusColor = (status?: string): 'default' | 'warning' | 'success' | 'error' => {
  switch (status) {
    case 'completed':
      return 'success';
    case 'processing':
      return 'warning';
    case 'failed':
      return 'error';
    default:
      return 'default';
  }
};

/**
 * Получает текст для статуса маркера
 */
const getMarkerStatusLabel = (status?: string): string => {
  switch (status) {
    case 'completed':
      return 'Готов';
    case 'processing':
      return 'Обработка';
    case 'pending':
      return 'Ожидание';
    case 'failed':
      return 'Ошибка';
    default:
      return 'Неизвестно';
  }
};

/**
 * ImagePreview компонент
 */
export const ImagePreview: React.FC<ImagePreviewProps> = ({
  arContent,
  size = 'medium',
  onClick,
  showStatus = true,
  loading = false,
  className = '',
}) => {
  // Выбираем URL изображения (превью или оригинал)
  const imageUrl = React.useMemo(() => {
    // Для портретов используем среднее превью или оригинал
    return arContent.thumbnail_url || arContent.image_url;
  }, [arContent]);

  if (loading) {
    return (
      <Skeleton
        variant="rectangular"
        sx={{
          borderRadius: 2,
          aspectRatio: '16/9',
          width: '100%',
        }}
      />
    );
  }

  return (
    <Box
      className={className}
      sx={{
        position: 'relative',
        cursor: onClick ? 'pointer' : 'default',
        borderRadius: 2,
        overflow: 'hidden',
        transition: 'all 0.2s ease',
        '&:hover': onClick
          ? {
              transform: 'translateY(-2px)',
              boxShadow: 3,
            }
          : {},
        '&:hover .image-overlay': {
          opacity: 1,
        },
      }}
      onClick={onClick}
    >
      {/* Изображение */}
      <LazyImage
        src={imageUrl}
        alt={arContent.title}
        style={{
          width: '100%',
          height: 'auto',
          backgroundColor: '#f5f5f5',
        }}
        onError={(e) => {
          // Fallback на placeholder при ошибке загрузки
          (e.target as HTMLImageElement).src = '/placeholder-image.webp';
        }}
      />

      {/* Overlay при hover */}
      {onClick && (
        <Box
          className="image-overlay"
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            bgcolor: 'rgba(0, 0, 0, 0.3)',
            opacity: 0,
            transition: 'opacity 0.3s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <ImageIcon size={size === 'small' ? 32 : size === 'medium' ? 48 : 64} color="white" />
        </Box>
      )}

      {/* Marker status badge */}
      {showStatus && arContent.marker_status && (
        <Chip
          label={getMarkerStatusLabel(arContent.marker_status)}
          size="small"
          color={getMarkerStatusColor(arContent.marker_status)}
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            fontWeight: 600,
            fontSize: '0.7rem',
            height: 24,
          }}
        />
      )}

      {/* Active badge */}
      {arContent.is_active && (
        <Chip
          label="Активно"
          size="small"
          color="success"
          sx={{
            position: 'absolute',
            top: 8,
            left: 8,
            fontWeight: 600,
            fontSize: '0.7rem',
            height: 24,
          }}
        />
      )}
    </Box>
  );
};

export default ImagePreview;
