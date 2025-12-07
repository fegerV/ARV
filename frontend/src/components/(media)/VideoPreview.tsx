/**
 * VideoPreview - Компонент для отображения превью видео
 * Поддерживает три размера: small, medium, large
 * Показывает play icon overlay и badge с длительностью
 */
import React from 'react';
import { Box, Chip } from '@mui/material';
import { PlayCircle } from 'lucide-react';
import { LazyImage } from './LazyImage';

export interface Video {
  id: number;
  title?: string;
  video_url: string;
  thumbnail_url?: string;
  thumbnail_small_url?: string;
  thumbnail_large_url?: string;
  duration?: number;
  width?: number;
  height?: number;
  mime_type?: string;
  is_active?: boolean;
}

interface VideoPreviewProps {
  video: Video;
  size?: 'small' | 'medium' | 'large';
  onClick?: () => void;
  showDuration?: boolean;
  showPlayIcon?: boolean;
  className?: string;
}

/**
 * Форматирует длительность в секундах в MM:SS
 */
const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * VideoPreview компонент
 */
export const VideoPreview: React.FC<VideoPreviewProps> = ({
  video,
  size = 'medium',
  onClick,
  showDuration = true,
  showPlayIcon = true,
  className = '',
}) => {
  // Выбираем правильный URL превью в зависимости от размера
  const thumbnailUrl = React.useMemo(() => {
    const urls = {
      small: video.thumbnail_small_url,
      medium: video.thumbnail_url,
      large: video.thumbnail_large_url,
    };
    
    // Fallback: если нужный размер не доступен, используем любой доступный
    return urls[size] || video.thumbnail_url || video.thumbnail_small_url || video.thumbnail_large_url || '/placeholder-video.webp';
  }, [video, size]);

  return (
    <Box
      className={className}
      sx={{
        position: 'relative',
        cursor: onClick ? 'pointer' : 'default',
        borderRadius: 2,
        overflow: 'hidden',
        '&:hover .play-icon': {
          opacity: showPlayIcon ? 1 : 0,
          transform: 'scale(1.1)',
        },
        transition: 'transform 0.2s',
        '&:hover': onClick ? {
          transform: 'translateY(-2px)',
          boxShadow: 3,
        } : {},
      }}
      onClick={onClick}
    >
      {/* Thumbnail изображение */}
      <LazyImage
        src={thumbnailUrl}
        alt={video.title || 'Video preview'}
        style={{
          width: '100%',
          height: 'auto',
          backgroundColor: '#000',
        }}
      />

      {/* Play icon overlay */}
      {showPlayIcon && (
        <Box
          className="play-icon"
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            opacity: 0.85,
            transition: 'all 0.3s ease',
            pointerEvents: 'none',
            color: 'white',
            filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.5))',
          }}
        >
          <PlayCircle size={size === 'small' ? 32 : size === 'medium' ? 48 : 64} />
        </Box>
      )}

      {/* Duration badge */}
      {showDuration && video.duration && (
        <Chip
          label={formatDuration(video.duration)}
          size="small"
          sx={{
            position: 'absolute',
            bottom: 8,
            right: 8,
            bgcolor: 'rgba(0, 0, 0, 0.75)',
            color: 'white',
            fontWeight: 600,
            fontSize: '0.75rem',
            height: 24,
            '& .MuiChip-label': {
              px: 1,
            },
          }}
        />
      )}

      {/* Active badge */}
      {video.is_active && (
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

export default VideoPreview;
