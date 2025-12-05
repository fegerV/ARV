# 📚 Vertex AR Component Library

Полная библиотека переиспользуемых UI компонентов для Admin Panel.

## 🏗️ Layout Components

### AppLayout
**File**: `components/layout/AppLayout.tsx` ✅ Created  
**Purpose**: Главный layout с Sidebar и контентом  
**Props**:
- `children`: ReactNode

**Usage**:
```tsx
<AppLayout>
  <Dashboard />
</AppLayout>
```

---

### PageHeader
**File**: `components/common/PageHeader.tsx` ✅ Created  
**Purpose**: Заголовок страницы с breadcrumbs и actions  
**Props**:
- `title`: string
- `breadcrumbs?`: Breadcrumb[]
- `actions?`: ReactNode
- `description?`: string

**Usage**:
```tsx
<PageHeader
  title="Компании"
  breadcrumbs={[
    { label: 'Главная', href: '/' },
    { label: 'Компании' }
  ]}
  actions={
    <Button startIcon={<AddIcon />}>
      Добавить компанию
    </Button>
  }
  description="Управление клиентскими компаниями"
/>
```

---

### PageSection
**File**: `components/common/PageSection.tsx` ✅ Created  
**Purpose**: Секция страницы (Card с заголовком)  
**Props**:
- `title?`: string
- `children`: ReactNode
- `action?`: ReactNode

**Usage**:
```tsx
<PageSection title="Основная информация">
  <TextField label="Название" />
</PageSection>
```

---

## 📋 Forms Components

### FormCard
**File**: `components/forms/FormCard.tsx` ✅ Created  
**Purpose**: Карточка с формой + кнопки сохранения  
**Props**:
- `title`: string
- `children`: ReactNode
- `onSubmit`: (e: React.FormEvent) => void
- `onCancel`: () => void
- `loading?`: boolean
- `submitLabel?`: string
- `cancelLabel?`: string

**Usage**:
```tsx
<FormCard
  title="Новая компания"
  onSubmit={handleSubmit}
  onCancel={() => navigate(-1)}
  loading={saving}
>
  <TextField label="Название" />
  <TextField label="Email" />
</FormCard>
```

---

### FileUploadZone
**File**: `components/forms/FileUploadZone.tsx` ✅ Created  
**Purpose**: Drag-and-drop загрузка файлов  
**Props**:
- `accept`: string (MIME types)
- `maxSize?`: number (MB, default 10)
- `onFileSelect`: (file: File) => void
- `label?`: string
- `description?`: string

**Features**:
- ✅ Drag-and-drop
- ✅ File size validation
- ✅ Visual feedback
- ✅ Remove file
- ✅ Progress bar

**Usage**:
```tsx
<FileUploadZone
  accept="image/jpeg,image/png"
  maxSize={5}
  onFileSelect={handleImageUpload}
  label="Загрузить портрет"
  description="Поддерживаются JPEG и PNG, макс. 5MB"
/>
```

---

### CompanySelector
**File**: `components/forms/CompanySelector.tsx` 🔨 TODO  
**Purpose**: Autocomplete для выбора компании  
**Props**:
- `value`: Company | null
- `onChange`: (company: Company | null) => void
- `error?`: boolean
- `helperText?`: string

---

### ProjectSelector
**File**: `components/forms/ProjectSelector.tsx` 🔨 TODO  
**Purpose**: Autocomplete для выбора проекта  
**Props**:
- `companyId`: number
- `value`: Project | null
- `onChange`: (project: Project | null) => void

---

### ScheduleEditor
**File**: `components/forms/ScheduleEditor.tsx` 🔨 TODO  
**Purpose**: Редактор правил ротации видео  
**Props**:
- `value`: ScheduleRule[]
- `onChange`: (rules: ScheduleRule[]) => void

**Features**:
- ✅ Default video
- ✅ Date-specific rules
- ✅ Daily cycle
- ✅ Random selection

---

## 📊 Data Display

