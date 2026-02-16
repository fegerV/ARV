# AR Viewer — Android

Мобильное приложение для просмотра AR-контента. Наводишь камеру на маркер (фото) — поверх него воспроизводится видео. Построено на ARCore, Kotlin, Media3, Hilt DI и Firebase Crashlytics.

## Стек

| Компонент | Версия |
|---|---|
| Kotlin | 2.0 |
| minSdk / targetSdk | 24 / 35 |
| ARCore | 1.52 |
| Media3 (ExoPlayer) | 1.7.1 |
| Hilt DI | 2.51.1 |
| Firebase BOM | 33.6.0 |

## API бэкенда

| Эндпоинт | Назначение |
|---|---|
| `GET /api/viewer/ar/{unique_id}/check` | Проверка доступности контента |
| `GET /api/viewer/ar/{unique_id}/manifest` | Манифест (маркер, видео, метаданные) |
| `GET /api/viewer/ar/{unique_id}/active-video` | Следующее видео (ротация) |
| `GET /.well-known/assetlinks.json` | App Links для `https://ar.neuroimagen.ru/view/{id}` |

Deep link (запасной): `arv://view/{unique_id}`

## Архитектура

```
MainActivity                   ArViewerActivity
  │                               │
  ├─ MainViewModel                ├─ ArViewerViewModel
  │    └─ ViewerRepository        │    └─ MarkerCache (disk, по uniqueId)
  │         ├─ ViewerApi          │
  │         └─ ManifestCache      ├─ ArRenderer (OpenGL)
  │              (disk, 7 дней)   │    ├─ BackgroundRenderer (камера)
  │                               │    └─ VideoQuadRenderer (видео на маркере)
  │                               │
  │                               ├─ ExoPlayer + VideoCache (256 MB LRU)
  │                               └─ ArRecorder (запись MP4)
```

**Ключевые решения:**

- **MVVM + Hilt** — ViewModel'ы не содержат Android-зависимостей (кроме `@ApplicationContext`), вся DI через `@HiltViewModel` / `@Inject`.
- **Cache-first манифест** — при повторном открытии того же контента манифест возвращается из кеша мгновенно, фоновый refresh обновляет кеш для следующего раза (stale-while-revalidate).
- **Стабильные ключи кеша** — видео кешируется по `{uniqueId}_video_{videoId}`, маркер по `uniqueId`. Яндекс Диск генерирует новый временный URL при каждом запросе — без стабильных ключей кеш промахивается на 100%.
- **ARCore сессия на фоновом потоке** — создание `AugmentedImageDatabase` вынесено в `Dispatchers.Default`, чтобы main thread не блокировался и loading tips продолжали анимироваться.
- **Видео-квад только после STATE_READY** — рендерер не рисует квад до декодирования первого кадра, предотвращая чёрный прямоугольник.

## Структура проекта

```
app/src/main/java/ru/neuroimagen/arviewer/
├── ArViewerApp.kt              # @HiltAndroidApp, Firebase init
├── MainActivity.kt             # Ввод ID / QR / deep link → загрузка манифеста → AR
├── QrScannerActivity.kt        # CameraX + ML Kit Barcode
├── ArViewerActivity.kt         # ARCore + ExoPlayer + фото/видео запись
├── ar/
│   ├── ArRenderer.kt           # GLSurfaceView.Renderer, видео + камера + запись
│   ├── ArSessionHelper.kt      # Создание ARCore Session, Augmented Image DB
│   ├── BackgroundRenderer.kt   # Отрисовка камеры (OpenGL)
│   ├── VideoQuadRenderer.kt    # Видео-квад на AR-маркере (OES texture)
│   ├── ArRecorder.kt           # Запись AR-сцены в MP4
│   └── ShaderUtil.kt           # Загрузка GLSL шейдеров
├── data/
│   ├── api/ViewerApi.kt        # Retrofit интерфейс
│   ├── cache/
│   │   ├── ManifestCache.kt    # Диск-кеш манифестов (по uniqueId, 7 дней)
│   │   ├── MarkerCache.kt      # Диск-кеш маркеров (по uniqueId, 7 дней)
│   │   └── VideoCache.kt       # Media3 SimpleCache (LRU, 256 MB)
│   ├── model/                  # ViewerManifest, ViewerError, ContentCheckResponse
│   └── repository/
│       └── ViewerRepository.kt # Cache-first загрузка + фоновый refresh
├── di/
│   └── NetworkModule.kt        # OkHttp, Retrofit, Gson (Hilt @Module)
├── ui/
│   ├── MainViewModel.kt        # Загрузка манифеста, навигация
│   └── ArViewerViewModel.kt    # Загрузка маркера (bitmap)
└── util/
    ├── UniqueIdParser.kt       # Парсинг UUID из URL / строки
    └── CrashReporter.kt        # Обёртка Firebase Crashlytics
```

## Быстрый старт

### Требования

