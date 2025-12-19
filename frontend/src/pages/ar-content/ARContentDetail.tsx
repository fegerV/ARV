import { useState, useEffect, useRef, useCallback } from 'react';
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
import { Upload as UploadIcon, FileUpload as FileUploadIcon } from '@mui/icons-material';

interface ARContentDetailProps {
  id: string;
  order_number: string;
  unique_link?: string;
  public_url?: string;
  company_id: number;
  project_id: number;
  storage_path?: string;
  company_name?: string;
  project_name?: string;
  created_at: string;
  status: string;
  customer_name?: string;
  customer_phone?: string;
  customer_email?: string;
  duration_years: number;
  photo_url?: string;
  thumbnail_url?: string;
  active_video_title?: string | null;
  active_video_url?: string | null;
  views_count: number;
  views_30_days?: number;
  qr_code_url?: string;
  marker_url?: string | null;
  marker_status?: string | null;
  marker_metadata?: Record<string, any> | null;
  videos: VideoResponse[];
  active_video?: VideoResponse | null;
}

interface VideoResponse {
  id: number;
  ar_content_id: number;
  filename: string;
  duration: number | null;
  size: number | null;
  status: string;
  is_active: boolean;
  created_at: string;
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
  const { addToast } = useToast();
  const qrCanvasRef = useRef<HTMLCanvasElement>(null);
  
  const [content, setContent] = useState<ARContentDetailProps | null>(null);
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [generatingMarker, setGeneratingMarker] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [portraitLightbox, setPortraitLightbox] = useState(false);
  const [videoLightbox, setVideoLightbox] = useState<VideoInfo | null>(null);
  const [qrDialog, setQrDialog] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [downloadingQR, setDownloadingQR] = useState(false);
  const [uploadingVideo, setUploadingVideo] = useState(false);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [uploadDialog, setUploadDialog] = useState(false);

  const fetchContentDetail = useCallback(async () => {
    setLoading(true);
    try {
      const response = await arContentAPI.getDetail(String(arContentId));
      const data = response.data;
      setContent(data);
      
      // Convert VideoResponse objects to VideoInfo objects for display
      const convertedVideos: VideoInfo[] = (data.videos || []).map((video: VideoResponse) => ({
        id: video.id,
        fileName: video.filename,
        fileSize: video.size || 0,
        duration: video.duration || 0,
        width: 0, // Will be populated from video metadata if available
        height: 0, // Will be populated from video metadata if available
        fps: 0, // Will be populated from video metadata if available
        codec: '', // Will be populated from video metadata if available
        previewUrl: data.video_url,
        videoUrl: data.video_url,
        isActive: video.is_active,
      }));
      
      setVideos(convertedVideos);
    } catch (error: any) {
      addToast(
        error.response?.data?.message || 'Failed to load AR content',
        'error'
      );
      console.error('Failed to fetch content:', error);
    } finally {
      setLoading(false);
    }
  }, [arContentId, addToast]);

