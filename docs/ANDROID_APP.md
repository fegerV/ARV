# AR Viewer — документация приложения

Мобильное приложение для просмотра AR-контента по маркеру (ARCore, Kotlin). Получает манифест и медиа с бэкенда ARV, поддерживает офлайн-режим и кэширование.

---

## 1. Обзор

| Параметр | Значение |
|----------|----------|
| **Название** | AR Viewer |
| **applicationId** | `ru.neuroimagen.arviewer` |
| **minSdk** | 24 |
| **targetSdk** | 34 |
| **Язык** | Kotlin |
| **Сборка** | Gradle 8.x, JDK 17 |

**Основные возможности:**

- Открытие AR по unique_id (ввод, QR-код, deep link / App Link).
- Воспроизведение видео на распознанном маркере (ARCore Augmented Images).
- Кэш маркера и манифеста, кэш видео (ExoPlayer) — работа без сети после первого просмотра.
- Splash Screen при старте по иконке; по ссылке — сразу главный экран.

---

## 2. Экраны

| Экран | Описание |
|-------|----------|
| **SplashActivity** | Экран загрузки при запуске по иконке (логотип, индикатор ~1,5 с), затем переход в MainActivity. |
| **MainActivity** | Главный экран: поле ввода ID/URL, кнопки «Открыть» и «Сканировать QR», панели загрузки и ошибки с «Повторить». |
| **QrScannerActivity** | Сканер QR (CameraX + ML Kit), распознаёт AR-ссылки и UUID, возвращает unique_id в MainActivity. |
| **ArViewerActivity** | AR-сцена: камера, маркер, видео поверх маркера; кнопки «Снимок» и «Запись видео» (запись — заглушка). |

**Deep links:** при открытии по ссылке (`https://ar.neuroimagen.ru/view/{id}` или `arv://view/{id}`) запускается **MainActivity** с intent.data; Splash не показывается.

---

## 3. Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│ UI                                                               │
│   SplashActivity → MainActivity, QrScannerActivity, ArViewerActivity
├─────────────────────────────────────────────────────────────────┤
│ Data                                                             │
│   ViewerRepository (manifest: network + ManifestCache fallback)   │
│   ViewerApi (Retrofit), ApiProvider                               │
│   ManifestCache, MarkerCache, VideoCache                          │
├─────────────────────────────────────────────────────────────────┤
│ AR                                                               │
│   ArSessionHelper, ArRenderer, BackgroundRenderer, VideoQuadRenderer
└─────────────────────────────────────────────────────────────────┘
```

- **Модели:** `ViewerManifest`, `ViewerManifestVideo`, `ContentCheckResponse`, `ViewerError`.
- **Кэш:** манифест по unique_id (7 дней), маркер по URL (7 дней), видео — ExoPlayer SimpleCache (256 МБ, LRU).

Подробнее о структуре модулей: [STRUCTURE.md](STRUCTURE.md), [android/README.md](../android/README.md).

---

## 4. API и конфигурация

- **Base URL:** задаётся в `build.gradle.kts` как `API_BASE_URL` (debug/release), по умолчанию `https://ar.neuroimagen.ru:8000`.
- **Эндпоинты:** `GET /api/viewer/ar/{unique_id}/check`, `GET .../manifest`, `GET .../active-video`; загрузка изображения маркера по полному URL.
- Контракт API: [API.md](API.md), раздел «Viewer».

App Links: `/.well-known/assetlinks.json` для домена `ar.neuroimagen.ru`.

---

## 5. Версионирование

Используется **семантическое версионирование** в формате `MAJOR.MINOR.PATCH`.

| Место | Поле | Описание |
|-------|------|----------|
| **build.gradle.kts** | `versionName` | Строка версии для пользователя (например `1.0.0`). |
| **build.gradle.kts** | `versionCode` | Целое число, монотонно растёт с каждой публикацией (обновления в Store). |

**Правила:**

- **MAJOR** — несовместимые изменения API или контракта с бэкендом.
- **MINOR** — новая функциональность без ломания (новые экраны, офлайн, кэш).
- **PATCH** — исправления ошибок, тексты, мелкие улучшения.

При релизе: увеличить `versionCode` и при необходимости `versionName`, закоммитить, собрать и выложить артефакт/APK.

---

## 6. Роадмап

### Реализовано (v1.0.x)

- [x] Главный экран: ввод ID/URL, открытие AR.
- [x] Deep links и App Links.
- [x] QR-сканер (AR-ссылки и UUID).
- [x] AR Viewer: маркер + видео, снимок экрана.
- [x] Кэш маркера (диск, 7 дней).
- [x] Офлайн: кэш манифеста и медиа (манифест при сетевой ошибке, видео через ExoPlayer cache).
- [x] Splash Screen при старте.
- [x] Сборка в GitHub Actions, артефакт APK.

### В планах

- [ ] Запись видео AR-сцены (сейчас заглушка).
- [ ] Ротация видео по расписанию (запрос active-video при смене ролика).
- [ ] Экран настроек (качество видео, язык, очистка кэша).
- [ ] Шаринг скриншота/видео.
- [ ] Аналитика/события просмотра на бэкенд.
- [ ] Поддержка Android 12+ Splash Screen API (иконка и брендинг в системном сплэше).

---

## 7. Сборка и CI

**Локально (из корня репозитория):**

```bash
cd android
./gradlew assembleDebug
```

APK: `android/app/build/outputs/apk/debug/app-debug.apk`.

**CI (GitHub Actions):**

- Workflow: [.github/workflows/android.yml](../.github/workflows/android.yml).
- Триггеры: push/PR в `main`, `develop`, ручной запуск.
- Шаги: JDK 17, Android SDK 34, кэш Gradle, `./gradlew assembleDebug --no-daemon --stacktrace`, загрузка APK в артефакты (30 дней).

Скачать APK: **Actions** → выбранный run → **Artifacts** → `app-debug`.

---

## 8. Тестирование и отладка

- Устройство из [списка ARCore](https://developers.google.com/ar/devices); эмулятор для AR не подходит.
- Сценарии: запуск по иконке (splash → главный экран); открытие по ссылке; ввод ID и по QR; офлайн после первого просмотра; снимок; обработка ошибок (нет сети, неверный ID).
- Логи: теги по компонентам (например ArSessionHelper, ViewerRepository); при необходимости диагностика как в веб-viewer.

Дополнительно: [AR_VIEWER_TROUBLESHOOTING.md](AR_VIEWER_TROUBLESHOOTING.md), [ANDROID_STUDIO_SETUP.md](ANDROID_STUDIO_SETUP.md).
