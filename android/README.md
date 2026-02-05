# AR Viewer (Android)

Мобильное приложение **AR Viewer** для просмотра AR-контента (ARCore + Kotlin). Получает манифест с бэкенда ARV, отображает видео на маркере (растровое фото). Поддерживает кэширование и офлайн-режим, Splash Screen при старте.

**Полная документация:** [docs/ANDROID_APP.md](../docs/ANDROID_APP.md) (экраны, архитектура, версионирование, роадмап, сборка, CI).

## Связь с бэкендом

- **Манифест:** `GET /api/viewer/ar/{unique_id}/manifest`
- **Проверка доступности:** `GET /api/viewer/ar/{unique_id}/check`
- **Следующее видео (rotation):** `GET /api/viewer/ar/{unique_id}/active-video`
- **App Links:** `/.well-known/assetlinks.json` для `https://ar.neuroimagen.ru/view/{unique_id}`
- **Deep link (запасной):** `arv://view/{unique_id}`

Контракт API: [docs/API.md](../docs/API.md), раздел «Viewer».

## Настройка проекта в Android Studio

Подробная инструкция (в т.ч. при пустой папке SDK): [docs/ANDROID_STUDIO_SETUP.md](../docs/ANDROID_STUDIO_SETUP.md).

Кратко:

1. **Установить Android Studio** — [developer.android.com/studio](https://developer.android.com/studio). При первом запуске установить Android SDK (SDK Manager: Android 14 / API 34, Build-Tools, Platform-Tools, Google Play services для ARCore).

2. **Открыть именно папку `android`** — **File → Open** → выбрать `E:\Project\ARV\android` (не корень репозитория ARV). Дождаться **Gradle Sync**.

3. **Путь к SDK** — в `android/local.properties` (создаётся автоматически или вручную) задать `sdk.dir` с путём к SDK (например `C\:\\Users\\Vertex\\AppData\\Local\\Android\\Sdk`). После правки: **File → Sync Project with Gradle Files**.

4. **Лицензии** — при сборке из терминала один раз выполнить из корня репозитория: `.\scripts\android_accept_licenses.ps1`. В Android Studio обычно не требуется.

5. **Сборка и запуск** — **Build → Make Project** (Ctrl+F9), запуск на устройстве — **Run** (Shift+F10). ARCore работает только на реальном устройстве из [списка поддерживаемых](https://developers.google.com/ar/devices); эмулятор для AR не подходит.

6. **Если SDK «unavailable»** — проверить наличие папок `platforms`, `build-tools`, `platform-tools` в каталоге SDK; при необходимости **File → Invalidate Caches → Invalidate and Restart**.

## Структура

- **SplashActivity** — экран загрузки при запуске по иконке (~1,5 с), затем переход в MainActivity.
- **MainActivity** — ввод unique_id/URL, проверка (check), загрузка манифеста (с fallback на кэш при офлайн), переход в AR; обработка deep link с немедленным переходом в AR; кнопка «Сканировать QR».
- **QrScannerActivity** — сканер QR (CameraX + ML Kit), возврат unique_id в MainActivity.
- **ArViewerActivity** — ARCore-сессия, Augmented Images, загрузка маркера (с кэшем), фон камеры (OpenGL), ExoPlayer с кэшем видео на кваде по маркеру, кнопки «Снимок» и «Запись видео» (фото через PixelCopy + MediaStore).
- **data/** — модели (ViewerManifest, ContentCheckResponse, ViewerError), ViewerApi (Retrofit), ViewerRepository; кэши ManifestCache, MarkerCache, VideoCache (ExoPlayer).
- **ar/** — BackgroundRenderer, VideoQuadRenderer, ArSessionHelper, ShaderUtil, шейдеры в `assets/shaders/`.

## Сборка

Из корня репозитория:

```bash
cd android && .\gradlew.bat assembleDebug
```

Либо после [установки Gradle](https://gradle.org/install): `gradle assembleDebug`. Перед первой сборкой примите лицензии SDK: `scripts/android_accept_licenses.ps1` (Windows) или `sdkmanager --licenses`.

## Тестирование на устройстве

- Устройство из [списка ARCore](https://developers.google.com/ar/devices); камера; распечатанный маркер (фото из манифеста, достаточный размер и контраст).
- Сценарии: открытие по deep link (HTTPS и `arv://`); ввод unique_id → проверка → загрузка → AR; наведение на маркер и воспроизведение видео; снимок (кнопка «Снимок»); обработка ошибок (неверный ID, истёкшая подписка, нет видео).
- Отладка: логи по тегам `BackgroundRenderer`, `VideoQuadRenderer`, `ArSessionHelper`, `ShaderUtil`; при необходимости отправка диагностики на бэкенд (как в веб-viewer с `?diagnose=1`).

## Стабильность и требования

- **minSdk 24**, targetSdk 34; ARCore 1.40, ExoPlayer 2.19.
- Снимок экрана (PixelCopy) доступен с API 24; сохранение в MediaStore — с учётом разрешений (READ_MEDIA_IMAGES / WRITE_EXTERNAL_STORAGE для старых версий).
- При падении сессии ARCore рендерер перестаёт рисовать кадры; при необходимости обрабатывать `UnavailableException` и показывать пользователю сообщение.

Подробнее: [docs/STRUCTURE.md](../docs/STRUCTURE.md).

## Версионирование

- **versionName** (например `1.0.0`) и **versionCode** задаются в `app/build.gradle.kts`.
- Формат версии: **MAJOR.MINOR.PATCH**. MAJOR — несовместимые изменения; MINOR — новая функциональность; PATCH — исправления.
- При каждом релизе увеличивать `versionCode`; при смене версии для пользователя — `versionName`.

Полное описание: [docs/ANDROID_APP.md](../docs/ANDROID_APP.md#5-версионирование).

## Роадмап

- **Сделано:** главный экран, deep links, QR-сканер, AR Viewer, кэш маркера/манифеста/видео, офлайн, Splash Screen, CI.
- **В планах:** запись видео AR, ротация видео по расписанию, настройки, шаринг, аналитика, Splash API 12+.

Подробный роадмап: [docs/ANDROID_APP.md](../docs/ANDROID_APP.md#6-роадмап).
