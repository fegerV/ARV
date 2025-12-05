# Структура компонентов Vertex AR Admin Panel

Production-ready структура компонентов с TypeScript и организацией по категориям.

## 📁 Общая структура

```
src/components/
├── (layout)/           # Макеты страниц
├── (ui)/               # Базовые UI-примитивы
├── (forms)/            # Формы и поля ввода
├── (data)/             # Таблицы, списки (TODO)
├── (media)/            # Изображения, видео, QR (TODO)
├── (analytics)/        # Графики, метрики
├── (feedback)/         # Уведомления, диалоги
├── (auth)/             # Авторизация
├── (system)/           # Системные виджеты (TODO)
├── icons/              # SVG иконки (TODO)
└── index.ts            # Barrel exports
```

## ✅ Реализованные компоненты (25)

### 1. Layout Components (6)

#### `AppLayout`
Главный layout приложения с адаптивным сайдбаром.

```tsx
import { AppLayout } from '@/components';

<AppLayout>
  {/* Ваш контент */}
</AppLayout>
```

#### `TopBar`
Верхняя панель с меню пользователя и уведомлениями.

#### `SidebarNav`
Навигация с иконками и вложенными элементами.

#### `PageHeader`
Заголовок страницы с breadcrumbs и действиями.

```tsx
<PageHeader
  title="Компании"
  subtitle="Управление клиентскими агентствами"
  icon={<Business />}
  breadcrumbs={[{ label: 'Компании', href: '/companies' }]}
  actions={<Button>Создать</Button>}
/>
```

#### `PageContent`
Контентная область с отступами.

#### `Breadcrumbs`
Хлебные крошки для навигации.

---

### 2. UI Primitives (8)

#### `Button`
Кнопка с вариантами стилей и loading состоянием.

```tsx
<Button 
  variant="primary" 
  loading={isLoading}
  startIcon={<Save />}
>
  Сохранить
</Button>
```

**Варианты:** `primary | secondary | danger | ghost`

#### `Card`
Карточка с заголовком и действиями.

```tsx
<Card 
  title="Заголовок"
  subtitle="Подзаголовок"
  actions={<Button>Действие</Button>}
>
  Контент
</Card>
```

#### `StatusBadge`
Badge для статусов AR контента.

```tsx
<StatusBadge status="ready" />
<StatusBadge status="processing" />
```

**Статусы:** `pending | processing | ready | failed | active | expired`

#### `PageSpinner`, `ListSkeleton`, `ButtonSpinner`
Индикаторы загрузки.

```tsx
<PageSpinner />
<ListSkeleton count={5} />
```

#### `EmptyState`
Пустое состояние с иконкой и действием.

```tsx
<EmptyState
  icon={<Business />}
  title="Нет компаний"
  description="Создайте первую компанию"
  actionLabel="Создать"
  onAction={() => {}}
/>
```

---

### 3. Forms (2)

#### `FormCard`
Карточка с формой и кнопками.

```tsx
<FormCard
  title="Создать компанию"
  onSubmit={handleSubmit}
  onCancel={handleCancel}
  loading={isSubmitting}
>
  <TextField label="Название" />
</FormCard>
```

#### `FileUploadZone`
Drag-n-drop загрузка файлов.

```tsx
<FileUploadZone
  accept="image/*"
  maxSize={10}
  onFileSelect={handleFile}
  label="Загрузить портрет"
/>
```

---

### 4. Feedback (1)

#### `ConfirmDialog`
Диалог подтверждения действия.

```tsx
<ConfirmDialog
  open={isOpen}
  title="Удалить компанию?"
  message="Действие необратимо"
  variant="danger"
  onConfirm={handleDelete}
  onCancel={handleCancel}
/>
```

**Варианты:** `danger | warning | info`

---

### 5. Analytics (1)

#### `KpiCard`
Карточка метрики с трендом.

```tsx
<KpiCard
  title="Всего просмотров"
  value="12,345"
  icon={<ViewInAr />}
  trend={{ value: 12, direction: 'up' }}
/>
```

---

### 6. Auth (2)

#### `ProtectedRoute`
Защищенный роут.

```tsx
<Route 
  path="/companies" 
  element={
    <ProtectedRoute>
      <CompaniesPage />
    </ProtectedRoute>
  } 
/>
```

#### `UserMenu`
Меню пользователя.

---

## 🔧 Использование

### Импорт компонентов

```tsx
// Все компоненты доступны через главный index
import { 
  AppLayout, 
  PageHeader, 
  Button, 
  Card, 
  FormCard,
  ConfirmDialog,
  KpiCard 
} from '@/components';
```

### Типы

```tsx
import type { 
  ButtonProps, 
  CardProps, 
  PageHeaderProps 
} from '@/types/components';
```

---

## 📦 Зависимости

```json
{
  "@mui/material": "^5.15.15",
  "@mui/icons-material": "^5.15.15",
  "lucide-react": "^0.294.0",
  "clsx": "^2.1.1",
  "tailwind-merge": "^2.2.2"
}
```

---

## 🚀 Следующие шаги (TODO)

### Data Components
- `DataTable` - универсальная таблица
- `CompaniesTable`, `ProjectsTable`, `ARContentTable`
- `ActivityFeed` - лента событий

### Media Components
- `ImagePreview`, `VideoPreview`
- `QRCodeCard` - QR с экспортом
- `MarkerInfo` - информация о NFT маркере

### System Widgets
- `HealthStatus` - статус сервисов
- `BackupStatus` - статус бэкапов
- `GlobalSearch` - поиск

### Icons
- SVG иконки проекта
- Обертка lucide-react

---

## 📝 Соглашения по коду

### Именование
- Компоненты: `PascalCase`
- Файлы: `PascalCase.tsx`
- Папки: `(category)` для группировки

### Экспорт
- Named exports: `export const Button`
- Barrel exports: `index.ts` в каждой папке

### TypeScript
- 100% типизация
- Интерфейсы в `types/components.ts`
- Props с комментариями

### Стили
- MUI `sx` prop
- Tailwind CSS для утилит
- `cn()` для объединения классов

---

## ✨ Готово к использованию!

**Всего создано:** 25 компонентов  
**Покрытие:** Layout + UI + Forms + Feedback + Analytics + Auth  
**Готовность:** 30% от полной библиотеки (85 компонентов)

Следующий этап: Создание страниц с использованием новых компонентов! 🚀
