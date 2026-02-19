# AR Viewer — Android

Мобильное приложение для просмотра AR-контента. Наводишь камеру на маркер (фото) — поверх него воспроизводится видео. Построено на ARCore, Kotlin, Media3, Hilt DI и Firebase Crashlytics.

## Стек

| Компонент | Версия |
|---|---|
| Kotlin | 2.0.21 |
| minSdk / targetSdk | 24 / 35 |
| ARCore | 1.52.0 |
| Media3 (ExoPlayer) | 1.7.1 |
| CameraX | 1.4.0 |
| ML Kit Barcode | 17.3.0 |
| Hilt DI | 2.51.1 |
| Firebase BOM | 33.6.0 |
| OkHttp / Retrofit | 4.12.0 / 2.12.0 |

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
  QrScannerActivity               │
    └─ CameraX + ML Kit           ├─ ExoPlayer + VideoCache (256 MB LRU)
                                  └─ ArRecorder (запись MP4, recording/)
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
├── ArViewerApp.kt                  # @HiltAndroidApp, Firebase init
├── MainActivity.kt                 # Ввод ID / QR / deep link → загрузка манифеста → AR
├── QrScannerActivity.kt            # CameraX + ML Kit Barcode
├── ArViewerActivity.kt             # ARCore + ExoPlayer + фото/видео запись
├── ar/
│   ├── ArRenderer.kt               # GLSurfaceView.Renderer, видео + камера + запись
│   ├── ArSessionHelper.kt          # Создание ARCore Session, Augmented Image DB
│   ├── BackgroundRenderer.kt       # Отрисовка камеры (OpenGL)
│   ├── VideoQuadRenderer.kt        # Видео-квад на AR-маркере (OES texture)
│   ├── RecordableEGLConfigChooser.kt # EGL-конфигурация для записи
│   └── ShaderUtil.kt               # Загрузка GLSL шейдеров
├── recording/
│   └── ArRecorder.kt               # Запись AR-сцены в MP4
├── data/
│   ├── api/ViewerApi.kt            # Retrofit интерфейс
│   ├── cache/
│   │   ├── ManifestCache.kt        # Диск-кеш манифестов (по uniqueId, 7 дней)
│   │   ├── MarkerCache.kt          # Диск-кеш маркеров (по uniqueId, 7 дней)
│   │   └── VideoCache.kt           # Media3 SimpleCache (LRU, 256 MB)
│   ├── model/
│   │   ├── ViewerManifest.kt       # Модель манифеста AR-контента
│   │   ├── ViewerManifestVideo.kt  # Модель видео в манифесте
│   │   ├── ViewerError.kt          # Ошибки + ContentUnavailableReason
│   │   └── ContentCheckResponse.kt # Ответ проверки доступности контента
│   └── repository/
│       └── ViewerRepository.kt     # Cache-first загрузка + фоновый refresh
├── di/
│   └── NetworkModule.kt            # OkHttp, Retrofit, Gson (Hilt @Module)
├── ui/
│   ├── MainViewModel.kt            # Загрузка манифеста, навигация
│   ├── ArViewerViewModel.kt        # Загрузка маркера (bitmap)
│   └── ViewerErrorMessages.kt      # Локализованные сообщения об ошибках
└── util/
    ├── UniqueIdParser.kt            # Парсинг UUID из URL / строки
    ├── CrashReporter.kt             # Обёртка Firebase Crashlytics
    └── CrashReporting.kt            # Фасад логирования ошибок (Logcat / Crashlytics)
```

## Быстрый старт

### Требования

- Android Studio (Ladybug+ / Meerkat+)
- Android SDK: API 35+, Build-Tools, Platform-Tools
- JDK 17 (встроен в Android Studio)
- Для полноценного AR: устройство из [списка ARCore](https://developers.google.com/ar/devices). Приложение можно устанавливать на любом Android — на неподдерживаемых при открытии AR показывается экран с пояснением и кнопками «Проверить снова» и «Список поддерживаемых устройств».

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

**Windows (PowerShell):**

```powershell
cd android
.\gradlew.bat assembleDebug
```

При первой сборке из терминала может потребоваться принять лицензии SDK:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\cmdline-tools\latest\bin\sdkmanager.bat" --licenses
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
   - Ошибки: неверный ID, истёкшая подписка, нет видео, нет ARCore. На устройствах без AR Core — экран с кнопками «Проверить снова» и «Список поддерживаемых устройств».
3. **Google Play:** чтобы приложение было доступно на всех устройствах (а не только с AR Core), в консоли разработчика не следует ограничивать установку по «AR Core supported devices». Тогда пользователи смогут установить приложение на любой телефон; AR будет работать только на устройствах из списка Google.
4. Логи по тегам: `ArViewerActivity`, `ArRenderer`, `VideoQuadRenderer`, `ArSessionHelper`, `ViewerRepository`.

## Версионирование

- `versionName` и `versionCode` в `app/build.gradle.kts`
- Формат: **MAJOR.MINOR.PATCH** (semver)
- При каждом релизе: увеличить `versionCode`, обновить `versionName`
- Текущая версия: **1.0.1** (`versionCode = 2`)
