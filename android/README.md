# AR Viewer (Android)

Мобильное приложение **AR Viewer** для просмотра AR-контента (ARCore + Kotlin). Получает манифест с бэкенда ARV, отображает видео на маркере (растровое фото). Поддерживает кэширование и офлайн-режим, Splash Screen API, тёмную тему, DI через Hilt и Firebase Crashlytics.

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

- **ArViewerApp** — `@HiltAndroidApp` entry point, инициализация Firebase Crashlytics.
- **MainActivity** — ввод unique_id/URL, проверка (check), загрузка манифеста (с fallback на кэш при офлайн), переход в AR; обработка deep link; кнопка «Сканировать QR». SplashScreen API при старте.
- **QrScannerActivity** — сканер QR (CameraX + ML Kit), возврат unique_id в MainActivity.
- **ArViewerActivity** — ARCore-сессия, Augmented Images, загрузка маркера (с кэшем), фон камеры (OpenGL), Media3 с кэшем видео на кваде по маркеру, кнопки «Снимок» и «Запись видео» (фото через PixelCopy + MediaStore).
- **di/** — Hilt-модули: `NetworkModule` (OkHttp, Retrofit, ViewerApi, Gson).
- **ui/** — ViewModels: `MainViewModel`, `ArViewerViewModel` (оба `@HiltViewModel`).
- **data/** — модели (ViewerManifest, ContentCheckResponse, ViewerError), ViewerApi (Retrofit), ViewerRepository (`@Inject`); кэши ManifestCache, MarkerCache, VideoCache (Media3).
- **ar/** — BackgroundRenderer, VideoQuadRenderer, ArSessionHelper, ShaderUtil, шейдеры в `assets/shaders/`.
- **util/** — `UniqueIdParser` (UUID-парсинг), `CrashReporter` (Firebase Crashlytics обёртка).

## Firebase Crashlytics

В `app/google-services.json` — placeholder-файл. Для включения отправки крэшей:

1. Создать проект в [Firebase Console](https://console.firebase.google.com/).
2. Добавить Android-приложение (package: `ru.neuroimagen.arviewer`).
3. Скачать `google-services.json` и заменить placeholder в `android/app/`.
4. Crashlytics инициализируется автоматически в `ArViewerApp.onCreate()` (отключен в debug-сборках).

## Firebase Crashlytics

Проект поставляется с placeholder-файлом `app/google-services.json`. Для реальной отправки крэш-отчётов:

1. Создать проект в [Firebase Console](https://console.firebase.google.com/).
2. Добавить Android-приложение с пакетом `ru.neuroimagen.arviewer`.
3. Скачать `google-services.json` и заменить placeholder в `app/`.
4. Crashlytics автоматически включится в release-билдах (`BuildConfig.DEBUG == false`).

В debug-билдах сбор крэшей отключён через `CrashReporter.init(enabled = false)`.

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

- **minSdk 24**, targetSdk 35; ARCore 1.52, Media3 1.7.1, Kotlin 2.0, Hilt 2.51.1, Firebase Crashlytics.
- Снимок экрана (PixelCopy) доступен с API 24; сохранение в MediaStore — с учётом разрешений (READ_MEDIA_IMAGES / WRITE_EXTERNAL_STORAGE для старых версий).
- При падении сессии ARCore рендерер перестаёт рисовать кадры; при необходимости обрабатывать `UnavailableException` и показывать пользователю сообщение.

Подробнее: [docs/STRUCTURE.md](../docs/STRUCTURE.md).

## Версионирование

- **versionName** (например `1.0.0`) и **versionCode** задаются в `app/build.gradle.kts`.
- Формат версии: **MAJOR.MINOR.PATCH**. MAJOR — несовместимые изменения; MINOR — новая функциональность; PATCH — исправления.
- При каждом релизе увеличивать `versionCode`; при смене версии для пользователя — `versionName`.

Полное описание: [docs/ANDROID_APP.md](../docs/ANDROID_APP.md#5-версионирование).

## Роадмап

- **Сделано:** главный экран, deep links, QR-сканер, AR Viewer, кэш маркера/манифеста/видео, офлайн, SplashScreen API, Hilt DI, Firebase Crashlytics, тёмная тема, CI.
- **В планах:** запись видео AR, ротация видео по расписанию, настройки, шаринг, аналитика.

Подробный роадмап: [docs/ANDROID_APP.md](../docs/ANDROID_APP.md#6-роадмап).
