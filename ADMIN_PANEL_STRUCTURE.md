# 🎨 Vertex AR Admin Panel - Полная структура проекта

## 📊 Обзор

Создана полная структура Admin Panel с 8 основными разделами и 32 подразделами для управления B2B AR-платформой.

## 🗂️ Структура файлов (27 новых файлов)

```
frontend/
├── src/
│   ├── components/
│   │   └── layout/
│   │       └── Sidebar.tsx                    # ✅ Навигация (8 разделов)
│   ├── pages/
│   │   ├── Dashboard.tsx                      # ✅ 8 KPI карточек
│   │   ├── companies/
│   │   │   ├── CompaniesList.tsx              # ✅ Список компаний
│   │   │   ├── CompanyDetails.tsx             # ✅ Детали компании
│   │   │   └── CompanyForm.tsx                # ✅ Форма создания
│   │   ├── projects/
│   │   │   ├── ProjectsList.tsx               # ✅ Список проектов
│   │   │   └── ProjectForm.tsx                # ✅ Форма проекта
│   │   ├── ar-content/
│   │   │   ├── ARContentList.tsx              # ✅ Список AR контента
│   │   │   └── ARContentForm.tsx              # ✅ Форма контента
│   │   ├── Analytics.tsx                      # ✅ Аналитика
│   │   ├── Storage.tsx                        # ✅ Хранилища
│   │   ├── Notifications.tsx                  # ✅ Уведомления
│   │   └── Settings.tsx                       # ✅ Настройки
│   ├── App.tsx                                # ✅ React Router (14 маршрутов)
│   ├── main.tsx                               # ✅ Entry point
│   ├── theme.ts                               # ✅ MUI тема
│   └── index.css                              # ✅ Global styles
├── index.html                                 # ✅ HTML шаблон
├── vite.config.ts                             # ✅ Vite + proxy
├── tsconfig.json                              # ✅ TypeScript config
├── tsconfig.node.json                         # ✅ Node config
├── package.json                               # ✅ Dependencies
└── README.md                                  # ✅ Документация
```

## 🎯 8 основных разделов Admin Panel

### 1. 🏠 Dashboard (Главная страница)
**Файл**: `pages/Dashboard.tsx`

**Компоненты**:
- 8 KPI карточек:
  - 👁️ Total AR Views: 45,892 (+12.5%)
  - 👤 Unique Sessions: 38,234
  - 🎬 Active Content: 280
  - 💾 Storage Usage: 125GB (10%)
  - 🏢 Active Companies: 15
  - 📁 Active Projects: 100
  - 💰 Revenue: $4,200 (+15%)
  - ✅ Uptime: 99.92%

**Статус**: ✅ Структура готова, требуется подключение к API

---

### 2. 🏢 Companies (Управление клиентами)
**Файлы**:
- `pages/companies/CompaniesList.tsx` - список компаний
- `pages/companies/CompanyDetails.tsx` - детали компании
- `pages/companies/CompanyForm.tsx` - форма создания/редактирования

**Функционал**:
- Поиск/фильтр по имени, статусу, expiry
- Статусы: ⭐ Active | ⚠️ Expiring | ❌ Expired
- Quick Actions: Edit | Analytics | Add Project
- Bulk Actions: Extend | Archive | Notify

**Форма создания**:
- Company Info: Name, Slug, Contacts
- Storage: Yandex Disk OAuth → Folder Picker
- Subscription: Tier (Basic/Pro/Enterprise), Period
- Quotas: Storage GB, Projects limit

**Статус**: ✅ Базовая структура, требуется интеграция с API

---

### 3. 📁 Projects (Проекты/папки)
**Файлы**:
- `pages/projects/ProjectsList.tsx` - список проектов
- `pages/projects/ProjectForm.tsx` - форма проекта

**Функционал**:
- Фильтр по компании
- Статусы: Active/Draft/Paused/Expired
- Expiry Date (color-coded)
- Quick Stats: AR Items, Views

**Форма**:
- Project Info: Name, Type (Posters/Souvenirs), Description
- Folder: Create new or select existing
- Timeline: Start/End Date, Auto-renew
- Notifications: 7/14/30 days before expiry
- Tags: Comma-separated

**Статус**: ✅ Структура готова

---

