# Настройка Android-проекта в Android Studio

Инструкция для случая, когда папка SDK пуста (`C:\Users\<user>\AppData\Local\Android\Sdk` или аналог).

## Где скачать SDK и куда положить

- **Скачивать отдельно не обязательно.** Обычно SDK ставится **вместе с Android Studio**: при установке или при первом открытии **SDK Manager** (см. шаг 2 ниже) Android Studio сам скачивает нужные компоненты в выбранную папку.
- **Если нужны только инструменты без IDE:** [Command line tools only](https://developer.android.com/studio#command-line-tools-only) — распаковать архив, затем через `sdkmanager` установить `platforms;android-34`, `build-tools`, `platform-tools` и т.д. Для сборки AR Viewer проще использовать Android Studio.

**Куда положить SDK (путь):**
- По умолчанию на Windows: `C:\Users\<ИмяПользователя>\AppData\Local\Android\Sdk`.
- Можно указать свою папку, например `D:\Android\Sdk` или `E:\Android\Sdk` — без пробелов и кириллицы. Её укажете в **Settings → Android SDK** (или в мастере при первом запуске). Android Studio создаст каталог и скачает туда компоненты.
- В проекте AR Viewer путь к этой папке прописывается в `android/local.properties` в переменной `sdk.dir` (см. раздел 4).

## 1. Установить Android Studio

- Скачайте с [developer.android.com/studio](https://developer.android.com/studio).
- Установите, при первом запуске пройдите мастер настройки.

## 2. Установить Android SDK через Android Studio

1. **File → Settings** (или **Ctrl+Alt+S**).
2. **Languages & Frameworks → Android SDK**.
3. Если видите предупреждение «The Android SDK location cannot be at…» или путь к SDK недоступен:
   - Нажмите **Edit** рядом с путём к SDK (или **Android SDK Location**).
   - Оставьте путь по умолчанию `C:\Users\Vertex\AppData\Local\Android\Sdk` **или** укажите другую папку (например `D:\Android\Sdk`) и нажмите **Next** — Android Studio создаст папку и предложит скачать компоненты.
4. Вкладка **SDK Platforms**:
   - Отметьте **Android 14.0 ("UpsideDownCake"; API 34)** — проект использует `compileSdk = 34`.
   - При необходимости отметьте **Android 15.0 (API 35)** для новых устройств.
   - Нажмите **Apply** — начнётся загрузка (несколько гигабайт).
5. Вкладка **SDK Tools**:
   - Убедитесь, что отмечены: **Android SDK Build-Tools**, **Android SDK Platform-Tools**, **Android SDK Command-line Tools**, **Google Play services** (для ARCore).
   - Нажмите **Apply**, дождитесь установки.

## 3. Открыть проект в Android Studio

**Важно:** открывать нужно **папку `android`**, а не корень репозитория ARV.

1. **File → Open**.
2. Укажите папку: `E:\Project\ARV\android`.
3. Нажмите **OK**.
4. Если появится «Gradle Sync» — дождитесь окончания (первый раз может скачивать зависимости).
5. Если спросят про SDK — выберите установленный SDK (путь из шага 2).

## 4. Путь к SDK в проекте

В папке `android` есть файл **`local.properties`** (не коммитится в git). В нём должна быть строка:

```properties
sdk.dir=C\:\\Users\\Vertex\\AppData\\Local\\Android\\Sdk
```

- Если SDK вы установили в другой каталог, отредактируйте `sdk.dir` в `local.properties` на свой путь (с двойными обратными слэшами `\\` для Windows).
- После изменения `local.properties` выполните **File → Sync Project with Gradle Files**.

## 5. Принять лицензии SDK (для сборки из терминала)

Если будете собирать из командной строки (`gradlew assembleDebug`), один раз примите лицензии:

Из **корня репозитория** `E:\Project\ARV`:

```powershell
.\scripts\android_accept_licenses.ps1
```

Или из папки `android`:

```powershell
..\scripts\android_accept_licenses.ps1
```

В Android Studio сборка обычно не требует этого шага — лицензии принимаются через диалоги при установке компонентов.

## 6. Сборка и запуск

- В Android Studio: **Build → Make Project** (или **Ctrl+F9**).
- Запуск на устройстве/эмуляторе: зелёная кнопка **Run** или **Shift+F10**.

Эмулятор для AR не подойдёт — ARCore требует реальное устройство из [списка поддерживаемых](https://developers.google.com/ar/devices).

## Если SDK по-прежнему «unavailable»

- Убедитесь, что в папке SDK после установки есть подпапки: `platforms`, `build-tools`, `platform-tools`, `tools` (или `cmdline-tools`).
- Перезапустите Android Studio.
- В **File → Invalidate Caches → Invalidate and Restart** — сброс кэшей и перезапуск.

## 7. Базовый URL API

Приложение обращается к бэкенду по адресу из `BuildConfig.API_BASE_URL` (задаётся в `android/app/build.gradle.kts`).

- По умолчанию: `https://ar.neuroimagen.ru`.
- Для отладки на локальном сервере замените в `build.gradle.kts` в `defaultConfig` и в `buildTypes.debug`:
  ```kotlin
  buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8000\"")  // эмулятор → localhost ПК
  // или для устройства в той же сети:
  buildConfigField("String", "API_BASE_URL", "\"http://192.168.1.100:8000\"")
  ```
- После изменения выполните **File → Sync Project with Gradle Files** и пересоберите проект.

**Важно:** для ARCore и камеры в продакшене нужен HTTPS. Локальный HTTP — только для разработки.

## 8. App Links и deep link

В `AndroidManifest.xml` уже настроено:

- **App Link (HTTPS):** `https://ar.neuroimagen.ru/view/{unique_id}` — intent-filter с `android:autoVerify="true"`. Чтобы Android открывал ссылку сразу в приложении без выбора браузера, на бэкенде должен быть доступен `https://ar.neuroimagen.ru/.well-known/assetlinks.json` с корректными SHA-256 отпечатками приложения (см. README и [docs/AR_VIEWER_TROUBLESHOOTING.md](AR_VIEWER_TROUBLESHOOTING.md)).
- **Custom scheme (запасной):** `arv://view/{unique_id}` — работает без верификации; на лендинге кнопка «Открыть в приложении» ведёт на этот URL.

Если используете другой домен (например, для теста), добавьте в манифест второй `intent-filter` с `android:autoVerify="true"` и нужным `android:host`, либо временно тестируйте только через `arv://view/{unique_id}`.

## 9. Отладка

- **Логи:** в Logcat фильтруйте по тегам `BackgroundRenderer`, `VideoQuadRenderer`, `ArSessionHelper`, `ShaderUtil`, `MainActivity`, `ArViewerActivity`.
- **Устройство:** ARCore не работает в эмуляторе. Нужно реальное устройство из [списка поддерживаемых ARCore](https://developers.google.com/ar/devices).
- **Типичные проблемы:**
  - «SDK location not found» — задайте `sdk.dir` в `local.properties`.
  - Ошибки Gradle sync — проверьте доступ в интернет (загрузка зависимостей), при необходимости **File → Invalidate Caches → Invalidate and Restart**.
  - Приложение не открывается по HTTPS-ссылке — проверьте доступность `/.well-known/assetlinks.json` в браузере и что на сервере заданы `ANDROID_APP_SHA256_FINGERPRINTS`; верификация App Links может занять время после установки приложения.
