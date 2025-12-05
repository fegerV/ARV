# 🎯 Быстрый старт: Frontend Testing

## ✅ Установка завершена!

Все зависимости для тестирования установлены. Можно начинать!

---

## 🚀 Первый запуск

### 1. Unit тесты (самый быстрый старт)

```bash
cd e:\Project\ARV\frontend
npm test
```

Вы должны увидеть:
```
Test Suites: 4 passed, 4 total
Tests:       21 passed, 21 total
Snapshots:   0 total
Time:        5.234s
```

### 2. Проверка покрытия

```bash
npm run test:coverage
```

После выполнения откройте:
```
e:\Project\ARV\frontend\coverage\lcov-report\index.html
```

### 3. E2E тесты (требуется установка браузеров)

```bash
# Установить Playwright браузеры (один раз)
npx playwright install chromium

# Запустить E2E тесты
npm run test:e2e
```

### 4. Интерактивный режим Playwright

```bash
npm run test:e2e:ui
```

Откроется UI где можно:
- Видеть все тесты
- Запускать по одному
- Смотреть trace
- Дебажить

---

## 📊 Структура тестов

```
frontend/tests/
├── unit/               21 тестов
│   ├── hooks/          15 тестов (auth, theme)
│   └── components/     6 тестов (KpiCard)
│
├── integration/        7 тестов
│   └── pages/          7 тестов (Login)
│
└── e2e/               20 сценариев
    ├── auth.spec.ts        6 сценариев
    ├── companies.spec.ts   7 сценариев
    └── ar-content.spec.ts  7 сценариев
```

**Итого: 48 тестов + 14 визуальных снапшотов**

---

## 🎭 Примеры запуска

### Запустить конкретный тест

```bash
# Jest
npm test -- useAuthStore

# Playwright
npx playwright test auth.spec.ts
```

### Watch mode (авто-перезапуск)

```bash
npm run test:watch
```

### Только coverage

```bash
npm run test:coverage
```

### TypeScript проверка

```bash
npm run test:type
```

### Полный CI прогон

```bash
npm run test:ci
```

---

## 🐛 Troubleshooting

### "Cannot find module '@testing-library/react'"

Это нормально! TypeScript показывает ошибки до установки зависимостей.
После `npm install` всё работает.

### Playwright браузеры не установлены

```bash
npx playwright install --with-deps chromium
```

### Jest кэш проблемы

```bash
npx jest --clearCache
npm test
```

---

## 📝 Добавление новых тестов

### Unit тест для компонента

Создайте файл `frontend/tests/unit/components/MyComponent.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { MyComponent } from '@/components/MyComponent';

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
```

### E2E тест

Создайте файл `frontend/tests/e2e/my-feature.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test('my feature works', async ({ page }) => {
  await page.goto('/my-page');
  await expect(page.getByText('Hello')).toBeVisible();
});
```

---

## 🎯 Цели покрытия

```
Branches:   85%+
Functions:  90%+
Lines:      90%+
Statements: 90%+
```

---

## 📚 Полезные команды

```bash
# Все unit/integration тесты
npm test

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage

# E2E headless
npm run test:e2e

# E2E UI mode
npm run test:e2e:ui

# E2E с браузером
npm run test:e2e:headed

# Visual regression
npm run test:visual

# TypeScript check
npm run test:type

# Полный CI набор
npm run test:ci
```

---

## ✨ Следующие шаги

1. **Запустите тесты**: `npm test`
2. **Проверьте покрытие**: `npm run test:coverage`
3. **Попробуйте E2E**: `npm run test:e2e:ui`
4. **Изучите примеры**: смотрите `tests/unit/`, `tests/integration/`, `tests/e2e/`

---

## 📖 Документация

- **Полное руководство**: [`TESTING.md`](./TESTING.md)
- **Summary**: [`TESTING_IMPLEMENTATION_SUMMARY.md`](./TESTING_IMPLEMENTATION_SUMMARY.md)

---

**Готово к использованию! 🎉**