- Android Studio (Ladybug+)
- Android SDK: API 34+, Build-Tools, Platform-Tools
- Устройство из [списка ARCore](https://developers.google.com/ar/devices)

### Настройка

1. **File → Open** → выбрать папку `android/` (не корень репозитория).
2. Дождаться Gradle Sync. Если SDK не найден — прописать в `android/local.properties`:

```properties
sdk.dir=C\:\\Users\\<user>\\AppData\\Local\\Android\\Sdk
```

3. **File → Sync Project with Gradle Files**.

### Сборка

**Debug (для разработки):**

```bash
cd android
./gradlew assembleDebug
```

**Release для RuStore / Google Play** (иначе стор выдаст «Это дебаг-сборка»):

1. Создайте ключ подписи (один раз; храните пароли и `.keystore` в надёжном месте).

   Перейдите в папку `android/app` и выполните (в PowerShell или cmd — `keytool` идёт в составе JDK/Android Studio):

   ```powershell
   cd E:\Project\ARV\android\app
   keytool -genkey -v -keystore portal-ar-release.keystore -alias portal-ar -keyalg RSA -keysize 2048 -validity 10000
   ```

   Если `keytool` не найден, укажите полный путь к нему (JDK из Android Studio):
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\jbr\bin\keytool.exe" -genkey -v -keystore portal-ar-release.keystore -alias portal-ar -keyalg RSA -keysize 2048 -validity 10000
   ```

   Введите пароль хранилища и пароль ключа (можно один и тот же), имя и т.д. — эти пароли понадобятся для секретов в GitHub и для локальной сборки.

2. Скопируйте пример конфига и заполните пути и пароли:

```bash
cp keystore.properties.example keystore.properties
```

В `keystore.properties` укажите:

- `storeFile` — имя файла ключа (например `portal-ar-release.keystore`)
- `storePassword` и `keyPassword` — пароли от хранилища и ключа
- `keyAlias` — алиас ключа (например `portal-ar`)

3. Соберите релизный бандл (AAB — для загрузки в сторы):

```bash
cd android
./gradlew bundleRelease
```

Файл для загрузки: `android/app/build/outputs/bundle/release/app-release.aab`. Загружайте именно его в RuStore или Google Play.

**Сборка на GitHub (Actions):**

- При пуше в `main`/`develop` (или по кнопке **Run workflow**) всегда собирается **debug APK** → артефакт `app-debug`.
- **Release AAB** собирается только если в репозитории заданы секреты подписи. Тогда появляется артефакт `app-release-aab` (AAB для RuStore/Play).

**Откуда взять секреты:** их не скачивают — вы сами задаёте их при создании ключа (один раз).

1. **Создайте ключ** (если ещё не создавали для RuStore/Play) — см. шаг 1 выше в «Release для RuStore». При создании вы вводите пароль хранилища и пароль ключа — запомните их.
2. **Закодируйте файл ключа в base64** (Windows PowerShell, из папки `android/app`):
   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("portal-ar-release.keystore")) | Set-Clipboard
   ```
   Строка попадёт в буфер обмена — вставьте её в значение секрета в GitHub.
3. В репозитории: **Settings → Secrets and variables → Actions → New repository secret**. Создайте четыре секрета:

| Секрет | Откуда взять |
|--------|----------------|
| `ANDROID_KEYSTORE_BASE64` | Вставка из буфера после команды base64 выше (содержимое `.keystore` в base64) |
| `ANDROID_KEYSTORE_PASSWORD` | Пароль, который вы ввели при создании ключа (store password) |
| `ANDROID_KEY_ALIAS` | Алиас ключа, например `portal-ar` (как в команде keytool `-alias`) |
| `ANDROID_KEY_PASSWORD` | Пароль ключа, который вы ввели при создании ключа (key password) |

После добавления секретов перезапустите workflow (Actions → Android (Portal AR) → Re-run all jobs) или сделайте пуш в `android/`.

Windows:

```powershell
cd android
.\gradlew.bat assembleDebug
```

При первой сборке из терминала — принять лицензии:

```powershell
.\scripts\android_accept_licenses.ps1
```

### Запуск

**Run → Run 'app'** (Shift+F10) на подключённом устройстве. Эмулятор для AR не подходит.

## Firebase Crashlytics

Проект содержит placeholder `app/google-services.json`. Для реальных крэш-отчётов:

1. Создать проект в [Firebase Console](https://console.firebase.google.com/).
2. Добавить Android-приложение: `ru.neuroimagen.arviewer`.
3. Скачать `google-services.json` → заменить placeholder в `app/`.
4. Crashlytics включается автоматически в release-билдах. В debug отключён через `CrashReporter.init(enabled = false)`.

## Кеширование

| Что | Где | Ключ | TTL | Размер |
|---|---|---|---|---|
| Манифест | `manifest_cache/` | `uniqueId` | 7 дней | ~1 КБ |
| Маркер (фото) | `marker_cache/` | `uniqueId` | 7 дней | 1–5 МБ |
| Видео | `video_cache/` | `{uniqueId}_video_{videoId}` | LRU | до 256 МБ |

**Стратегия:** cache-first с фоновым обновлением. Повторное открытие того же контента — мгновенное (маркер и видео читаются с диска, сетевой запрос не блокирует).

## Тестирование

1. Распечатать маркер (фото из манифеста) — достаточный размер и контраст.
2. Сценарии:
   - Ввод `unique_id` → проверка → загрузка → AR
   - Deep link: `https://ar.neuroimagen.ru/view/{id}` и `arv://view/{id}`
   - Наведение на маркер → воспроизведение видео
   - Кнопка «Снимок» (PixelCopy → MediaStore)
   - Ошибки: неверный ID, истёкшая подписка, нет видео, нет ARCore
3. Логи по тегам: `ArViewerActivity`, `ArRenderer`, `VideoQuadRenderer`, `ArSessionHelper`, `ViewerRepository`.

## Версионирование

- `versionName` и `versionCode` в `app/build.gradle.kts`
- Формат: **MAJOR.MINOR.PATCH** (semver)
- При каждом релизе: увеличить `versionCode`, обновить `versionName`
