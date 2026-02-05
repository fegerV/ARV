# MindAR Generator (устарел)

Генерация маркеров в формате MindAR (.mind) **отключена**. Просмотр AR выполняется только в приложении **AR Viewer** (Android, ARCore).

- **Маркер для ARCore** — растровое изображение (JPEG/PNG), то же фото, что загружено для контента. URL отдаётся в манифесте в поле `marker_image_url`.
- **Сервис маркеров:** [`app/services/marker_service.py`](app/services/marker_service.py) (`ARCoreMarkerService`) — возвращает URL фото как маркера, анализ качества изображения, рекомендации.
- **API вьювера:** см. [API.md](API.md#viewer) (манифест, `/check`, active-video).