  useEffect(() => {
    fetchContentDetail();
  }, [fetchContentDetail]);

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
      // Use the company_id and project_id from the content object for hierarchical deletion
      if (content && content.company_id && content.project_id) {
        await arContentAPI.deleteByHierarchy(String(content.company_id), String(content.project_id), String(content.id));
      } else {
        // Fallback to flat deletion if company or project IDs are not available
        await arContentAPI.delete(String(content?.id));
      }
      addToast('AR content deleted successfully', 'success');
      navigate('/ar-content'); // Navigate back to the list after deletion
    } catch (error: any) {
      addToast(
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

  const handleGenerateMarker = async () => {
    if (!content) return;
    
    setGeneratingMarker(true);
    try {
      addToast('Marker generation is not wired yet', 'warning');
    } catch (error: any) {
      addToast(
        error.response?.data?.message || 'Failed to start marker generation',
        'error'
      );
      console.error('Failed to generate marker:', error);
    } finally {
      setGeneratingMarker(false);
    }
  };

  const copyToClipboard = (text: string) => {
    if (!text) {
      addToast('Ссылка недоступна', 'error');
      return;
    }
    navigator.clipboard.writeText(text).then(() => {
      addToast('Copied to clipboard!', 'success');
    }).catch(() => {
      addToast('Failed to copy', 'error');
    });
  };

  const handleDownloadQR = async (format: 'png' | 'svg' | 'pdf') => {
    if (!content) return;
    
    setDownloadingQR(true);
    try {
      const canvas = qrCanvasRef.current;
      if (!canvas) {
        addToast('QR code not ready', 'error');
        return;
      }

      const filename = `qr-${content.order_number}.${format}`;
      const arUrl = fullArUrl || '';
      if (!arUrl) {
        addToast('Ссылка недоступна — QR-код нельзя скачать', 'error');
        return;
      }

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

      addToast(`QR code downloaded as ${format.toUpperCase()}`, 'success');
    } catch (error) {
      addToast('Failed to download QR code', 'error');
      console.error('Download error:', error);
    } finally {
      setDownloadingQR(false);
    }
  };

  const handleVideoUpload = async () => {
    if (!content || !videoFile) return;
    
    setUploadingVideo(true);
    try {
      const formData = new FormData();
      formData.append('video', videoFile);
      
      // Use company_id and project_id from the content object
      const companyId = content.company_id;
      const projectId = content.project_id;
      
      if (!companyId || !projectId) {
        addToast('Company or project information missing', 'error');
        return;
      }
      
      await arContentAPI.updateVideo(String(companyId), String(projectId), String(content.id), formData);
      addToast('Video uploaded successfully!', 'success');
      setUploadDialog(false);
      setVideoFile(null);
      // Refresh the content details
      await fetchContentDetail();
    } catch (error: any) {
      addToast(
        error.response?.data?.message || 'Failed to upload video',
        'error'
      );
      console.error('Failed to upload video:', error);
    } finally {
      setUploadingVideo(false);
    }
 };

  const handleVideoFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      // Validate file type
      if (!file.type.startsWith('video/')) {
        addToast('Please select a video file', 'error');
        return;
      }
      setVideoFile(file);
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

  const arUrl = content.public_url || content.unique_link || '';
  // Ensure arUrl is a complete URL, not just a path
  const fullArUrl = arUrl.startsWith('/') ? `${window.location.origin}${arUrl}` : arUrl;
  const hasPortrait = Boolean(content.photo_url);
  
  // AR viewer URL - using unique_link from the response
  const arViewerUrl = content.unique_link ? `/view/${content.unique_link}` : '';

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton onClick={() => navigate(-1)}>
            <BackIcon />
          </IconButton>
          <Typography variant="h4">
            Заказ {content.order_number}
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
          <Chip label={`🏢 ${content.company_name || '—'}`} />
          <Chip label={`📁 ${content.project_name || '—'}`} />
          <Chip label={`📅 ${format(new Date(content.created_at), 'dd.MM.yyyy HH:mm')}`} />
          <Chip label={`⏳ ${content.duration_years}y`} />
        </Box>
      </Paper>

      {/* Portrait + File Info */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Paper 
            sx={{ 
              height: 400, 
              cursor: hasPortrait ? 'pointer' : 'default',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
              ...(hasPortrait ? { '&:hover': { opacity: 0.9 } } : null),
            }}
            onClick={() => {
              if (!hasPortrait) return;
              setPortraitLightbox(true);
            }}
          >
            {hasPortrait ? (
              <img 
                src={content.photo_url || ''} 
                alt="Portrait" 
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <Typography variant="body2" color="text.secondary">
                Портрет не загружен
              </Typography>
            )}
          </Paper>
          <Typography variant="caption" sx={{ mt: 1, display: 'block', textAlign: 'center' }}>
            {hasPortrait ? 'Кликните для просмотра в полный размер' : '—'}
          </Typography>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>👤 Заказчик</Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2">Имя: {content.customer_name || '—'}</Typography>
              <Typography variant="body2">Телефон: {content.customer_phone || '—'}</Typography>
              <Typography variant="body2">Email: {content.customer_email || '—'}</Typography>
            </Box>

            <Divider sx={{ my: 2 }} />

            <Typography variant="h6" gutterBottom>💾 Расположение файлов</Typography>
            <Typography variant="body2">
              {content.storage_path ? content.storage_path : 'Путь не определен'}
            </Typography>

            <Divider sx={{ my: 2 }} />

            <Typography variant="h6" gutterBottom>🎬 Видео</Typography>
            <Typography variant="body2">Активное: {content.active_video?.filename || '—'}</Typography>
            <Button
              variant="outlined"
              startIcon={<UploadIcon />}
              onClick={() => setUploadDialog(true)}
              sx={{ mt: 2 }}
            >
              Загрузить новое видео
            </Button>
          </Paper>
        </Grid>
      </Grid>

      {/* Links & QR Code Preview */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>🌐 Ссылки и QR-код</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
          <TextField
            fullWidth
            value={fullArUrl}
            InputProps={{
              readOnly: true,
              endAdornment: (
                <IconButton onClick={() => copyToClipboard(fullArUrl)} disabled={!fullArUrl}>
                  <CopyIcon />
                </IconButton>
              ),
            }}
          />
          <Button
          variant="outlined"
          startIcon={<OpenIcon />}
          onClick={() => window.open(fullArUrl, '_blank')}
          disabled={!arUrl}
        >
          Открыть
        </Button>
        {arViewerUrl && (
          <Button
            variant="contained"
            startIcon={<PlayIcon />}
            onClick={() => window.open(arViewerUrl, '_blank')}
          >
            AR Просмотр
          </Button>
        )}
      </Box>
      
      <Box sx={{ display: 'flex', gap: 3, alignItems: 'flex-start' }}>
        <Box>
          <div
            ref={(el: any) => {
              if (el) {
                const canvas = el.querySelector('canvas');
                if (canvas && qrCanvasRef.current !== canvas) {
                  // @ts-ignore
                  qrCanvasRef.current = canvas;
                }
              }
            }}
            onClick={() => setQrDialog(true)}
            style={{ cursor: 'pointer' }}
          >
            <QRCode
                value={arUrl}
                size={300}
                includeMargin
              />
          </div>
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

      {/* AR Marker Info */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>🎯 AR Маркер</Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2 }}>
          <Typography variant="body2">
            Статус: {
              content.marker_status === 'pending' ? 'В процессе генерации' :
              content.marker_status === 'ready' ? 'Готов' :
              content.marker_status === 'failed' ? 'Ошибка генерации' :
              'Неизвестен'
            }
          </Typography>
          {content.marker_url && (
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              href={content.marker_url}
              target="_blank"
              download
            >
              Скачать маркер
            </Button>
          )}
          {!content.marker_url && content.marker_status === 'failed' && (
            <Button
              variant="outlined"
              color="warning"
              startIcon={<EditIcon />}
              onClick={handleGenerateMarker}
            >
              Повторить генерацию
            </Button>
          )}
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
            <Typography>📸 Портрет</Typography>
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
              src={content.photo_url || ''} 
              alt="Portrait full size"
              style={{ width: `${zoom}%`, maxWidth: 'none' }}
            />
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
            <div ref={(el: any) => {
              if (el) {
                const canvas = el.querySelector('canvas');
                if (canvas && qrCanvasRef.current !== canvas) {
                  // @ts-ignore
                  qrCanvasRef.current = canvas;
                }
              }
            }}>
              <QRCode value={fullArUrl} size={300} />
            </div>
          </Box>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {fullArUrl}
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
            Вы уверены, что хотите удалить заказ "{content.order_number}"?
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
      
      {/* Video Upload Dialog */}
      <Dialog open={uploadDialog} onClose={() => setUploadDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography>📁 Загрузить новое видео</Typography>
            <IconButton onClick={() => setUploadDialog(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <input
              accept="video/*"
              type="file"
              onChange={handleVideoFileChange}
              style={{ display: 'none' }}
              id="video-upload"
            />
            <label htmlFor="video-upload">
              <Button
                variant="outlined"
                component="span"
                startIcon={<FileUploadIcon />}
                fullWidth
              >
                Выберите видео файл
              </Button>
            </label>
            {videoFile && (
              <Box sx={{ mt: 2, p: 2, border: '1px dashed #ccc', borderRadius: 1 }}>
                <Typography variant="body2">Выбран файл: {videoFile.name}</Typography>
                <Typography variant="body2">Размер: {formatBytes(videoFile.size)}</Typography>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialog(false)} disabled={uploadingVideo}>
            Отмена
          </Button>
          <Button
            onClick={handleVideoUpload}
            variant="contained"
            disabled={!videoFile || uploadingVideo}
            startIcon={uploadingVideo ? <CircularProgress size={16} /> : <UploadIcon />}
          >
            {uploadingVideo ? 'Загрузка...' : 'Загрузить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
