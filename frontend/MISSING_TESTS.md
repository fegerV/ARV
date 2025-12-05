# 🎯 Компоненты без тестов - Краткий обзор

## ❌ КРИТИЧНЫЕ (начать немедленно)

### Layout (0% покрытие)
- [ ] `AppLayout.tsx` - основной layout всего приложения
- [ ] `SidebarNav.tsx` - главное меню навигации
- [ ] `TopBar.tsx` - верхняя панель с user menu
- [ ] `PageHeader.tsx` - заголовки страниц
- [ ] `Breadcrumbs.tsx` - навигационные крошки
- [ ] `PageContent.tsx` - контейнер контента

### Auth (0% покрытие)  
- [ ] `ProtectedRoute.tsx` - защита маршрутов
- [ ] `UserMenu.tsx` - меню пользователя + logout

### Forms (0% покрытие)
- [ ] `FileUploadZone.tsx` - загрузка файлов для AR
- [ ] `FormCard.tsx` - обёртка форм

---

## 🟡 ВАЖНЫЕ (следующий этап)

### Pages - Integration тесты (7% покрытие)
- [ ] `Dashboard.tsx` - главная страница
- [ ] `companies/CompaniesList.tsx`
- [ ] `companies/CompanyDetail.tsx`
- [ ] `companies/CompanyForm.tsx`
- [ ] `projects/ProjectsList.tsx`
- [ ] `projects/ProjectForm.tsx`
- [ ] `ar-content/ARContentList.tsx`
- [ ] `ar-content/ARContentDetail.tsx`
- [ ] `ar-content/ARContentForm.tsx`

### Hooks (50% покрытие)
- [x] `useAuthStore` ✅
- [x] `useThemeStore` ✅
- [ ] `useKeyboardShortcuts.ts`
- [ ] `useSystemTheme.ts`

---

## 🟢 ЖЕЛАТЕЛЬНЫЕ (можно отложить)

### UI Components (13% покрытие)
- [ ] `Badge/StatusBadge.tsx`
- [ ] `Button/PrimaryButton.tsx`
- [ ] `Card/InfoCard.tsx`
- [ ] `EmptyState/EmptyState.tsx`
- [ ] `Loading/LoadingSpinner.tsx`

### Utils/Services (0% покрытие)
- [ ] `api.ts` - HTTP клиент
- [ ] `cn.ts` - className utility
- [ ] `qrCodeExport.ts` - экспорт QR

### Остальные Pages
- [ ] `Analytics.tsx`
- [ ] `Settings.tsx`
- [ ] `Storage.tsx`
- [ ] `Notifications.tsx`

---

## 📊 Статистика

**Протестировано**: 9 компонентов/модулей  
**Не протестировано**: ~45 компонентов/модулей  
**Покрытие**: ~15-20%  
**Цель**: 90%+

---

## 🚀 Быстрый старт

### Создать сейчас (приоритет 1):

```bash
# 1. Layout тесты
frontend/tests/unit/components/(layout)/AppLayout.test.tsx
frontend/tests/unit/components/(layout)/SidebarNav.test.tsx
frontend/tests/unit/components/(layout)/TopBar.test.tsx

# 2. Auth тесты  
frontend/tests/unit/components/(auth)/ProtectedRoute.test.tsx
frontend/tests/unit/components/(auth)/UserMenu.test.tsx

# 3. Forms тесты
frontend/tests/unit/components/(forms)/FileUploadZone.test.tsx
frontend/tests/unit/components/(forms)/FormCard.test.tsx
```

Ожидаемый результат: +35-40 тестов, покрытие ~40%

---

**Детальный анализ**: см. `TESTING_COVERAGE_GAP_ANALYSIS.md`
