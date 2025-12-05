# Frontend Testing Documentation

## 🧪 Тестовая инфраструктура

Vertex AR Admin Panel использует комплексную стратегию тестирования с 90%+ покрытием кода.

### Тестовая пирамида

```
     60% - Unit Tests (Jest + React Testing Library)
     25% - Integration Tests (API + компонентные деревья)
     10% - E2E Tests (Playwright)
      5% - Performance + Visual Regression
```

## 🛠️ Технологический стек

- **Unit/Integration**: Jest 29 + React Testing Library 14
- **E2E**: Playwright 1.48
- **API Mocking**: MSW (Mock Service Worker) 2.2
- **Visual Regression**: Playwright Visual Comparisons
- **Performance**: Lighthouse CI
- **Coverage**: Jest Coverage с минимальными порогами 85-90%

## 📦 Установка

```bash
cd frontend
npm install
```

## 🚀 Запуск тестов

### Unit и Integration тесты

```bash
# Запустить все тесты
npm test

# Watch mode (автоматический перезапуск)
npm run test:watch

# С покрытием
npm run test:coverage

# Проверка типов TypeScript
npm run test:type
```

### E2E тесты (Playwright)

```bash
# Установить браузеры (один раз)
npm run playwright:install

# Запустить E2E тесты
npm run test:e2e

# UI mode (интерактивный режим)
npm run test:e2e:ui

# С видимым браузером
npm run test:e2e:headed
```

### Visual Regression

```bash
# Запустить визуальные тесты
npm run test:visual
```

### Полный CI набор

```bash
# Все тесты как в CI
npm run test:ci
```

## 📁 Структура тестов

```
frontend/
├── tests/
│   ├── setup.ts                    # Глобальная настройка Jest
│   ├── mocks/
│   │   ├── handlers.ts             # MSW API handlers
│   │   ├── server.ts               # MSW server setup
│   │   ├── styleMock.ts            # CSS mock
│   │   └── fileMock.ts             # File mock
│   ├── unit/
│   │   ├── components/             # Тесты компонентов
│   │   │   ├── KpiCard.test.tsx
│   │   │   └── ...
│   │   └── hooks/                  # Тесты хуков
│   │       ├── useAuthStore.test.ts
│   │       └── useThemeStore.test.ts
│   ├── integration/
│   │   └── pages/                  # Тесты страниц
│   │       ├── Login.test.tsx
│   │       ├── Dashboard.test.tsx
│   │       └── ...
│   └── e2e/                        # Playwright E2E
│       ├── auth.spec.ts
│       ├── companies.spec.ts
│       ├── ar-content.spec.ts
│       └── visual/
│           └── visual-regression.spec.ts
├── jest.config.ts                  # Jest конфигурация
└── lighthouserc.json               # Lighthouse CI config
```

## ✅ Минимальные пороги покрытия

```javascript
{
  branches: 85%,
  functions: 90%,
  lines: 90%,
  statements: 90%
}
```

## 🎯 Примеры тестов

### Unit Test (Component)

```typescript
// tests/unit/components/KpiCard.test.tsx
import { render, screen } from '@testing-library/react';
import { KpiCard } from '@/components/(analytics)/KpiCard';

describe('KpiCard Component', () => {
  it('should render title and value', () => {
    render(<KpiCard title="Total Companies" value={45} />);
    
    expect(screen.getByText('Total Companies')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
  });
});
```

### Integration Test (Page)

```typescript
// tests/integration/pages/Login.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Login } from '@/pages/Login';

describe('Login Page', () => {
  it('should successfully login with valid credentials', async () => {
    const user = userEvent.setup();
    render(<Login />);
    
    await user.type(screen.getByLabelText(/email/i), 'admin@test.com');
    await user.type(screen.getByLabelText(/пароль/i), 'password123');
    await user.click(screen.getByRole('button', { name: /войти/i }));
    
    expect(window.location.pathname).toBe('/dashboard');
  });
});
```

### E2E Test (Playwright)

```typescript
// tests/e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test('successful login redirects to dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="email"]', 'admin@vertexar.com');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button:has-text("ВОЙТИ")');
  
  await page.waitForURL('**/dashboard');
  await expect(page.getByText(/dashboard/i)).toBeVisible();
});
```

## 🔍 MSW API Mocking

Все API запросы мокаются через MSW для изолированного тестирования.

```typescript
// tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.post('/api/auth/login', async ({ request }) => {
    const body = await request.json();
    
    if (body.username === 'admin@test.com') {
      return HttpResponse.json({
        access_token: 'mock-jwt-token',
        user: { id: 1, email: 'admin@test.com' }
      });
    }
    
    return HttpResponse.json(
      { detail: 'Неверный email или пароль' },
      { status: 401 }
    );
  }),
];
```

## 📊 Покрытие

После запуска `npm run test:coverage` откройте:

```
coverage/lcov-report/index.html
```

## 🎭 Playwright UI Mode

Интерактивный режим для отладки E2E тестов:

```bash
npm run test:e2e:ui
```

## ⚡ Performance Testing

Lighthouse CI проверяет:
- Performance Score: 90+
- Accessibility: 95+
- Best Practices: 90+
- SEO: 90+

Критические метрики:
- FCP (First Contentful Paint): < 2s
- LCP (Largest Contentful Paint): < 2.5s
- CLS (Cumulative Layout Shift): < 0.1
- TBT (Total Blocking Time): < 300ms

## 🔄 CI/CD Integration

GitHub Actions автоматически запускает:
1. TypeScript type check
2. ESLint
3. Unit + Integration тесты
4. E2E тесты (Chromium, Firefox, Webkit)
5. Visual regression
6. Lighthouse performance
7. Build проверка

## 🐛 Отладка тестов

### Jest Tests

```bash
# Debug отдельного теста
npm test -- --testNamePattern="should login successfully"

# Watch mode для быстрой итерации
npm run test:watch -- --testPathPattern=Login
```

### Playwright Tests

```bash
# Запустить с видимым браузером
npm run test:e2e:headed

# Debug mode
PWDEBUG=1 npm run test:e2e

# Отдельный тест
npx playwright test auth.spec.ts
```

## 📝 Лучшие практики

1. **Именование тестов**: `should [expected behavior] when [condition]`
2. **AAA Pattern**: Arrange → Act → Assert
3. **Изоляция**: Каждый тест независим
4. **Data-testid**: Используйте `data-testid` для стабильных селекторов
5. **Ожидания**: Используйте `waitFor` для асинхронных операций
6. **Моки**: Всегда мокайте внешние зависимости

## 🚨 Troubleshooting

### Jest не находит модули

```bash
# Очистите кэш Jest
npx jest --clearCache
npm test
```

### Playwright браузеры не установлены

```bash
npx playwright install --with-deps
```

### Тесты падают в CI но работают локально

Проверьте:
- Таймауты (увеличьте в CI)
- Асинхронные операции (используйте `waitFor`)
- Переменные окружения

## 📚 Дополнительные ресурсы

- [Jest Documentation](https://jestjs.io/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright Documentation](https://playwright.dev/)
- [MSW Documentation](https://mswjs.io/)

## 🎯 Цели покрытия по модулям

| Модуль | Target Coverage |
|--------|----------------|
| Components | 92% |
| Hooks | 95% |
| Pages | 88% |
| Utils | 100% |
| Overall | 90% ✅ |

---

**Готово к production!** 🚀
