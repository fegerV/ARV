# iOS Release: GitHub Actions → App Store

Пошаговая инструкция по сборке iOS приложения V-Portal через GitHub Actions и публикации в App Store.

---

## Шаг 1. Подготовка в Apple Developer Portal

### 1.1. Создать Distribution Certificate

1. Зайти на [developer.apple.com](https://developer.apple.com/account) → **Certificates, IDs & Profiles**
2. **Certificates** → нажать **+** → выбрать **Apple Distribution**
3. Следовать инструкциям (создать CSR через Keychain Access на Mac)
4. Скачать `.cer` файл и установить в Keychain
5. Экспортировать из Keychain Access как `.p12` (с паролем)

### 1.2. Проверить Bundle ID

1. **Identifiers** → найти `ru.neuroimagen.arviewer`
2. Убедиться что статус **Active**

### 1.3. Создать App Store Provisioning Profile

1. **Profiles** → нажать **+** → выбрать **App Store**
2. Выбрать Bundle ID: `ru.neuroimagen.arviewer`
3. Выбрать Distribution Certificate
4. Скачать `.mobileprovision` файл

---

## Шаг 2. Получить API ключ App Store Connect

1. [App Store Connect](https://appstoreconnect.apple.com) → **Users and Access** → **Keys** → **App Store Connect API**
2. Нажать **Generate API Key**
3. Скачать `.p8` файл — **скачивается один раз!**
4. Записать: **Key ID**, **Issuer ID**
5. **Team ID** — на [developer.apple.com](https://developer.apple.com/account) → **Membership**

---

## Шаг 3. Добавить секреты в GitHub

GitHub → Repository → **Settings** → **Secrets and variables** → **Actions**:

| Secret | Значение | Пример |
|--------|----------|--------|
| `IOS_CERTIFICATE_P12_BASE64` | Base64 от `.p12` файла | `MII...` |
| `IOS_CERTIFICATE_PASSWORD` | Пароль от `.p12` | `MyP@ssw0rd` |
| `IOS_PROVISIONING_PROFILE_BASE64` | Base64 от `.mobileprovision` | `PD9...` |
| `IOS_PROVISIONING_PROFILE_NAME` | Имя профиля | `App Store ru.neuroimagen.arviewer` |
| `APPLE_TEAM_ID` | Team ID | `X1Y2Z3ABCD` |
| `APPLE_API_KEY_ID` | Key ID | `ABC123DEF4` |
| `APPLE_API_ISSUER_ID` | Issuer ID | `a1b2c3d4-...` |
| `APPLE_API_KEY_CONTENT` | Содержимое `.p8` файла | `-----BEGIN PRIVATE KEY-----...` |

**Windows PowerShell для кодирования:**
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("certificate.p12")) | Set-Clipboard
[Convert]::ToBase64String([IO.File]::ReadAllBytes("profile.mobileprovision")) | Set-Clipboard
```

---

## Шаг 4. Создать приложение в App Store Connect

1. **My Apps** → **+** → **New App**
2. Name: `V-Portal`, Bundle ID: `ru.neuroimagen.arviewer`, SKU: `VPORTAL001`
3. Заполнить: Description, Keywords, Support URL, Privacy Policy URL
4. Загрузить скриншоты и App Icon (1024×1024)

---

## Шаг 5. Запустить сборку

### Через тег:
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Вручную:
GitHub → **Actions** → **iOS Release** → **Run workflow** → version: `1.0.0`, upload_to_testflight: `true`

---

## Шаг 6. TestFlight → App Store

1. **TestFlight** → выбрать сборку → добавить тестировщиков
2. **App Store** → выбрать build → заполнить metadata → **Submit for Review**
3. Ожидание 24–48 часов → Approved → доступно в App Store

---

## Быстрая шпаргалка

```
1. developer.apple.com → Certificates + Profiles
2. App Store Connect → API Key (.p8)
3. GitHub Secrets → 8 секретов
4. App Store Connect → Создать App
5. git tag v1.0.0 && git push origin v1.0.0
6. GitHub Actions → сборка → TestFlight
7. TestFlight → протестировать
8. App Store → заполнить metadata → Submit for Review
9. Approved → доступно в App Store
```
