import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  Chip,
  IconButton,
  TextField,
  Card,
  CardContent,
  CardMedia,
  Divider,
  Dialog,
  DialogContent,
  DialogTitle,
  DialogActions,
  Skeleton,
  CircularProgress,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  QrCode as QrCodeIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ContentCopy as CopyIcon,
  OpenInNew as OpenIcon,
  Download as DownloadIcon,
  PlayArrow as PlayIcon,
  Close as CloseIcon,
  Analytics as AnalyticsIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
} from '@mui/icons-material';
import QRCode from 'qrcode.react';
import { format } from 'date-fns';
import { arContentAPI } from '../../services/api';
import { useToast } from '../../store/useToast';
import { downloadQRAsPNG, downloadQRAsSVG, downloadQRAsPDF } from '../../utils/qrCodeExport';

interface ARContentDetailProps {
  id: number;
  title: string;
  uniqueId: string;
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  imageSize: number;
  mimeType: string;
  markerStatus: 'pending' | 'processing' | 'ready' | 'failed';
  markerFileName?: string;
  markerSize?: number;
  markerFeaturePoints?: number;
  markerGenerationTime?: number;
  createdAt: string;
  createdBy: string;
}

interface VideoInfo {
  id: number;
  fileName: string;
  fileSize: number;
  duration: number;
  width: number;
  height: number;
  fps: number;
  codec: string;
  previewUrl: string;
  videoUrl: string;
  isActive: boolean;
  scheduleType?: 'default' | 'date_specific' | 'daily_cycle';
  scheduleDate?: string;
}

interface Stats {
  totalViews: number;
  uniqueSessions: number;
  avgSessionDuration: number;
  avgFps: number;
  deviceBreakdown: { device: string; percentage: number }[];
}

