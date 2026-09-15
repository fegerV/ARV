# Runbook: восстановление системы из бэкапа

**Проект:** V-Portal / ARV · **Прод:** `ar.neuroimagen.ru` (`192.144.12.68`, пользователь `aruser`)
**Пути:** приложение `/opt/arv/app`, venv `/opt/arv/venv`, медиа `/opt/arv/storage`, staging `/var/backups/arv`
**БД:** PostgreSQL 16, БД `vertex_ar`, роль `vertex_ar`, `127.0.0.1:5432`
**Связанный документ:** `docs/BACKUP_AND_RECOVERY.md` (§7 — проверка целостности, §10 — концептуальный порядок восстановления). Этот файл — операционная, привязанная к хосту версия §10.

---

## 0. TL;DR — что нужно знать до начала

1. **Восстанавливается только база данных.** Медиа и секреты в бэкап **не попадают** (см. §1).
2. **Три уровня проверки, от дешёвого к опасному:** `verify` → `drill` → `restore`. Первые два прод **не трогают**. Третий пишет в БД.
3. **Код отказывается восстанавливать поверх продовой БД.** `restore_to()` сравнивает имя целевой БД с именем из `DATABASE_URL` и падает с `RuntimeError`, если они совпадают. Восстановление идёт **всегда в отдельную БД**, а переключение прода на неё — отдельный осознанный шаг (§6).
4. **Целевую БД нужно создать заранее.** `restore_to()` её **не создаёт** (в отличие от drill). Создание — на операторе.
5. **Порядок обязателен: секреты → БД → медиа.** OAuth-токены в дампе зашифрованы `TOKEN_ENCRYPTION_KEY`; без `.env` восстановленная БД содержит нерасшифровываемые токены.
6. ⚠️ **Главное ограничение:** штатный `restore` скачивает дамп с Yandex Disk, используя токен из **самой БД** (`companies.yandex_disk_token` → расшифровка ключом из `.env`). Значит при **полной потере БД** автоматический путь не работает — нужен ручной (§7).
7. **Ключ шифрования бэкапов (`age`) на прод-сервере не хранится.** Сейчас дампы и так не шифруются (`encrypted=False`), но если шифрование включат — восстановление без ключа невозможно.

---

## 1. Что реально можно восстановить сегодня

| Класс | Данные | Бэкапится? | Как восстановить |
|---|---|---|---|
| **A1** | PostgreSQL `vertex_ar` | ✅ **Да** — ежедневно 03:00 (встроенный APScheduler, `company_id=4`) | `python -m app.cli.backup restore <id> --target-db <db>` |
| **A2** | Оригиналы медиа `/opt/arv/storage` | ❌ **Нет** — `BACKUP_MEDIA_ENABLED=false`, restic не настроен, снапшотов нет | Только из другого источника. `restic restore` работать не с чем |
| **A3** | `.env`, `/etc/letsencrypt`, `deploy/` | ❌ **Нет** — `arv-backup-secrets.timer` не установлен | Вручную из менеджера паролей / копии оператора |
| **B** | Производные медиа (`marker.mind`, `qr_code.png`, thumbnails) | ❌ Нет | Регенерируются из A2 |
| **C** | Redis (JWT-blacklist, OAuth-state, rate-limit) | Не нужно | Эфемерны, пересоздаются сами |
| **D** | Код | ✅ git `github.com/fegerV/ARV` | `git checkout <commit>` |

**Практический вывод.** Сегодня реально восстановима **только БД**. Потеря сервера целиком приведёт к потере всех фото/видео клиентов (A2) — их нельзя перезалить, это физически отснятые материалы. Это осознанный технический долг, а не аварийная ситуация: см. §11.

Состояние на момент последнего аудита (2026-09-15): `backup_history` — последний успех **id 136**, 68 544 Б, `app:/vertexart/backups/backup_20260915_153035.sql.gz`, ротация GFS `deleted=1`. Шифрование — `encrypted=False`.

---

## 2. Шаг 0 — проверка готовности (перед любым восстановлением)

