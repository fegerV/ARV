# Примеры использования компонентов

Практические примеры интеграции новых компонентов.

## 🎯 Пример 1: Простая страница

```tsx
import { 
  PageHeader, 
  PageContent, 
  Button, 
  Card 
} from '@/components';
import { Plus } from 'lucide-react';

export const CompaniesPage = () => {
  return (
    <>
      <PageContent>
        <PageHeader
          title="Компании"
          subtitle="Управление клиентскими агентствами"
          breadcrumbs={[{ label: 'Компании' }]}
          actions={
            <Button variant="primary" startIcon={<Plus size={20} />}>
              Создать компанию
            </Button>
          }
        />

        <Card title="Список компаний">
          {/* Контент */}
        </Card>
      </PageContent>
    </>
  );
};
```

## 🎯 Пример 2: Страница с формой

```tsx
import { 
  PageHeader, 
  PageContent, 
  FormCard, 
  FileUploadZone 
} from '@/components';
import { TextField, Grid } from '@mui/material';

export const CreateCompanyPage = () => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Логика сохранения
  };

  return (
    <PageContent maxWidth="md">
      <PageHeader
        title="Новая компания"
        breadcrumbs={[
          { label: 'Компании', href: '/companies' },
          { label: 'Создать' }
        ]}
      />

      <FormCard
        title="Информация о компании"
        onSubmit={handleSubmit}
        onCancel={() => navigate(-1)}
      >
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <TextField label="Название" fullWidth required />
          </Grid>
          <Grid item xs={12}>
            <TextField label="Email" type="email" fullWidth />
          </Grid>
        </Grid>
      </FormCard>
    </PageContent>
  );
};
```

## 🎯 Пример 3: Dashboard с метриками

```tsx
import { 
  PageContent, 
  PageHeader, 
  KpiCard 
} from '@/components';
import { Grid } from '@mui/material';
import { Eye, Users, FolderOpen, ViewInAr } from 'lucide-react';

export const Dashboard = () => {
  return (
    <PageContent>
      <PageHeader
        title="Dashboard"
        subtitle="Обзор системы"
      />

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Всего просмотров"
            value="45,892"
            icon={<Eye size={24} />}
            trend={{ value: 12.5, direction: 'up' }}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Компаний"
            value="24"
            icon={<Users size={24} />}
            trend={{ value: 3, direction: 'up' }}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Проектов"
            value="156"
            icon={<FolderOpen size={24} />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="AR Контента"
            value="342"
            icon={<ViewInAr size={24} />}
            trend={{ value: 8.2, direction: 'up' }}
          />
        </Grid>
      </Grid>
    </PageContent>
  );
};
```

## 🎯 Пример 4: Диалог подтверждения

```tsx
import { useState } from 'react';
import { Button, ConfirmDialog } from '@/components';
import { Trash2 } from 'lucide-react';

export const CompanyActions = ({ companyId }: { companyId: number }) => {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.delete(`/companies/${companyId}`);
      // Успех
    } catch (error) {
      // Ошибка
    } finally {
      setIsDeleting(false);
      setConfirmOpen(false);
    }
  };

  return (
    <>
      <Button 
        variant="danger" 
        startIcon={<Trash2 size={20} />}
        onClick={() => setConfirmOpen(true)}
      >
        Удалить
      </Button>

      <ConfirmDialog
        open={confirmOpen}
        title="Удалить компанию?"
        message="Все проекты и AR контент будут удалены. Действие необратимо."
        variant="danger"
        confirmLabel="Удалить"
        onConfirm={handleDelete}
        onCancel={() => setConfirmOpen(false)}
        loading={isDeleting}
      />
    </>
  );
};
```

## 🎯 Пример 5: Полный layout

```tsx
import { AppLayout, ProtectedRoute } from '@/components';
import { Route, Routes } from 'react-router-dom';

export const App = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/companies" element={<CompaniesPage />} />
                <Route path="/projects" element={<ProjectsPage />} />
                {/* ... */}
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};
```

## 🎯 Пример 6: EmptyState

```tsx
import { EmptyState } from '@/components';
import { Building2 } from 'lucide-react';

export const CompaniesList = ({ companies }: { companies: Company[] }) => {
  if (companies.length === 0) {
    return (
      <EmptyState
        icon={<Building2 size={64} />}
        title="Нет компаний"
        description="Создайте первую компанию для начала работы"
        actionLabel="Создать компанию"
        onAction={() => navigate('/companies/create')}
      />
    );
  }

  return (
    <div>
      {/* Список компаний */}
    </div>
  );
};
```

## 🎯 Пример 7: StatusBadge

```tsx
import { StatusBadge } from '@/components';

export const ARContentRow = ({ content }: { content: ARContent }) => {
  return (
    <TableRow>
      <TableCell>{content.name}</TableCell>
      <TableCell>
        <StatusBadge status={content.marker_status} />
      </TableCell>
    </TableRow>
  );
};
```

---

## 📝 Миграция старых компонентов

### До (старая структура)
```tsx
import PageHeader from '@/components/common/PageHeader';
import FormCard from '@/components/forms/FormCard';
import EmptyState from '@/components/common/EmptyState';
```

### После (новая структура)
```tsx
import { PageHeader, FormCard, EmptyState } from '@/components';
```

**Преимущества:**
- ✅ Единая точка импорта
- ✅ TypeScript автодополнение
- ✅ Tree-shaking оптимизация
- ✅ Консистентный код

---

## 🚀 Best Practices

### 1. Используйте именованные импорты
```tsx
// ✅ Хорошо
import { Button, Card } from '@/components';

// ❌ Плохо
import * as Components from '@/components';
```

### 2. Передавайте типы
```tsx
import type { ButtonProps } from '@/types/components';

const MyButton = (props: ButtonProps) => {
  return <Button {...props} />;
};
```

### 3. Используйте composition
```tsx
<Card title="Компании">
  <EmptyState
    title="Нет данных"
    actionLabel="Создать"
  />
</Card>
```

### 4. Loading состояния
```tsx
<KpiCard loading={isLoading} />
<Button loading={isSaving}>Сохранить</Button>
```

---

Готово к использованию! 🎉