### KpiCard
**File**: `components/common/KpiCard.tsx` ✅ Created  
**Purpose**: KPI карточка с трендом  
**Props**:
- `title`: string
- `value`: string | number
- `icon?`: ReactNode
- `trend?`: number (% change)
- `loading?`: boolean
- `subtitle?`: string

**Usage**:
```tsx
<KpiCard
  title="Всего просмотров"
  value="3,245"
  icon={<VisibilityIcon />}
  trend={+12.5}
  subtitle="За последние 30 дней"
/>
```

---

### DataTable
**File**: `components/tables/DataTable.tsx` 🔨 TODO  
**Purpose**: Универсальная таблица с сортировкой/пагинацией  
**Props**:
- `columns`: Column[]
- `data`: any[]
- `loading?`: boolean
- `onSort?`: (column: string, direction: 'asc' | 'desc') => void
- `onPageChange?`: (page: number) => void
- `totalPages?`: number

---

### CompaniesTable
**File**: `components/tables/CompaniesTable.tsx` 🔨 TODO  
**Extends**: DataTable  
**Columns**:
- Logo
- Name
- Email
- Projects Count
- Storage Used
- Status
- Actions (Edit, View, Delete)

---

### ARContentTable
**File**: `components/tables/ARContentTable.tsx` 🔨 TODO  
**Extends**: DataTable  
**Columns**:
- Thumbnail
- Title
- Marker Status
- Videos Count
- Views
- Created At
- Actions

---

## 🎨 Media Components

### ImagePreview
**File**: `components/media/ImagePreview.tsx` 🔨 TODO  
**Purpose**: Preview изображения с lightbox  
**Props**:
- `src`: string
- `alt`: string
- `width?`: number
- `height?`: number

---

### VideoPreview
**File**: `components/media/VideoPreview.tsx` 🔨 TODO  
**Purpose**: Preview видео с длительностью  
**Props**:
- `src`: string
- `thumbnail?`: string
- `duration`: number

---

### MediaLightbox
**File**: `components/media/MediaLightbox.tsx` 🔨 TODO  
**Purpose**: Универсальный lightbox для фото/видео  
**Props**:
- `open`: boolean
- `onClose`: () => void
- `type`: 'image' | 'video'
- `src`: string

---

### FileInfoPanel
**File**: `components/media/FileInfoPanel.tsx` 🔨 TODO  
**Purpose**: Информация о файле  
**Props**:
- `file`: FileInfo

**Displays**:
- Format (JPEG, PNG, MP4)
- Size (2.5 MB)
- Resolution (1920x1080)
- Duration (for videos)
- Path

---

## 🔗 AR/QR Components

### QRCodeCard
**File**: `components/ar/QRCodeCard.tsx` 🔨 TODO  
**Purpose**: QR код с actions  
**Features**:
- ✅ QR preview
- ✅ Copy link
- ✅ Open link
- ✅ Download PNG/SVG/PDF
- ✅ Send email

---

### PermanentLinkField
**File**: `components/ar/PermanentLinkField.tsx` 🔨 TODO  
**Purpose**: Постоянная ссылка + copy/open  
**Props**:
- `url`: string
- `label?`: string

---

### MarkerStatusBadge
**File**: `components/ar/MarkerStatusBadge.tsx` 🔨 TODO  
**Purpose**: Статус NFT маркера  
**Props**:
- `status`: 'pending' | 'processing' | 'ready' | 'failed'

**Colors**:
- pending → gray
- processing → blue
- ready → green
- failed → red

---

### MarkerQualityInfo
**File**: `components/ar/MarkerQualityInfo.tsx` 🔨 TODO  
**Purpose**: Информация о качестве маркера  
**Props**:
- `featurePoints`: number
- `generationTime`: number
- `fileSize`: number
- `quality`: 'excellent' | 'good' | 'poor'

---

## 🎯 Navigation

### FilterBar
**File**: `components/navigation/FilterBar.tsx` 🔨 TODO  
**Purpose**: Панель фильтров  
**Props**:
- `filters`: Filter[]
- `onFilterChange`: (filters: FilterState) => void

---

