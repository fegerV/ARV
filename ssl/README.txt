Папка для SSL-сертификатов (HTTPS).
Директория ssl/ и файлы *.pem не попадают в git (.gitignore).

Положите сюда:
  - privkey.pem   — закрытый ключ
  - fullchain.pem — сертификат (цепочка)

В .env укажите (относительно корня проекта):
  SSL_KEYFILE=ssl/privkey.pem
  SSL_CERTFILE=ssl/fullchain.pem
  PUBLIC_URL=https://ar.neuroimagen.ru

Домен https://ar.neuroimagen.ru, порты проброшены. При наличии обоих путей uvicorn запускается с HTTPS.