export default function ARContentDetail() {
  const { arContentId } = useParams<{ arContentId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const qrCanvasRef = useRef<HTMLCanvasElement>(null);
  
  const [content, setContent] = useState<ARContentDetailProps | null>(null);
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [company, setCompany] = useState<{ name: string } | null>(null);
  const [project, setProject] = useState<{ name: string } | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [portraitLightbox, setPortraitLightbox] = useState(false);
  const [videoLightbox, setVideoLightbox] = useState<VideoInfo | null>(null);
  const [qrDialog, setQrDialog] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [downloadingQR, setDownloadingQR] = useState(false);

  useEffect(() => {
    fetchContentDetail();
  }, [arContentId]);

  const fetchContentDetail = async () => {
    setLoading(true);
    try {
      const response = await arContentAPI.getDetail(Number(arContentId));
      const data = response.data;
      
      setContent(data.arContent);
      setVideos(data.videos || []);
      setStats(data.stats);
      setCompany(data.company);
      setProject(data.project);
      
      showToast('Content loaded successfully', 'success');
    } catch (error: any) {
      showToast(
        error.response?.data?.message || 'Failed to load AR content',
        'error'
      );
      console.error('Failed to fetch content:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await arContentAPI.delete(Number(arContentId));
      showToast('AR content deleted successfully', 'success');
      navigate(-1);
    } catch (error: any) {
      showToast(
        error.response?.data?.message || 'Failed to delete AR content',
        'error'
      );
      console.error('Failed to delete:', error);
    } finally {
      setDeleting(false);
      setDeleteDialog(false);
    }
  };

  const handleEdit = () => {
    navigate(`/ar-content/${arContentId}/edit`);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Copied to clipboard!', 'success');
    }).catch(() => {
      showToast('Failed to copy', 'error');
    });
  };

  const handleDownloadQR = async (format: 'png' | 'svg' | 'pdf') => {
    if (!content) return;
    
    setDownloadingQR(true);
    try {
      const canvas = qrCanvasRef.current;
      if (!canvas) {
        showToast('QR code not ready', 'error');
        return;
      }

      const filename = `qr-${content.uniqueId}.${format}`;
      const arUrl = `https://ar.vertexar.com/view/${content.uniqueId}`;

      switch (format) {
        case 'png':
          downloadQRAsPNG(canvas, filename);
          break;
        case 'svg':
          await downloadQRAsSVG(arUrl, filename);
          break;
        case 'pdf':
          await downloadQRAsPDF(canvas, filename, arUrl);
          break;
      }

      showToast(`QR code downloaded as ${format.toUpperCase()}`, 'success');
    } catch (error) {
      showToast('Failed to download QR code', 'error');
      console.error('Download error:', error);
    } finally {
      setDownloadingQR(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
        <Skeleton variant="rectangular" height={60} sx={{ mb: 3 }} />
        <Skeleton variant="rectangular" height={100} sx={{ mb: 3 }} />
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Skeleton variant="rectangular" height={400} />
          </Grid>
          <Grid item xs={12} md={6}>
            <Skeleton variant="rectangular" height={400} />
          </Grid>
        </Grid>
      </Box>
    );
  }

  if (!content) return <Typography>AR content not found</Typography>;

  const arUrl = `https://ar.vertexar.com/view/${content.uniqueId}`;

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton onClick={() => navigate(-1)}>
            <BackIcon />
          </IconButton>
          <Typography variant="h4">
            🎬 {content.title}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" startIcon={<QrCodeIcon />} onClick={() => setQrDialog(true)}>
            QR-код
          </Button>
          <Button variant="outlined" startIcon={<EditIcon />} onClick={handleEdit}>
            Редактировать
          </Button>
          <Button 
            variant="outlined" 
            color="error" 
            startIcon={<DeleteIcon />}
            onClick={() => setDeleteDialog(true)}
          >
            Удалить
          </Button>
        </Box>
      </Box>

      {/* Company & Project Info */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Chip label={`🏢 ${company?.name}`} />
          <Chip label={`📁 ${project?.name}`} />
          <Chip label={`👤 ${content.createdBy}`} color="primary" />
          <Chip label={`📅 ${format(new Date(content.createdAt), 'dd.MM.yyyy HH:mm')}`} />
        </Box>
      </Paper>

      {/* Portrait + File Info */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Paper 
            sx={{ 
              height: 400, 
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
              '&:hover': { opacity: 0.9 }
            }}
            onClick={() => setPortraitLightbox(true)}
          >
            <img 
              src={content.imageUrl} 
              alt="Portrait" 
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </Paper>
          <Typography variant="caption" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
            Кликните для просмотра в полный размер
          </Typography>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>📊 Информация о файле</Typography>
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2">📏 Размер: {content.imageWidth}×{content.imageHeight} px</Typography>
              <Typography variant="body2">🏷️ Формат: {content.mimeType}</Typography>
              <Typography variant="body2">📁 Размер: {formatBytes(content.imageSize)}</Typography>
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="h6" gutterBottom>🎯 NFT Маркеры</Typography>
            <Box>
              <Chip 
                label={content.markerStatus === 'ready' ? '✅ Сгенерирован' : '⏳ Генерация'} 
                color={content.markerStatus === 'ready' ? 'success' : 'default'}
                sx={{ mb: 1 }}
              />
              <Typography variant="body2">📁 {content.markerFileName} ({formatBytes(content.markerSize || 0)})</Typography>
              <Typography variant="body2">🔍 {content.markerFeaturePoints?.toLocaleString()} feature points</Typography>
              <Typography variant="body2">⏱️ Генерация: {content.markerGenerationTime}s</Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Links & QR Code Preview */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>🌐 Ссылки и QR-код</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
          <TextField
            fullWidth
            value={arUrl}
            InputProps={{
              readOnly: true,
              endAdornment: (
                <IconButton onClick={() => copyToClipboard(arUrl)}>
                  <CopyIcon />
                </IconButton>
              ),
            }}
          />
          <Button 
            variant="outlined" 
            startIcon={<OpenIcon />}
            onClick={() => window.open(arUrl, '_blank')}
          >
            Открыть
          </Button>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 3, alignItems: 'flex-start' }}>
          <Box>
            <QRCode 
              value={arUrl} 
              size={200}
              ref={(el) => {
                if (el) {
                  const canvas = el.querySelector('canvas');
                  if (canvas && qrCanvasRef.current !== canvas) {
                    // @ts-ignore
                    qrCanvasRef.current = canvas;
                  }
                }
              }}
            />
          </Box>
          <Box>
            <Typography variant="body2" gutterBottom>Скачать QR-код:</Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Button 
                variant="outlined" 
                size="small" 
                startIcon={downloadingQR ? <CircularProgress size={16} /> : <DownloadIcon />}
                onClick={() => handleDownloadQR('png')}
                disabled={downloadingQR}
              >
                PNG
              </Button>
              <Button 
                variant="outlined" 
                size="small" 
                startIcon={downloadingQR ? <CircularProgress size={16} /> : <DownloadIcon />}
                onClick={() => handleDownloadQR('svg')}
                disabled={downloadingQR}
              >
                SVG
              </Button>
              <Button 
                variant="outlined" 
                size="small" 
                startIcon={downloadingQR ? <CircularProgress size={16} /> : <DownloadIcon />}
                onClick={() => handleDownloadQR('pdf')}
                disabled={downloadingQR}
              >
                PDF
              </Button>
            </Box>
          </Box>
        </Box>
      </Paper>

      {/* Videos */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>📹 Видеоанимации ({videos.length} файлов)</Typography>
        
        <Grid container spacing={2}>
          {videos.map((video) => (
            <Grid item xs={12} md={6} key={video.id}>
              <Card>
                <CardMedia
                  component="img"
                  height="140"
                  image={video.previewUrl}
                  alt={video.fileName}
                  sx={{ cursor: 'pointer' }}
                  onClick={() => setVideoLightbox(video)}
                />
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box>
                      <Typography variant="subtitle1">🎥 {video.fileName}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {video.duration}s • {formatBytes(video.fileSize)} • {video.codec}
                      </Typography>
                      {video.isActive && (
                        <Chip label="⭐ Активное сейчас" color="success" size="small" sx={{ mt: 1 }} />
                      )}
                    </Box>
                    <IconButton onClick={() => setVideoLightbox(video)}>
                      <PlayIcon />
                    </IconButton>
                  </Box>
                  
                  {video.scheduleType && video.scheduleType !== 'default' && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        📅 {video.scheduleDate && format(new Date(video.scheduleDate), 'dd MMMM')}
                      </Typography>
                      <Typography variant="caption" display="block" color="text.secondary">
                        🔔 Ежегодно
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h6" gutterBottom>🔄 Расписание ротации</Typography>
        <Box component="ul" sx={{ pl: 2 }}>
          <li>По умолчанию: Простая анимация (3 года)</li>
          <li>25 декабря: Снегопад</li>
          <li>31 декабря: Новогодняя</li>
          <li><strong>Следующая смена: 25 декабря 2025 00:00</strong></li>
        </Box>
      </Paper>

      {/* Statistics */}
      {stats && (
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6" gutterBottom>📊 Статистика просмотров (30 дней)</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="h4">{stats.totalViews.toLocaleString()}</Typography>
                <Typography variant="body2" color="text.secondary">👁️ Всего просмотров</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="h4">{stats.uniqueSessions.toLocaleString()}</Typography>
                <Typography variant="body2" color="text.secondary">👤 Уникальных сессий</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="h4">{stats.avgSessionDuration}s</Typography>
                <Typography variant="body2" color="text.secondary">⏱️ Средняя сессия</Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box>
                <Typography variant="h4">{stats.avgFps}</Typography>
                <Typography variant="body2" color="text.secondary">📈 Средний FPS</Typography>
              </Box>
            </Grid>
          </Grid>

          <Divider sx={{ my: 2 }} />

          <Typography variant="body2" gutterBottom>📱 Устройства:</Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            {stats.deviceBreakdown.map((device) => (
              <Chip 
                key={device.device}
                label={`${device.device} ${device.percentage}%`}
                variant="outlined"
              />
            ))}
          </Box>
        </Paper>
      )}

      {/* Actions */}
      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-start' }}>
        <Button variant="outlined" startIcon={<BackIcon />} onClick={() => navigate(-1)}>
          Назад
        </Button>
        <Button variant="outlined" startIcon={<AnalyticsIcon />}>
          Детальная аналитика
        </Button>
      </Box>

      {/* Portrait Lightbox */}
      <Dialog 
        open={portraitLightbox} 
        onClose={() => setPortraitLightbox(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography>📸 Портрет (оригинал {content.imageWidth}×{content.imageHeight})</Typography>
            <Box>
              <IconButton onClick={() => setZoom(Math.max(50, zoom - 25))}>
                <ZoomOutIcon />
              </IconButton>
              <Typography component="span" sx={{ mx: 1 }}>{zoom}%</Typography>
              <IconButton onClick={() => setZoom(Math.min(200, zoom + 25))}>
                <ZoomInIcon />
              </IconButton>
              <IconButton onClick={() => setPortraitLightbox(false)}>
                <CloseIcon />
              </IconButton>
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ textAlign: 'center', overflow: 'auto' }}>
            <img 
              src={content.imageUrl} 
              alt="Portrait full size"
              style={{ width: `${zoom}%`, maxWidth: 'none' }}
            />
          </Box>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2">📁 Файл: {content.mimeType.split('/')[1]} ({formatBytes(content.imageSize)})</Typography>
            <Typography variant="body2">📏 Размер: {content.imageWidth}×{content.imageHeight} px</Typography>
            <Typography variant="body2">🎯 Качество NFT: {content.markerFeaturePoints} feature points (отлично)</Typography>
          </Box>
          <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
            <Button variant="outlined" startIcon={<DownloadIcon />}>
              Скачать оригинал
            </Button>
            <Button variant="outlined" startIcon={<EditIcon />}>
              Редактировать
            </Button>
          </Box>
        </DialogContent>
      </Dialog>

      {/* Video Lightbox */}
      <Dialog 
        open={!!videoLightbox} 
        onClose={() => setVideoLightbox(null)}
        maxWidth="md"
        fullWidth
      >
        {videoLightbox && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography>▶️ {videoLightbox.fileName} ({videoLightbox.duration} сек)</Typography>
                <IconButton onClick={() => setVideoLightbox(null)}>
                  <CloseIcon />
                </IconButton>
              </Box>
            </DialogTitle>
            <DialogContent>
              <video 
                controls 
                style={{ width: '100%' }}
                src={videoLightbox.videoUrl}
              >
                Your browser does not support video playback.
              </video>
              
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2">📁 {videoLightbox.fileName} ({formatBytes(videoLightbox.fileSize)}, {videoLightbox.codec})</Typography>
                <Typography variant="body2">📏 {videoLightbox.width}×{videoLightbox.height} • {videoLightbox.fps}fps</Typography>
              </Box>
              
              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <Button variant="outlined" startIcon={<DownloadIcon />}>
                  Скачать
                </Button>
              </Box>
            </DialogContent>
          </>
        )}
      </Dialog>

      {/* QR Code Dialog */}
      <Dialog open={qrDialog} onClose={() => setQrDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography>🖨️ QR-код для печати</Typography>
            <IconButton onClick={() => setQrDialog(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ textAlign: 'center', mb: 2 }}>
            <div ref={(el) => {
              if (el) {
                const canvas = el.querySelector('canvas');
                if (canvas && qrCanvasRef.current !== canvas) {
                  // @ts-ignore
                  qrCanvasRef.current = canvas;
                }
              }
            }}>
              <QRCode value={arUrl} size={300} />
            </div>
          </Box>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {arUrl}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button 
              variant="contained" 
              startIcon={downloadingQR ? <CircularProgress size={16} /> : <DownloadIcon />}
              onClick={() => handleDownloadQR('png')}
              disabled={downloadingQR}
            >
              PNG
            </Button>
            <Button 
              variant="outlined" 
              startIcon={downloadingQR ? <CircularProgress size={16} /> : <DownloadIcon />}
              onClick={() => handleDownloadQR('svg')}
              disabled={downloadingQR}
            >
              SVG
            </Button>
            <Button 
              variant="outlined" 
              startIcon={downloadingQR ? <CircularProgress size={16} /> : <DownloadIcon />}
              onClick={() => handleDownloadQR('pdf')}
              disabled={downloadingQR}
            >
              PDF
            </Button>
          </Box>
        </DialogContent>
      </Dialog>
      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog} onClose={() => setDeleteDialog(false)}>
        <DialogTitle>Подтвердите удаление</DialogTitle>
        <DialogContent>
          <Typography>
            Вы уверены, что хотите удалить AR контент "{content.title}"?
            Это действие нельзя отменить.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog(false)} disabled={deleting}>
            Отмена
          </Button>
          <Button 
            onClick={handleDelete} 
            color="error" 
            variant="contained"
            disabled={deleting}
            startIcon={deleting ? <CircularProgress size={16} /> : <DeleteIcon />}
          >
            {deleting ? 'Удаление...' : 'Удалить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