### GlobalSearch
**File**: `components/navigation/GlobalSearch.tsx` 🔨 TODO  
**Purpose**: Глобальный поиск по компаниям/проектам/контенту  
**Features**:
- ✅ Autocomplete
- ✅ Recent searches
- ✅ Keyboard shortcuts (Ctrl+K)

---

### Tabs
**File**: `components/navigation/Tabs.tsx` 🔨 TODO  
**Purpose**: Вкладки внутри страницы  
**Props**:
- `tabs`: Tab[]
- `value`: string
- `onChange`: (value: string) => void

---

## 💬 Feedback Components

### EmptyState
**File**: `components/common/EmptyState.tsx` ✅ Created  
**Purpose**: Красивая заглушка для пустых списков  
**Props**:
- `icon?`: ReactNode
- `title`: string
- `description?`: string
- `actionLabel?`: string
- `onAction?`: () => void

**Usage**:
```tsx
<EmptyState
  icon={<BusinessIcon />}
  title="Нет компаний"
  description="Добавьте первую компанию для начала работы"
  actionLabel="Добавить компанию"
  onAction={() => navigate('/companies/new')}
/>
```

---

### ConfirmDialog
**File**: `components/common/ConfirmDialog.tsx` ✅ Created  
**Purpose**: Диалог подтверждения действия  
**Props**:
- `open`: boolean
- `title`: string
- `message`: string
- `onConfirm`: () => void
- `onCancel`: () => void
- `loading?`: boolean
- `confirmLabel?`: string
- `cancelLabel?`: string
- `severity?`: 'warning' | 'error' | 'info'

**Usage**:
```tsx
<ConfirmDialog
  open={deleteDialog}
  title="Удалить компанию?"
  message="Это действие нельзя отменить. Все проекты и AR контент будут удалены."
  onConfirm={handleDelete}
  onCancel={() => setDeleteDialog(false)}
  severity="error"
/>
```

---

### LoadingState
**File**: `components/common/LoadingState.tsx` 🔨 TODO  
**Purpose**: Fullscreen loader с анимацией  
**Props**:
- `message?`: string

---

### AlertBanner
**File**: `components/common/AlertBanner.tsx` 🔨 TODO  
**Purpose**: Banner вверху страницы  
**Props**:
- `severity`: 'success' | 'error' | 'warning' | 'info'
- `message`: string
- `onClose?`: () => void

---

### ErrorBoundary
**File**: `components/common/ErrorBoundary.tsx` 🔨 TODO  
**Purpose**: React Error Boundary UI  
**Features**:
- ✅ Catch errors
- ✅ Display error message
- ✅ Reload button
- ✅ Report error

---

## 📈 Charts Components

### ViewsChart
**File**: `components/charts/ViewsChart.tsx` 🔨 TODO  
**Purpose**: График просмотров (Line chart)  
**Props**:
- `data`: ViewsData[]
- `loading?`: boolean

**Library**: Recharts

---

### DeviceChart
**File**: `components/charts/DeviceChart.tsx` 🔨 TODO  
**Purpose**: Распределение по устройствам (Pie chart)  
**Props**:
- `data`: DeviceData[]

---

### StorageChart
**File**: `components/charts/StorageChart.tsx` 🔨 TODO  
**Purpose**: Использование хранилища (Bar chart)  
**Props**:
- `data`: StorageData[]

---

## 🔧 System Components

### SystemHealthWidget
**File**: `components/system/SystemHealthWidget.tsx` 🔨 TODO  
**Purpose**: Виджет здоровья системы  
**Displays**:
- PostgreSQL status
- Redis status
- Celery workers
- Queue size

---

### ActivityFeed
**File**: `components/system/ActivityFeed.tsx` 🔨 TODO  
**Purpose**: Лента последних событий  
**Props**:
- `events`: Event[]
- `limit?`: number

---

## 📊 Summary

### Created Components (8/40+)
- ✅ AppLayout
- ✅ PageHeader
- ✅ PageSection
- ✅ FormCard
- ✅ FileUploadZone
- ✅ KpiCard
- ✅ EmptyState
- ✅ ConfirmDialog