Выполнять **от `aruser`**; команды, требующие конфигурации приложения, запускать из-под `arv` с подгруженным `.env`.

### 2.1 Состояние бэкапов и таймеров

```bash
# последний прогон по каждому типу + статус верификации
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup status'

# установлены ли systemd-таймеры бэкапа (ожидаемо: НЕТ)
systemctl list-timers 'arv-backup-*' --all
ls -1 /etc/systemd/system/arv-backup-* 2>/dev/null || echo "таймеры не установлены"

# история последних попыток
sudo -u postgres psql -d vertex_ar -tAc "
  SELECT id, backup_type, status, encrypted, size_bytes, yd_path, finished_at
  FROM backup_history ORDER BY id DESC LIMIT 10"
```

### 2.2 Наличие инструментов

```bash
for b in pg_dump pg_restore psql age restic rclone gunzip; do
  printf '%-12s %s\n' "$b" "$(command -v $b || echo 'НЕ НАЙДЕН')"
done
```

### 2.3 Права роли БД (нужно для drill и для restore в новую БД)

```bash
sudo -u postgres psql -tAc \
  "SELECT rolname, rolcreatedb, rolsuper FROM pg_roles WHERE rolname='vertex_ar'"
```

`rolcreatedb = f` → **drill и создание целевой БД упадут**. Дать право:
`sudo -u postgres psql -c 'ALTER ROLE vertex_ar CREATEDB'` (drill создаёт и дропает одноразовую БД).

### 2.4 Конфигурация бэкапа (без раскрытия секретов)

```bash
sudo -n grep -E '^(BACKUP_|DATABASE_URL|TOKEN_ENCRYPTION_KEY|SECRET_KEY|STORAGE_BASE_PATH)' \
  /opt/arv/app/.env | sed -E 's/=(.*)$/=<set>/'
```

Что смотреть: `BACKUP_AGE_RECIPIENT` (пусто → дампы не шифруются), `BACKUP_AGE_IDENTITY_FILE` (нужен только для расшифровки), `BACKUP_MEDIA_ENABLED`, `BACKUP_RESTIC_REPOSITORY`, `BACKUP_SECONDARY_RCLONE_REMOTE` (пусто → второго off-site нет), `STORAGE_BASE_PATH`.

### 2.5 Место на диске

```bash
df -h / /var/backups /opt/arv
```

Восстановление требует места под staging-артефакт + распакованный `.dump` + саму БД. Ориентир: **3× размер дампа**.

---

## 3. Сценарий A — «бэкап вообще живой?» (безопасно, ~секунды)

Две независимые проверки: SHA-256 скачанного артефакта против записанного в БД и `pg_restore --list` по распакованному архиву. Прод не затрагивается.

```bash
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup verify --limit 3'
```

Ожидаемый вывод на каждый бэкап:

```
backup 136 (db): checksum=ok toc=ok entries=NNN
```

`checksum=FAIL` — байты не доехали/повреждены на Yandex Disk.
`toc=FAIL` — архив нечитаем как custom-format (обрыв, несовместимая версия `pg_dump`).
Оба случая = **этот артефакт восстанавливать нельзя**, брать предыдущий успешный id.

Результат пишется в `backup_history.verified_at` / `verification_status`.

---

## 4. Сценарий B — учебное восстановление (drill, безопасно)

Восстанавливает **последний** бэкап в одноразовую БД `arv_drill_<ts>` на том же кластере, считает таблицы и **дропает её в `finally`** — даже при падении мусор не останется. Это единственная проверка, доказывающая, что бэкап *пригоден*, а не просто существует.

```bash
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup drill --backup-type db'
```

Ожидаемо: `drill on backup 136: {'ok': True, 'tables_restored': NN, 'duration_seconds': N, 'drill_database': 'arv_drill_...'}`

`ok: False` → смотреть `error` в выводе и журнал:
`journalctl -u arv-backup-drill.service -n 100 --no-pager` (если таймер установлен) или stderr ручного запуска.

