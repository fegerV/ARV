// ARContentDetailPage.tsx
import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Chip,
  IconButton,
  Button,
  Divider,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { AppLayout } from '@/components/(layout)/AppLayout';
import { PageHeader } from '@/components/(layout)/PageHeader';
import { MarkerStatusBadge } from '@/components/(media)/MarkerStatusBadge';
import { QRCodeCard } from '@/components/(media)/QRCodeCard';
import { Lightbox } from '@/components/(media)/Lightbox';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { VideoListVirtualized } from '@/components/(media)/VideoListVirtualized';
import { LazyImage } from '@/components/(media)/LazyImage';
import { arContentApi } from '@/services/ar-content';
import { ARContentDetail } from '@/types/ar-content-detail';

const ARContentDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [portraitOpen, setPortraitOpen] = useState(false);
  const [videoLightbox, setVideoLightbox] = useState<number | null>(null);

  const { data, isLoading, isError, refetch, error } = useQuery({
    queryKey: ['ar-content', id],
    queryFn: () => arContentApi.get(Number(id)),
    enabled: !!id
  });

  const content: ARContentDetail | undefined = data?.data;
  const publicUrl = content
    ? `https://ar.vertexar.com/view/${content.unique_id}`
    : '';

  if (isLoading || !content) {
    return (
      <AppLayout>
        <Container maxWidth="lg">
          <PageHeader title="Загрузка заказа..." breadcrumbs={[{ label: 'Проекты', href: '/projects' }]} />
          <LoadingState message="Загрузка деталей заказа..." />
        </Container>
      </AppLayout>
    );
  }

  if (isError) {
    return (
      <AppLayout>
        <Container maxWidth="lg">
          <PageHeader title="Заказ AR‑контента" breadcrumbs={[{ label: 'Проекты', href: '/projects' }]} />
          <ErrorState
            message={(error as any)?.response?.data?.detail}
            onRetry={() => refetch()}
          />
        </Container>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <PageHeader
          title={content.title}
          subtitle={`Компания: ${content.company_name} • Проект: ${content.project_name}`}
          breadcrumbs={[{ label: 'Проекты', href: `/projects/${content.project_id}/content` }]}
        />

        <Grid container spacing={3}>
          {/* Левая колонка: портрет + файл + маркер */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Портрет
              </Typography>
              <Box
                sx={{
                  borderRadius: 2,
                  overflow: 'hidden',
                  cursor: 'pointer',
                  mb: 2,
                }}
                onClick={() => setPortraitOpen(true)}
              >
                <LazyImage
                  src={content.image_url || content.thumbnail_url}
                  alt={content.title}
                  style={{ width: '100%', height: 'auto' }}
                />
              </Box>
              <Typography variant="body2" color="text.secondary">
                {content.image_width}×{content.image_height} •{' '}
                {content.image_size_readable}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Путь: {content.image_path}
              </Typography>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                NFT‑маркер
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <MarkerStatusBadge status={content.marker_status} />
                {content.marker_status === 'ready' && (
                  <Chip
                    size="small"
                    label={`${content.marker_feature_points} feature points`}
                  />
                )}
              </Box>
              {content.marker_url && (
                <Typography variant="body2" color="text.secondary">
                  Файл: {content.marker_path}
                </Typography>
              )}
              <Button
                size="small"
                sx={{ mt: 1 }}
                onClick={() =>
                  arContentApi.generateMarker(content.id).then(() => {
                    // можно добавить refetch
                  })
                }
              >
                Перегенерировать маркер
              </Button>
            </Paper>
          </Grid>

          {/* Правая колонка: ссылки, QR, видео, расписание, статистика */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Ссылка и QR‑код
              </Typography>
              <Box
                sx={{
                  display: 'flex',
                  gap: 1,
                  alignItems: 'center',
                  mb: 2,
                }}
              >
                <Box sx={{ flex: 1, overflow: 'hidden' }}>
                  <Typography
                    variant="body2"
                    sx={{
                      whiteSpace: 'nowrap',
                      textOverflow: 'ellipsis',
                      overflow: 'hidden',
                    }}
                  >
                    {publicUrl}
                  </Typography>
                </Box>
                <IconButton
                  size="small"
                  onClick={() => navigator.clipboard.writeText(publicUrl)}
                >
                  <ContentCopyIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => window.open(publicUrl, '_blank')}
                >
                  <OpenInNewIcon fontSize="small" />
                </IconButton>
              </Box>

              <QRCodeCard value={publicUrl} title="QR для печати" size={180} />
            </Paper>

            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Видеоанимации
              </Typography>
              {content.videos.length === 0 ? (
                <Box sx={{ py: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    Видео ещё не загружены
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ height: 320 }}>
                  <VideoListVirtualized
                    videos={content.videos}
                    onVideoClick={(video) => setVideoLightbox(video.id)}
                  />
                </Box>
              )}
            </Paper>

            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Расписание
              </Typography>
              {content.rotation_rule ? (
                <>
                  <Typography variant="body2">
                    Тип: {content.rotation_rule.type_human}
                  </Typography>
                  {content.rotation_rule.default_video_title && (
                    <Typography variant="body2">
                      По умолчанию:{' '}
                      {content.rotation_rule.default_video_title}
                    </Typography>
                  )}
                  {content.rotation_rule.next_change_at && (
                    <Typography variant="body2">
                      Следующая смена:{' '}
                      {content.rotation_rule.next_change_at_readable}
                    </Typography>
                  )}
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Расписание не настроено, используется одно видео.
                </Typography>
              )}
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Статистика (30 дней)
              </Typography>
              <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                <StatItem label="Просмотры" value={content.stats.views} />
                <StatItem
                  label="Уникальные сессии"
                  value={content.stats.unique_sessions}
                />
                <StatItem
                  label="Средняя длительность"
                  value={`${content.stats.avg_duration}s`}
                />
                <StatItem
                  label="Средний FPS"
                  value={content.stats.avg_fps.toFixed(1)}
                />
              </Box>
            </Paper>
          </Grid>
        </Grid>

        {/* Лайтбоксы */}
        <Lightbox
          open={portraitOpen}
          onClose={() => setPortraitOpen(false)}
          type="image"
          src={content.image_url}
          title={content.title}
        />
        {videoLightbox && (
          <Lightbox
            open={!!videoLightbox}
            onClose={() => setVideoLightbox(null)}
            type="video"
            src={
              content.videos.find((v) => v.id === videoLightbox)?.video_url ||
              ''
            }
            title={
              content.videos.find((v) => v.id === videoLightbox)?.title || ''
            }
          />
        )}
      </Container>
    </AppLayout>
  );
};

const StatItem = ({ label, value }: { label: string; value: string | number }) => (
  <Box>
    <Typography variant="h6">{value}</Typography>
    <Typography variant="caption" color="text.secondary">
      {label}
    </Typography>
  </Box>
);

export default ARContentDetailPage;