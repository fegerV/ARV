# 🔌 API Integration & Advanced Features

Полная интеграция с backend API, экспорт QR-кодов в PDF/SVG, loading states и error handling.

## 📦 Добавленные файлы

### 1. API Service (`src/services/api.ts`)
Централизованный HTTP client с axios:

**Функции**:
- ✅ Request/Response interceptors
- ✅ Auto auth token injection
- ✅ 401 redirect to login
- ✅ 10s timeout
- ✅ Typed API methods

**API endpoints**:
```typescript
arContentAPI.getDetail(id)     // GET /api/ar-content/:id
arContentAPI.update(id, data)  // PUT /api/ar-content/:id
arContentAPI.delete(id)        // DELETE /api/ar-content/:id

companiesAPI.list()           // GET /api/companies
projectsAPI.list(companyId)   // GET /api/companies/:id/projects
analyticsAPI.arContent(id, days) // GET /api/analytics/ar-content/:id
```

---

### 2. Toast Store (`src/store/useToast.ts`)
Zustand store для global toast notifications:

**State**:
```typescript
{
  open: boolean;
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
}
```

**Methods**:
```typescript
showToast(message, severity)  // Показать toast
hideToast()                   // Скрыть toast
```

**Usage**:
```typescript
const { showToast } = useToast();
showToast('Success!', 'success');
showToast('Error occurred', 'error');
```

---

### 3. Toast Component (`src/components/common/ToastNotification.tsx`)
MUI Snackbar + Alert:

**Features**:
- ✅ Auto-hide через 6 секунд
- ✅ Позиция: top-right
- ✅ 4 severity levels (success/error/warning/info)
- ✅ Manual close button

---

### 4. QR Export Utils (`src/utils/qrCodeExport.ts`)
Экспорт QR-кодов в 3 форматах:

#### PNG Export
```typescript
downloadQRAsPNG(canvasElement, 'qr-abc123.png')
```
- Canvas → PNG data URL → download

#### SVG Export
```typescript
await downloadQRAsSVG(arUrl, 'qr-abc123.svg')
```
- Uses `qrcode` library
- Vector format
- 300x300px

#### PDF Export
```typescript
await downloadQRAsPDF(canvasElement, 'qr-abc123.pdf', arUrl)
```
- Uses `jspdf` library
- A4 portrait format
- Title: "Vertex AR QR Code"
- QR size: 80mm centered
- URL + instructions below QR

---

## 🔄 ARContentDetail Updates

### API Integration

#### Loading State
```typescript
const [loading, setLoading] = useState(true);

if (loading) {
  return <Skeleton />;  // MUI Skeleton loaders
}
```

**Skeleton structure**:
- Header (60px)
- Info bar (100px)
- Portrait grid (2x 400px)

#### Fetch Data
```typescript
const fetchContentDetail = async () => {
  setLoading(true);
  try {
    const response = await arContentAPI.getDetail(Number(arContentId));
    setContent(response.data.arContent);
    setVideos(response.data.videos);
    setStats(response.data.stats);
    setCompany(response.data.company);
    setProject(response.data.project);
    showToast('Content loaded successfully', 'success');
  } catch (error) {
    showToast('Failed to load AR content', 'error');
  } finally {
    setLoading(false);
  }
};
```

---

### Delete Action

#### State
```typescript
const [deleting, setDeleting] = useState(false);
const [deleteDialog, setDeleteDialog] = useState(false);
```

#### Handler
```typescript
const handleDelete = async () => {
  setDeleting(true);
  try {
    await arContentAPI.delete(Number(arContentId));
    showToast('AR content deleted successfully', 'success');
    navigate(-1);  // Back to list
  } catch (error) {
    showToast('Failed to delete AR content', 'error');
  } finally {
    setDeleting(false);
    setDeleteDialog(false);
  }
};
```

#### Dialog
```jsx
<Dialog open={deleteDialog} onClose={() => setDeleteDialog(false)}>
  <DialogTitle>Подтвердите удаление</DialogTitle>
  <DialogContent>
    <Typography>
      Вы уверены, что хотите удалить AR контент "{content.title}"?
      Это действие нельзя отменить.
    </Typography>
  </DialogContent>
  <DialogActions>
    <Button onClick={() => setDeleteDialog(false)}>Отмена</Button>
    <Button 
      onClick={handleDelete} 
      color="error"
      disabled={deleting}
      startIcon={deleting ? <CircularProgress size={16} /> : <DeleteIcon />}
    >
      {deleting ? 'Удаление...' : 'Удалить'}
    </Button>
  </DialogActions>
</Dialog>
```

---

### Edit Action

```typescript
const handleEdit = () => {
  navigate(`/ar-content/${arContentId}/edit`);
};
```

---

### Clipboard Copy

```typescript
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard!', 'success');
  }).catch(() => {
    showToast('Failed to copy', 'error');
  });
};
```

---

### QR Code Export

#### State
```typescript
const [downloadingQR, setDownloadingQR] = useState(false);
const qrCanvasRef = useRef<HTMLCanvasElement>(null);
```

#### Handler
```typescript
const handleDownloadQR = async (format: 'png' | 'svg' | 'pdf') => {
  setDownloadingQR(true);
  try {
    const canvas = qrCanvasRef.current;
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
  } finally {
    setDownloadingQR(false);
  }
};
```

#### Canvas Ref Binding
```jsx
<QRCode 
  value={arUrl} 
  size={200}
  ref={(el) => {
    if (el) {
      const canvas = el.querySelector('canvas');
      if (canvas) {
        qrCanvasRef.current = canvas;
      }
    }
  }}
/>
```