Проверить, что мусора не осталось: `sudo -u postgres psql -tAc "SELECT datname FROM pg_database LIKE 'arv_drill%'"` — пусто.

> **Эквивалент через хост-скрипт:** `sudo -u arv /opt/arv/app/deploy/backup/restore-drill.sh` (то же самое + `flock` против параллельного запуска).

**Рекомендация: прогнать drill до инцидента.** Восстановление, которое ни разу не репетировали, — это гипотеза.

---

## 5. Сценарий C — частичное восстановление

Прод работает, потерян фрагмент данных. **Прод-БД не трогаем** — восстанавливаем в отдельную БД и забираем из неё нужное.

```bash
# 1. отдельная БД под восстановление
sudo -u postgres createdb -O vertex_ar vertex_ar_recovered

# 2. восстановить в неё нужный бэкап
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup restore 136 --target-db vertex_ar_recovered'

# 3. вытащить нужное и перенести в прод точечно, например:
sudo -u postgres psql -d vertex_ar_recovered -c \
  "COPY (SELECT * FROM ar_content WHERE id = 1234) TO STDOUT WITH CSV HEADER" > /tmp/one_row.csv
# ... вставить в прод явными INSERT'ами, предварительно посмотрев, что именно перезаписывается

# 4. убрать временную БД, когда она больше не нужна
sudo -u postgres dropdb vertex_ar_recovered
```

Типовые случаи:

| Что случилось | Действие |
|---|---|
| Удалён один AR-контент | восстановить в `vertex_ar_recovered` → перенести строки `ar_content` / `videos` точечными `INSERT` |
| Ошибочно удалены проекты | то же, но сначала выгрузить список id; либо PITR (§10.2 в основном документе), если WAL включён |
| Испорчен один файл медиа | **нечем**: снапшотов restic нет (§1). Только перезагрузка оригинала клиентом |
| Утёк/сгорел Redis | ничего не делать, `systemctl restart redis` |

---

## 6. Сценарий D — полное восстановление с переключением прод-БД

Самый частый «настоящий» сценарий: текущая БД повреждена или данные испорчены, нужно откатиться на вчерашнее состояние. **Прод останавливать обязательно** — иначе приложение будет писать поверх восстановленного.

### 6.1 Сохранить текущее состояние (не пропускать)

```bash
# даже если БД «сломана» — сохранить её как есть, чтобы был путь назад
sudo -u postgres pg_dump -Fc -Z0 vertex_ar > /var/backups/arv/before_restore_$(date -u +%Y%m%d_%H%M%S).dump
sudo -u postgres psql -tAc "SELECT pg_size_pretty(pg_database_size('vertex_ar'))"
```

Если дамп не снимается (БД недоступна) — хотя бы зафиксировать текущий `DATABASE_URL` и не удалять каталог данных до успешной проверки.

### 6.2 Создать целевую БД и восстановить

```bash
sudo -u postgres createdb -O vertex_ar vertex_ar_recovered

sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup restore 136 --target-db vertex_ar_recovered'
```

Ожидаемо: `restore: {'ok': True, 'tables_restored': NN, 'target_database': 'vertex_ar_recovered', ...}`

Через хост-скрипт (интерактивный, с предупреждениями и подтверждением вводом имени БД):

```bash
sudo -u arv /opt/arv/app/deploy/backup/restore.sh --backup-id 136 --target-db vertex_ar_recovered
```

Скрипт предупредит, если `arv.service` ещё запущен, и проверит наличие `age`-идентичности (нужна только для зашифрованных дампов).

### 6.3 Довести схему и проверить данные

```bash
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  DATABASE_URL="postgresql+asyncpg://vertex_ar:<pass>@127.0.0.1:5432/vertex_ar_recovered" \
  /opt/arv/venv/bin/alembic upgrade head'

sudo -u postgres psql -d vertex_ar_recovered -c "
  SELECT 'companies' t, count(*) FROM companies
  UNION ALL SELECT 'projects', count(*) FROM projects
  UNION ALL SELECT 'ar_content', count(*) FROM ar_content
  UNION ALL SELECT 'videos', count(*) FROM videos
  UNION ALL SELECT 'users', count(*) FROM users
  UNION ALL SELECT 'backup_history', count(*) FROM backup_history"
```