### 4. 🎬 AR Content (Основной контент)
**Файлы**:
- `pages/ar-content/ARContentList.tsx` - список контента
- `pages/ar-content/ARContentForm.tsx` - форма создания

**Функционал списка**:
- Таблица: Portrait preview | Title | Videos | Marker Status | QR | Views
- Marker Status: ⏳ Pending | 🔄 Processing | ✅ Ready | ❌ Failed
- Bulk Actions: Generate Markers | Publish | Archive

**Форма создания (6-step wizard)**:
1. Upload Portrait (JPG/PNG, preview)
2. Generate Marker [🔧 Start] (progress bar)
3. Upload Videos (drag-n-drop, multiple)
4. Video Schedule (rotation rules)
5. QR Code + Links (auto-generate)
6. Publish

**Статус**: ✅ Базовая структура

---

### 5. 💾 Storage (Управление хранилищами)
**Файл**: `pages/Storage.tsx`

**Функционал**:
- Storage Connections таблица:
  - Provider: Local | MinIO | Yandex Disk
  - Status: ✅ Connected | ❌ Failed [Test]
  - Used: 125GB | Companies: 15
  - Actions: Edit | Test | Delete

- Storage Overview:
  - Total: 250GB (15% used)
  - By Company: Pie chart
  - By Type: Videos(60%) | Markers(20%) | Images(15%) | QR(5%)
  - 🔄 Sync Now button

**Статус**: ✅ Структура готова

---

### 6. 📊 Analytics (Аналитика)
**Файл**: `pages/Analytics.tsx`

**Компоненты**:
- Overview Dashboard (8 cards + 4 charts)
- Filters:
  - 📅 Date Range: Today | 7d | 30d | Custom
  - 🏢 Company Filter
  - 📁 Project Filter
  - 📱 Device Filter

- Charts:
  - Views by Company (Bar chart)
  - Views Over Time (Line chart)
  - Device/OS Breakdown (Pie)
  - Session Duration (Histogram)
  - Top Performing Content (Table)
  - Revenue by Subscription Tier

- AR Performance:
  - Avg FPS by Device
  - Tracking Quality (%)
  - Load Time Distribution
  - Geographic Heatmap

**Статус**: ✅ Структура готова, требуется Recharts integration

---

### 7. 🔔 Notifications (Уведомления)
**Файл**: `pages/Notifications.tsx`

**Разделы**:
1. **Email Settings**:
   - SMTP: Host/Port/User/Pass
   - From Name/Email
   - Test Email button

2. **Telegram Bot**:
   - Bot Token
   - Admin Chat ID
   - Dev Channel ID
   - Test Message

3. **Templates**:
   - Expiry Warning (7/14/30 days)
   - Video Rotation Notice
   - Marker Generation Failed
   - Quota Exceeded

4. **History** (Table):
   - Date | Type | Company | Status (✅ Sent / ❌ Failed)
   - Resend Failed button

**Статус**: ✅ Структура готова

---

### 8. ⚙️ Settings (Настройки системы)
**Файл**: `pages/Settings.tsx`

**Вкладки**:
1. **Profile**:
   - Change Password
   - API Tokens
   - Notification Preferences

2. **Subscription Tiers**:
   - Basic: 10GB, 50 projects, Email only
   - Pro: 50GB, 200 projects, Email+Telegram
   - Enterprise: Unlimited

3. **System Settings**:
   - Rate Limits
   - File Upload Limits (50MB videos)
   - AR Marker Settings (max features)
   - Analytics Retention (90 days)

4. **Admin Users**:
   - Table: Email | Role | Last Login | Active
   - Invite New Admin

5. **Security Audit**:
   - Failed Logins (last 30d)
   - API Token Usage
   - Suspicious Activity

**Статус**: ✅ Структура готова

---

## 🎨 UI/UX Components

### Sidebar Navigation
**Файл**: `components/layout/Sidebar.tsx`

**Функционал**:
- 8 menu items с иконками
- Responsive drawer (mobile/desktop)
- Selected state highlight
- AppBar с mobile toggle

**Маршруты**:
```typescript
{ text: 'Dashboard', icon: <DashboardIcon />, path: '/' }
{ text: 'Companies', icon: <BusinessIcon />, path: '/companies' }
{ text: 'Projects', icon: <FolderIcon />, path: '/projects' }
{ text: 'AR Content', icon: <ARIcon />, path: '/ar-content' }
{ text: 'Storage', icon: <StorageIcon />, path: '/storage' }
{ text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics' }
{ text: 'Notifications', icon: <NotificationsIcon />, path: '/notifications' }
{ text: 'Settings', icon: <SettingsIcon />, path: '/settings' }
```