#### Download Buttons
```jsx
<Button 
  variant="outlined" 
  size="small" 
  startIcon={downloadingQR ? <CircularProgress size={16} /> : <DownloadIcon />}
  onClick={() => handleDownloadQR('png')}
  disabled={downloadingQR}
>
  PNG
</Button>
<!-- SVG, PDF аналогично -->
```

---

## 📱 Backend API Contract

### GET /api/ar-content/:id

**Response**:
```json
{
  "arContent": {
    "id": 456,
    "title": "Постер #1 - Санта с подарками",
    "uniqueId": "abc123",
    "imageUrl": "/api/portraits/santa-poster.jpg",
    "imageWidth": 1920,
    "imageHeight": 1080,
    "imageSize": 2621440,
    "mimeType": "image/jpeg",
    "markerStatus": "ready",
    "markerFileName": "targets.mind",
    "markerSize": 251658,
    "markerFeaturePoints": 1247,
    "markerGenerationTime": 8.2,
    "createdAt": "2025-12-05T14:30:00",
    "createdBy": "admin@vertexar.com"
  },
  "company": {
    "id": 1,
    "name": "Рекламное агентство 1"
  },
  "project": {
    "id": 10,
    "name": "Новогодние постеры 2025"
  },
  "videos": [
    {
      "id": 1,
      "fileName": "santa-animation.mp4",
      "fileSize": 12582912,
      "duration": 15,
      "width": 1920,
      "height": 1080,
      "fps": 30,
      "codec": "H.264",
      "previewUrl": "/api/videos/preview-1.jpg",
      "videoUrl": "/api/videos/santa-animation.mp4",
      "isActive": true,
      "scheduleType": "default"
    }
  ],
  "stats": {
    "totalViews": 3245,
    "uniqueSessions": 2890,
    "avgSessionDuration": 28,
    "avgFps": 26.4,
    "deviceBreakdown": [
      { "device": "Android", "percentage": 72 },
      { "device": "iOS", "percentage": 25 },
      { "device": "Другое", "percentage": 3 }
    ]
  }
}
```

### DELETE /api/ar-content/:id

**Response**:
```json
{
  "status": "deleted",
  "message": "AR content deleted successfully"
}
```

**Error (404)**:
```json
{
  "error": {
    "code": 404,
    "message": "AR content not found"
  }
}
```

---

## 🎨 UI/UX Improvements

### Loading States
- ✅ Skeleton loaders (MUI)
- ✅ CircularProgress в кнопках
- ✅ Disabled state во время операций

### Error Handling
- ✅ Toast notifications для всех ошибок
- ✅ Try-catch для всех async операций
- ✅ Fallback messages

### Confirmations
- ✅ Delete confirmation dialog
- ✅ Cannot undo warning
- ✅ Loading state в кнопке удаления

### Feedback
- ✅ Success toast после загрузки
- ✅ Success toast после копирования
- ✅ Success toast после скачивания QR
- ✅ Error toast при неудачных операциях

---

## 📦 Dependencies Added

```json
{
  "qrcode": "^1.5.3",        // SVG generation
  "jspdf": "^2.5.1"          // PDF generation
}
```

**Already installed**:
- `zustand` - state management
- `axios` - HTTP client
- `qrcode.react` - React QR component
- `date-fns` - date formatting

---

## 🚀 Usage Examples

### Show Toast
```typescript
import { useToast } from '../../store/useToast';

const { showToast } = useToast();

// Success
showToast('Operation completed!', 'success');

// Error
showToast('Something went wrong', 'error');

// Warning
showToast('Please check your input', 'warning');

// Info
showToast('Loading data...', 'info');
```

### API Calls
```typescript
import { arContentAPI } from '../../services/api';

// Get detail
const response = await arContentAPI.getDetail(456);

// Delete
await arContentAPI.delete(456);

// Update (будет реализовано в edit form)
await arContentAPI.update(456, { title: 'New Title' });
```

### Download QR
```typescript
import { downloadQRAsPNG, downloadQRAsSVG, downloadQRAsPDF } from '../../utils/qrCodeExport';

const canvas = document.querySelector('canvas');
const url = 'https://ar.vertexar.com/view/abc123';

// PNG
downloadQRAsPNG(canvas, 'qr-code.png');

// SVG
await downloadQRAsSVG(url, 'qr-code.svg');

// PDF
await downloadQRAsPDF(canvas, 'qr-code.pdf', url);
```

---

## ✅ Completed Features

- [x] API service с axios interceptors
- [x] Zustand toast store
- [x] Toast notification component
- [x] QR export utils (PNG/SVG/PDF)
- [x] Loading states (Skeleton + CircularProgress)
- [x] Error handling (try-catch + toasts)
- [x] Delete action с confirmation
- [x] Edit action (navigation)
- [x] Clipboard copy с feedback
- [x] QR canvas ref management
- [x] Disabled states во время операций
- [x] Success/Error messages

---

## 🔄 Next Steps

1. **Backend Integration**:
   - [ ] Реализовать `GET /api/ar-content/:id`
   - [ ] Реализовать `DELETE /api/ar-content/:id`
   - [ ] Добавить auth middleware

2. **Edit Form**:
   - [ ] Создать `ARContentEdit.tsx`
   - [ ] Форма редактирования title/description
   - [ ] Upload new videos
   - [ ] Update rotation schedule

3. **Real-time Updates**:
   - [ ] WebSocket для live stats
   - [ ] Auto-refresh views count
   - [ ] Marker generation progress

4. **Additional Features**:
   - [ ] Email QR code
   - [ ] Print QR code
   - [ ] Batch QR download (multiple AR content)

---

**API интеграция и advanced features готовы! 🚀**