Дополнительно проверить, что нет осиротевших связей и пустых `company_id`:

```bash
sudo -u postgres psql -d vertex_ar_recovered -c "
  SELECT count(*) AS orphan_ar_content
  FROM ar_content a LEFT JOIN projects p ON p.id = a.project_id WHERE p.id IS NULL"
sudo -u postgres psql -d vertex_ar_recovered -tAc "
  SELECT count(*) FROM ar_content WHERE company_id IS NULL"
```

### 6.4 Переключить прод

```bash
sudo -n systemctl stop arv.service

# отредактировать DATABASE_URL в /opt/arv/app/.env (файл arv:arv 0600)
sudo -u arv sed -i 's#/vertex_ar"#/vertex_ar_recovered"#' /opt/arv/app/.env   # проверить результат глазами!
sudo -n grep '^DATABASE_URL' /opt/arv/app/.env

sudo -n systemctl start arv.service
sudo -n systemctl is-active arv.service
```

### 6.5 Проверка перед возвратом трафика

```bash
# HTTPS-смоук (nginx редиректит HTTP→HTTPS, поэтому так)
curl -sk -o /dev/null -w '%{http_code}\n' -H "Host: ar.neuroimagen.ru" https://127.0.0.1/
curl -sk -o /dev/null -w '%{http_code}\n' -H "Host: ar.neuroimagen.ru" https://127.0.0.1/admin/login   # 200
curl -sk -o /dev/null -w '%{http_code}\n' -H "Host: ar.neuroimagen.ru" https://127.0.0.1/admin         # 303
curl -sk -o /dev/null -w '%{http_code}\n' -H "Host: ar.neuroimagen.ru" https://127.0.0.1/api/backups/status  # 401

sudo -n journalctl -u arv.service -p warning -n 50 --no-pager
```

Затем вручную (обязательно, до объявления инцидента закрытым):

- [ ] вход супер-админа, виден список компаний/проектов;
- [ ] открывается один AR-контент: фото, видео, `marker.mind`, QR-код на месте;
- [ ] QR сканируется, viewer открывается, видео играет (медиа на месте — `/opt/arv/storage` не пострадал);
- [ ] **проверить расшифровку OAuth-токенов:** открыть настройки хранилища компании → если «токен недействителен» / OAuth не работает, значит `.env` не тот (`TOKEN_ENCRYPTION_KEY` не совпадает) — см. §8.

### 6.6 Откат переключения

Пока старая БД не удалена — откат тривиален:

```bash
sudo -n systemctl stop arv.service
sudo -u arv sed -i 's#/vertex_ar_recovered"#/vertex_ar"#' /opt/arv/app/.env
sudo -n systemctl start arv.service
```

Только после того, как восстановленная БД отработала сутки без замечаний, переименовать старую:

```bash
sudo -u postgres psql -c 'ALTER DATABASE vertex_ar RENAME TO vertex_ar_broken_20260915'
```

Не удалять сразу — неделя наблюдения обходится дешевле повторного инцидента.

---

## 7. Сценарий E — полная потеря БД (ручной путь, автоматика не работает)

**Почему автоматика не сработает.** `BackupService.download_backup()` достаёт артефакт с Yandex Disk, получая провайдера через `_get_yd_provider(record.company_id)` → читает строку `companies` из **той самой БД** и расшифровывает `yandex_disk_token` ключом `TOKEN_ENCRYPTION_KEY` из `.env`. Нет БД → нет `backup_history` (неизвестно, какой артефакт брать) → нет `companies` → нет токена. Замкнутый круг.

Поэтому при полной потере БД:

