# AR Viewer (iOS)

Приложение для просмотра AR-контента на iPhone/iPad. Тот же бэкенд и API, что и [Android-приложение](../android) (ar.neuroimagen.ru).

## Возможности

- **Сканирование QR-кода** — камера для быстрого открытия контента по QR на маркере.
- **Ввод вручную** — UUID или ссылка вида `https://ar.neuroimagen.ru/view/{uuid}` или `arv://view/{uuid}`.
- **Deep link** — схема `arv://view/{unique_id}` для открытия из браузера («Открыть в приложении»).
- **Просмотр AR** — открывается веб-страница `/view/{id}` в in-app WebView (Web AR на том же бэкенде).
- **Аналитика** — при открытии контента создаётся сессия (`POST /api/mobile/sessions`) с `device_type=mobile`, `os=iOS`, `device_model` для статистики в админке.

## Требования

- Xcode 15+
- iOS 15.0+
- Камера (для QR)

## Сборка

1. Откройте `ARViewer.xcodeproj` в Xcode (из папки `ios/`).
2. Выберите целевое устройство или симулятор.
3. Product → Run (⌘R).

Для установки на устройство нужна подписанная сборка (Signing & Capabilities → Team).

## Конфигурация

Базовый URL API задаётся в `ViewerService.shared.baseURL` (по умолчанию `https://ar.neuroimagen.ru`). Для теста можно заменить на свой сервер.

## Структура

- `ARViewerApp.swift` — точка входа.
- `Views/MainView.swift` — главный экран (QR, ввод, открыть).
- `Views/QRScannerView.swift` — сканер QR (AVFoundation).
- `Views/WebARView.swift` — WKWebView с `/view/{id}`.
- `Services/ViewerService.swift` — API: check, manifest, mobile/sessions.
- `Models/ViewerManifest.swift` — модели ответов API.
- `Utils/UniqueIdParser.swift` — разбор UUID и URL (arv://, https://).

## Бэкенд

Страница `/view/{unique_id}` на сервере отдаёт ссылки «Открыть в приложении» (arv://) и «Скачать в Google Play». После публикации iOS-приложения в App Store добавьте на страницу кнопку «Скачать в App Store» и при необходимости настройте [Universal Links](https://developer.apple.com/ios/universal-links/) для домена ar.neuroimagen.ru.