### TODO Components (32+)
- 🔨 CompanySelector
- 🔨 ProjectSelector
- 🔨 ScheduleEditor
- 🔨 DataTable
- 🔨 CompaniesTable
- 🔨 ARContentTable
- 🔨 ImagePreview
- 🔨 VideoPreview
- 🔨 MediaLightbox
- 🔨 FileInfoPanel
- 🔨 QRCodeCard
- 🔨 PermanentLinkField
- 🔨 MarkerStatusBadge
- 🔨 MarkerQualityInfo
- 🔨 FilterBar
- 🔨 GlobalSearch
- 🔨 Tabs
- 🔨 LoadingState
- 🔨 AlertBanner
- 🔨 ErrorBoundary
- 🔨 ViewsChart
- 🔨 DeviceChart
- 🔨 StorageChart
- 🔨 SystemHealthWidget
- 🔨 ActivityFeed
- ... and more

---

## 🎨 Design Principles

### 1. Consistent Spacing
- Card padding: `p: 3` (24px)
- Section margin: `mb: 3` (24px)
- Button gap: `gap: 1` (8px)

### 2. Typography
- Page title: `variant="h4"`, `fontWeight={700}`
- Section title: `variant="h6"`
- Body text: `variant="body1"`
- Caption: `variant="caption"`, `color="text.secondary"`

### 3. Colors
- Primary: MUI primary (blue)
- Success: `success.main` (green)
- Error: `error.main` (red)
- Warning: `warning.main` (orange)

### 4. Transitions
- All: `300ms cubic-bezier(0.4, 0, 0.2, 1)`
- Hover effects: `transform: translateY(-2px)`

### 5. Responsive
- Mobile breakpoint: `sm` (600px)
- Tablet: `md` (900px)
- Desktop: `lg` (1200px)

---

## 🚀 Usage Example

```tsx
import AppLayout from './components/layout/AppLayout';
import PageHeader from './components/common/PageHeader';
import PageSection from './components/common/PageSection';
import KpiCard from './components/common/KpiCard';
import FormCard from './components/forms/FormCard';
import FileUploadZone from './components/forms/FileUploadZone';
import EmptyState from './components/common/EmptyState';
import ConfirmDialog from './components/common/ConfirmDialog';

function CompanyDetailsPage() {
  return (
    <AppLayout>
      <PageHeader
        title="Компания XYZ"
        breadcrumbs={[
          { label: 'Главная', href: '/' },
          { label: 'Компании', href: '/companies' },
          { label: 'XYZ' }
        ]}
        actions={
          <>
            <Button variant="outlined">Редактировать</Button>
            <Button variant="contained" color="error">Удалить</Button>
          </>
        }
      />

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <KpiCard
            title="Проекты"
            value="15"
            icon={<FolderIcon />}
            trend={+8}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <KpiCard
            title="AR Контент"
            value="280"
            icon={<ViewInArIcon />}
            trend={+15.3}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <KpiCard
            title="Хранилище"
            value="2.5 GB"
            icon={<StorageIcon />}
          />
        </Grid>
      </Grid>

      <PageSection title="Основная информация">
        <TextField label="Название" value="XYZ" fullWidth />
        <TextField label="Email" value="info@xyz.com" fullWidth sx={{ mt: 2 }} />
      </PageSection>

      <PageSection title="Проекты">
        {projects.length === 0 ? (
          <EmptyState
            icon={<FolderIcon />}
            title="Нет проектов"
            description="Создайте первый проект"
            actionLabel="Добавить проект"
            onAction={() => navigate('/projects/new')}
          />
        ) : (
          <ProjectsTable data={projects} />
        )}
      </PageSection>

      <ConfirmDialog
        open={deleteDialog}
        title="Удалить компанию?"
        message="Все проекты и контент будут удалены"
        onConfirm={handleDelete}
        onCancel={() => setDeleteDialog(false)}
        severity="error"
      />
    </AppLayout>
  );
}
```

---

**🎉 Component Library Foundation Complete!**

✅ 8 core components created  
🔨 32+ specialized components planned  
📚 Comprehensive documentation  
🎨 Consistent design system  
🚀 Production-ready patterns