```
1. Взять .env из офсайт-хранилища оператора (менеджер паролей).
   Нужны как минимум: DATABASE_URL, SECRET_KEY, TOKEN_ENCRYPTION_KEY, STORAGE_BASE_PATH.
   ⚠️ Без TOKEN_ENCRYPTION_KEY восстановленная БД будет содержать
      нерасшифровываемые OAuth-токены → все компании потеряют доступ к своим
      хранилищам и должны будут переподключить Yandex Disk вручную.

2. Скачать дамп ВРУЧНУЮ (не через CLI):
   - войти в аккаунт Yandex, на который указывает prod-хранилище;
   - папка бэкапов: /vertexart/backups/ (последний успешный артефакт, напр.
     backup_20260915_153035.sql.gz);
   - скачать файл. Если включено шифрование (.sql.gz.age) — расшифровать:
       age --decrypt --identity /путь/к/backup-age.key --output dump.sql.gz dump.sql.gz.age

3. Создать БД и роль:
   sudo -u postgres psql -c "CREATE ROLE vertex_ar LOGIN PASSWORD '<из .env>'"
   sudo -u postgres createdb -O vertex_ar vertex_ar

4. Восстановить:
   gunzip -c backup_20260915_153035.sql.gz > /tmp/restore.dump
   sudo -u postgres pg_restore -j4 --exit-on-error -d vertex_ar /tmp/restore.dump

5. Довести схему до кода:  alembic upgrade head   (DATABASE_URL на vertex_ar)

6. Развернуть код нужной версии:
   git clone https://github.com/fegerV/ARV /opt/arv/app
   cd /opt/arv/app && git checkout <commit, зафиксированный при бэкапе>

7. Восстановить медиа — НЕЧЕМ (снапшотов нет). Восстановить секреты — только
   из офсайт-копии оператора. TLS: /etc/letsencrypt либо перевыпустить certbot.

8. Поднять сервисы и пройти чек-лист §6.5.
```

---

## 8. Порядок восстановления и почему он такой

```
секреты (.env)  →  база данных  →  медиа
```

- **Секреты первыми.** Дамп БД не самодостаточен: `companies.yandex_disk_token` и `storage_connections` зашифрованы `TOKEN_ENCRYPTION_KEY` (Fernet), JWT подписываются `SECRET_KEY`. Восстановили БД без `.env` — получили «мёртвые» токены: пользователи видят подключённые хранилища, но они не работают. Проверка — §6.5, последний пункт.
- **БД второй.** Она ссылается на медиа путями (`STORAGE_BASE_PATH`), поэтому `.env` должен быть на месте до первого старта приложения, иначе пути уедут.
- **Медиа последним.** Оно адресуется путями из БД; восстанавливать раньше бессмысленно, а `chown`/`chmod` нужно делать после распаковки:
  `sudo chown -R arv:arv /opt/arv/storage && sudo chmod -R a+rX /opt/arv/storage`

---

## 9. Откат неудачного восстановления

| Ситуация | Действие |
|---|---|
| Восстановили не тот бэкап, прод ещё не переключали | `sudo -u postgres dropdb vertex_ar_recovered`, повторить с правильным id |
| Переключили прод, но данные не те | §6.6 — вернуть `DATABASE_URL` на прежнюю БД |
| Прежняя БД уже переименована | `ALTER DATABASE vertex_ar_broken_<ts> RENAME TO vertex_ar` + вернуть `DATABASE_URL` |
| Восстановление упало на `--exit-on-error` | посмотреть первые ошибки: `pg_restore ... 2>&1 | head -50`. Частые причины: целевая БД не пуста, нет прав у роли, несовместимая версия `pg_restore` (клиент старше сервера) |

`pg_restore` вызывается с `--exit-on-error` намеренно: восстановление, «прошедшее» с ошибками, доказывает ровно ничего.

---

## 10. Известные ограничения (что проверить перед инцидентом)