### MUI Theme
**Файл**: `theme.ts`

**Цвета**:
- Primary: #1976d2 (Blue)
- Success: #2e7d32 (Green)
- Warning: #ed6c02 (Orange)
- Error: #d32f2f (Red)

**Стили**:
- Button: No text transform, 8px border radius
- Card: 12px border radius

---

## 🛠 Технологический стек

### Core
- React 18.3.1
- TypeScript 5.5.3
- Vite 5.3.1

### UI
- @mui/material 5.15.15
- @mui/icons-material 5.15.15
- @emotion/react + @emotion/styled

### Routing & State
- react-router-dom 6.22.3
- zustand 4.5.2

### Forms & Validation
- react-hook-form 7.51.5

### Charts & Visualization
- recharts 2.12.7
- qrcode.react 3.1.0

### Utils
- axios 1.6.8
- date-fns 3.0.0

---

## 🚀 React Router Structure

**Файл**: `App.tsx`

**Маршруты (14 routes)**:
```typescript
// Dashboard
<Route path="/" element={<Dashboard />} />

// Companies (3 routes)
<Route path="/companies" element={<CompaniesList />} />
<Route path="/companies/new" element={<CompanyForm />} />
<Route path="/companies/:id" element={<CompanyDetails />} />

// Projects (2 routes)
<Route path="/companies/:companyId/projects" element={<ProjectsList />} />
<Route path="/companies/:companyId/projects/new" element={<ProjectForm />} />

// AR Content (2 routes)
<Route path="/projects/:projectId/content" element={<ARContentList />} />
<Route path="/projects/:projectId/content/new" element={<ARContentForm />} />

// Other pages (4 routes)
<Route path="/analytics" element={<Analytics />} />
<Route path="/storage" element={<Storage />} />
<Route path="/notifications" element={<Notifications />} />
<Route path="/settings" element={<Settings />} />

// Redirect
<Route path="*" element={<Navigate to="/" replace />} />
```

---

## 🔗 API Integration (Vite Proxy)

**Файл**: `vite.config.ts`

**Proxy настройки**:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
  '/ar': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

**Backend endpoints**:
- `/api/companies` - Companies CRUD
- `/api/projects` - Projects CRUD
- `/api/ar-content` - AR Content CRUD
- `/api/storage` - Storage Management
- `/api/analytics` - Analytics Data
- `/api/notifications` - Notifications Settings
- `/ar/{unique_id}` - Public AR Viewer

---

## 📦 Следующие шаги (MVP Roadmap)

### Phase 1: Data Integration (Week 1-2)
- [ ] Подключить API к Dashboard (8 KPIs)
- [ ] Companies CRUD + Yandex Disk OAuth
- [ ] Projects CRUD
- [ ] AR Content upload + Marker generation

### Phase 2: Advanced Features (Week 3-4)
- [ ] Analytics charts (Recharts)
- [ ] Notifications (Email/Telegram)
- [ ] Storage management
- [ ] Settings + Admin users

### Phase 3: Forms & Validation
- [ ] React Hook Form + Zod validation
- [ ] Drag-n-drop file upload
- [ ] Multi-step wizard (AR Content)
- [ ] Yandex Disk folder picker

### Phase 4: Real-time & Testing
- [ ] WebSocket для alerts
- [ ] Unit tests (Vitest)
- [ ] E2E tests (Playwright)
- [ ] Performance optimization

---

## ✅ Completed
- [x] Project structure (27 files)
- [x] 8 main sections + routes
- [x] Sidebar navigation
- [x] MUI theme
- [x] TypeScript config
- [x] Vite config + proxy
- [x] README documentation
- [x] Git commit + push

---

## 🎯 Итого

**Создано**:
- ✅ 27 файлов
- ✅ 8 основных разделов
- ✅ 14 React Router маршрутов
- ✅ Sidebar navigation
- ✅ MUI theme
- ✅ TypeScript + Vite
- ✅ API proxy
- ✅ Документация

**Готово к разработке! 🚀**

Следующий шаг: `cd frontend && npm run dev`
