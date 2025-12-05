# Vertex AR Admin Panel

Полная структура Admin Panel для B2B AR-платформы.

## 📁 Структура проекта

```
frontend/
├── src/
│   ├── components/
│   │   └── layout/
│   │       └── Sidebar.tsx          # Главная навигация (8 разделов)
│   ├── pages/
│   │   ├── Dashboard.tsx             # 🏠 Dashboard (8 KPI cards)
│   │   ├── companies/
│   │   │   ├── CompaniesList.tsx     # 🏢 Companies List
│   │   │   ├── CompanyDetails.tsx    # 👁️ Company Details
│   │   │   └── CompanyForm.tsx       # ➕ New Company Form
│   │   ├── projects/
│   │   │   ├── ProjectsList.tsx      # 📁 Projects List
│   │   │   └── ProjectForm.tsx       # ➕ New Project Form
│   │   ├── ar-content/
│   │   │   ├── ARContentList.tsx     # 🎬 AR Content List
│   │   │   └── ARContentForm.tsx     # ➕ New AR Content Form
│   │   ├── Analytics.tsx             # 📊 Analytics Dashboard
│   │   ├── Storage.tsx               # 💾 Storage Management
│   │   ├── Notifications.tsx         # 🔔 Notifications Settings
│   │   └── Settings.tsx              # ⚙️ System Settings
│   ├── App.tsx                       # Router setup
│   ├── main.tsx                      # Entry point
│   ├── theme.ts                      # MUI theme
│   └── index.css                     # Global styles
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

## 🎯 8 основных разделов

### 1. 🏠 Dashboard
- 8 KPI карточек (Views, Sessions, Content, Storage, Companies, Projects, Revenue, Uptime)
- Charts: Views over time, Top companies, Device breakdown
- Alerts: Expiring companies, Queue backlog, Marker failures
- Recent activity feed

### 2. 🏢 Companies
- **CompaniesList**: Поиск/фильтр, статусы (Active/Expiring/Expired), bulk actions
- **CompanyForm**: Name, contacts, Yandex Disk OAuth, subscription tier, quotas
- **CompanyDetails**: Overview, projects list, analytics, storage usage

### 3. 📁 Projects
- **ProjectsList**: Фильтр по компании, статусы, expiry date
- **ProjectForm**: Name, type, folder, timeline, notifications, tags

### 4. 🎬 AR Content
- **ARContentList**: Фильтр по company/project/status, marker status, bulk actions
- **ARContentForm**: 6-step wizard (Portrait → Marker → Videos → Schedule → QR → Publish)

### 5. 💾 Storage
- Storage connections: Local/MinIO/Yandex Disk
- Test connection status
- Storage overview by company/type
- Sync now button

### 6. 📊 Analytics
- Filters: Date range, company, project, device
- Charts: Views by company, over time, device breakdown, session duration
- AR performance metrics (FPS, tracking quality, load time)
- Geographic heatmap

### 7. 🔔 Notifications
- Email settings (SMTP config)
- Telegram bot (token, chat ID)
- Templates (expiry warning, video rotation, marker failed)
- Notification history

### 8. ⚙️ Settings
- Profile (password, API tokens)
- Subscription tiers (Basic/Pro/Enterprise)
- System settings (rate limits, file upload limits)
- Admin users management
- Security audit

## 🚀 Запуск проекта

### Установка зависимостей
```bash
npm install
```

### Разработка
```bash
npm run dev
```

### Сборка
```bash
npm run build
```

### Preview
```bash
npm run preview
```

## 🛠 Технологический стек

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite 5
- **UI Library**: MUI 5 (Material-UI)
- **Routing**: React Router DOM 6
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Forms**: React Hook Form
- **Charts**: Recharts
- **QR Codes**: qrcode.react
- **Date**: date-fns

## 🎨 UI/UX принципы

### Цветовая схема
- 🟢 Green: Active/Healthy (✅ Ready, ⭐ Active)
- 🟡 Yellow: Warning/Expiring (⚠️ 7 days, 🟡 Slow)
- 🔴 Red: Error/Critical (❌ Failed, 🚫 Expired)

### Иконки
- 🏢 Companies
- 📁 Projects
- 🎬 AR Content
- 💾 Storage
- 👁️ Views
- 📊 Analytics
- 🔔 Notifications
- ⚙️ Settings

### Progressive Disclosure
- **Level 1**: Cards + Lists (80% пользователей)
- **Level 2**: Tables + Filters (15% пользователей)
- **Level 3**: Charts + Analytics (5% power users)

### Responsive Design
- **Mobile**: Cards only
- **Tablet**: List view (compact)
- **Desktop**: Full tables + charts

## 🔗 API Integration

Backend API работает на `http://localhost:8000` (прокси настроен в vite.config.ts):

- `/api/companies` - Companies CRUD
- `/api/projects` - Projects CRUD
- `/api/ar-content` - AR Content CRUD
- `/api/storage` - Storage Management
- `/api/analytics` - Analytics Data
- `/api/notifications` - Notifications Settings
- `/ar/{unique_id}` - Public AR Viewer

## 📦 Следующие шаги

1. Заполнить компоненты реальными данными из API
2. Добавить формы с валидацией (React Hook Form + Zod)
3. Реализовать Charts (Recharts)
4. Добавить Yandex Disk OAuth flow
5. Интегрировать WebSocket для real-time alerts
6. Добавить Unit/E2E тесты (Vitest + Playwright)

## 🎯 MVP Roadmap

**Phase 1 (Week 1-2)**: Core features
- ✅ Dashboard (4 KPIs)
- ✅ Companies CRUD + Storage
- ✅ Projects CRUD
- ✅ AR Content (Upload + Marker)

**Phase 2 (Week 3-4)**: Advanced features
- Analytics dashboard
- Notifications (Email/Telegram)
- Storage management
- Settings + Admin users

---

**Готово к разработке! 🚀**