| # | Ограничение | Последствие | Как закрыть |
|---|---|---|---|
| 1 | **Медиа не бэкапится** (`BACKUP_MEDIA_ENABLED=false`, restic не настроен) | Потеря сервера = потеря всех оригиналов фото/видео. Невосстановимо | Настроить `BACKUP_RESTIC_REPOSITORY` + `BACKUP_RESTIC_PASSWORD_FILE`, включить таймер |
| 2 | **Секреты не бэкапятся** (таймер `arv-backup-secrets` не установлен) | `.env` существует в одном экземпляре на сервере. Потеря = нерасшифровываемые OAuth-токены | Держать `.env` в менеджере паролей **и** включить таймер |
| 3 | **Дампы не шифруются** (`BACKUP_AGE_RECIPIENT` пуст) | Дамп с `users.hashed_password` лежит в облаке открытым текстом | Задать `BACKUP_AGE_RECIPIENT`, ключ хранить вне сервера |
| 4 | **systemd-таймеры бэкапа не установлены** | Работает только планировщик внутри приложения: упало приложение — остановились и бэкапы | `deploy/systemd/arv-backup-*` → `/etc/systemd/system/`, `enable --now` |
| 5 | **Второго off-site нет** (`BACKUP_SECONDARY_RCLONE_REMOTE` пуст) | Бэкап лежит на том же Yandex, что и прод-медиа. Один аккаунт = общая точка отказа | Настроить rclone-remote другого провайдера (B2/Selectel) |
| 6 | **Restore drill не по расписанию** | «Бэкап, который не восстанавливали, — гипотеза» | Установить `arv-backup-drill.timer` (1-е число 06:00) |
| 7 | **Автоматический restore требует живую БД** | При полной потере БД — только ручной путь (§7) | Дублировать токен Yandex/доступ к папке бэкапов в офсайт-хранилище оператора |
| 8 | `backup_company_id=4` — единственный получатель | Бэкапы только для VertexART | Осознанное решение, см. §13.2 п.14 основного документа |

Порядок закрытия по приоритету: **1 → 2 → 4 → 6** (это то, что делает восстановление вообще возможным), затем 3 → 5 (устойчивость), затем 7 → 8.

---

## 11. Шпаргалка: команды

```bash
# --- состояние ---
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; /opt/arv/venv/bin/python -m app.cli.backup status'
systemctl list-timers 'arv-backup-*' --all

# --- проверки (безопасные) ---
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; /opt/arv/venv/bin/python -m app.cli.backup verify --limit 3'
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; /opt/arv/venv/bin/python -m app.cli.backup drill --backup-type db'

# --- восстановление в отдельную БД (опасно: пишет данные) ---
sudo -u postgres createdb -O vertex_ar vertex_ar_recovered
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; /opt/arv/venv/bin/python -m app.cli.backup restore 136 --target-db vertex_ar_recovered'
# или интерактивно:
sudo -u arv /opt/arv/app/deploy/backup/restore.sh --backup-id 136 --target-db vertex_ar_recovered
# список последних бэкапов:
sudo -u arv /opt/arv/app/deploy/backup/restore.sh --list

# --- ручной путь (когда БД потеряна) ---
sudo -u postgres pg_restore -j4 --exit-on-error -d vertex_ar /tmp/restore.dump
pg_restore --list /tmp/restore.dump | head -50      # посмотреть оглавление без восстановления

# --- диагностика ---
sudo -n journalctl -u arv.service -p warning -n 50 --no-pager
sudo -u postgres psql -d vertex_ar -c "SELECT * FROM backup_history ORDER BY id DESC LIMIT 5"
df -h /var/backups /opt/arv
```

**Значения по умолчанию, о которые спотыкаются:**
`BACKUP_STAGING_DIR=/var/backups/arv` · `BACKUP_RESTORE_JOBS=4` · `BACKUP_DRILL_DB_PREFIX=arv_drill` · `BACKUP_MAX_AGE_HOURS=26` · таймауты: decrypt/restore 3600 с, `--list` 600 с · артефакт: `backup_<ts>.sql.gz` (внутри — custom-format `-Fc`, восстанавливается **только** через `pg_restore`) · `--trigger` — **top-level** аргумент CLI, до подкоманды.
