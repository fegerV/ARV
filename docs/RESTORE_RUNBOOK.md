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
5. **Порядок обязателен: секреты → БД → медиа.** OAuth-токены в дампе зашифрованы ключом, производным от `SECRET_KEY`; без `.env` восстановленная БД содержит нерасшифровываемые токены.
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

### Состояние прода, проверено на хосте 2026-09-15

| Факт | Значение |
|---|---|
| Последний успешный бэкап | **id 139**, 68 462 Б, `backups/backup_20260915_215426.sql.gz` |
| Восстановление проверено | **да** — `restore 139 --target-db vertex_ar_recovered` → `ok: True`, 15 таблиц, счётчики совпали с продом |
| `verification_status` | **`ok`** (записано 2026-09-15 22:29:47) |
| `restore_test_status` | **`ok`** (drill пройден 2026-09-15 22:30:15) |
| Шифрование дампа | `encrypted = f` — **не шифруется** |
| `media` / `secrets` бэкапы | `never run` |
| Размер БД / медиа | 10 МБ / 217 МБ (`/opt/arv/storage`) |
| Свободно на диске | 19 ГБ — запаса достаточно |
| Роль `vertex_ar` | `rolcreatedb = t` (выдано 2026-09-15 → drill работает) |
| Владельцы объектов в `public` | все 15 таблиц / 13 последовательностей / 48 индексов → `vertex_ar` (нормализовано 2026-09-15) |
| `pg_restore` | 16.11 (Ubuntu) = версия сервера → совместимо |
| `age` / `restic` / `rclone` | **не установлены** — apt-лок держит зависший `apt-get update` (см. ниже) |
| `/var/backups/arv` | **создан** (0700, `arv:arv`) |
| systemd-таймеры | `arv-backup-verify.timer` (вс 05:00), `arv-backup-drill.timer` (1-е 06:00) — **установлены и проверены боевым запуском** |

> ⚠️ **apt на сервере заблокирован ~200 дней.** Лок-файл `/var/lib/apt/lists/lock` держит процесс `apt-get -qq -y update` (PID 2865430), запущенный ~200 суток назад и висящий до сих пор. Следствия: `apt-get update/install` не работают, индекс пакетов устарел (пакеты отдают 404), **обновления безопасности ОС не приходят**. `age`, `restic`, `rclone` поставить из репозитория нельзя, пока это не устранено. Лечение: завершить зависший процесс (`sudo kill 2865430`), затем `sudo apt-get update`. Решение за оператором — это чужая сессия root.

> ⚠️ **Скрипты в репозитории лежали без флага выполнения** (`100644`), поэтому systemd не мог их запустить: `status=203/EXEC` и пустой журнал. Исправлено коммитом `5e98147` (`git update-index --chmod=+x`). Инструкция по установке предполагает `install -m 0755`, но это копирование поверх того же пути — флаг обязан быть в репозитории. Если разворачиваете на новом хосте и юниты падают с `203/EXEC` — проверить `ls -l deploy/backup/*.sh`.

> **Что здесь было сломано и исправлено (2026-09-15).** Бэкап исправно создавался и выгружался на Яндекс Диск, но **вернуть его было нельзя** — падали все три уровня: `verify`, `drill`, `restore`. Две независимые причины, обе исправлены и проверены на проде:
>
> | Коммит | Причина | Симптом | Проверка |
> |---|---|---|---|
> | `6f60cc5` | `download_backup()` вызывал `provider.save_file()` — метод **загрузки** (открывает первый аргумент как локальный файл) вместо `get_file()` | `FileNotFoundError: 'backups/backup_....sql.gz'` → `verify`/`drill`/`restore` падали всегда | `verify` → `checksum=ok toc=ok entries=150` |
> | `2b23b77` | `pg_restore` вызывался без `--no-owner`; дамп записывает владельцем `ai_jobs` роль `postgres`, а приложение подключается как `vertex_ar` | `ERROR: must be able to SET ROLE "postgres"`, и из-за `--exit-on-error` восстановление откатывалось целиком — в целевой БД оставалась 1 таблица | `restore 139` → `ok: True`, 15 таблиц |
>
> Оба дефекта жили незамеченными, потому что ни один бэкап никогда не проверялся: `verification_status` и `restore_test_status` были NULL у всех строк, а таймеры `verify`/`drill` не установлены. **Вывод для эксплуатации: непроверенный бэкап — это гипотеза, а не бэкап.**

**Проверенный результат полного восстановления** (`restore 139` в отдельную БД, прод не тронут):

```
tables           15 = 15        companies  4 = 4
projects          5 = 5         ar_content 61 = 61
videos           71 = 71        users       2 = 2
alembic: 20260914_1400_backup_verification (совпадает)
orphan_ar_content: 0            null_company_id: 0
```

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

На проде право **выдано 2026-09-15** (`rolcreatedb = t`), `drill` проходит. Если разворачиваете на новом хосте и `drill` падает с `permission denied to create database` — дать право:
`sudo -u postgres psql -c 'ALTER ROLE vertex_ar CREATEDB'` (drill создаёт и дропает одноразовую БД).

Альтернатива без выдачи прав: создавать целевую БД вручную от `postgres` — для `restore` этого достаточно (`CREATEDB` нужен только автоматическому `drill`).

### 2.4 Конфигурация бэкапа (без раскрытия секретов)

```bash
sudo -n grep -E '^(BACKUP_|DATABASE_URL|TOKEN_ENCRYPTION_KEY|SECRET_KEY|STORAGE_BASE_PATH)' \
  /opt/arv/app/.env | sed -E 's/=(.*)$/=<set>/'
```

Что смотреть: `BACKUP_AGE_RECIPIENT` (пусто → дампы не шифруются), `BACKUP_AGE_IDENTITY_FILE` (нужен только для расшифровки), `BACKUP_MEDIA_ENABLED`, `BACKUP_RESTIC_REPOSITORY`, `BACKUP_SECONDARY_RCLONE_REMOTE` (пусто → второго off-site нет), `STORAGE_BASE_PATH`.

На проде на 2026-09-15 ни одна из `BACKUP_*` переменных не задана; присутствуют только `ENVIRONMENT`, `DATABASE_URL`, `SECRET_KEY`, `STORAGE_BASE_PATH`, `REDIS_URL`. `TOKEN_ENCRYPTION_KEY` отсутствует — ключ шифрования токенов выводится из `SECRET_KEY` (см. §7 шаг 1). **`SECRET_KEY` — самый критичный секрет на этом хосте.**

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
backup 139 (db): checksum=ok toc=ok entries=150
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

Ожидаемо: `drill on backup 139: {'ok': True, 'tables_restored': 15, 'duration_seconds': N, 'drill_database': 'arv_drill_...'}`

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
  /opt/arv/venv/bin/python -m app.cli.backup restore 139 --target-db vertex_ar_recovered'

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
  /opt/arv/venv/bin/python -m app.cli.backup restore 139 --target-db vertex_ar_recovered'
```

Ожидаемо: `restore: {'ok': True, 'tables_restored': 15, 'target_database': 'vertex_ar_recovered', 'duration_seconds': 1}`

**Почему код передаёт `--no-owner`.** Дамп записывает владельца каждого объекта, и `pg_restore` воспроизводит это как `ALTER ... OWNER TO <роль>`, что требует от восстанавливающей роли права `SET ROLE` на эту роль. На проде `ai_jobs` и его последовательность/индексы были созданы ранней миграцией под `postgres`, а приложение подключается как `vertex_ar` — воспроизведение падало с `ERROR: must be able to SET ROLE "postgres"`, и `--exit-on-error` откатывал восстановление целиком (в целевой БД оставалась 1 таблица вместо 15). Владельцы объектов нормализованы на `vertex_ar` (2026-09-15), а флаг оставлен: он делает восстановление работоспособным и для старых дампов, и при смене роли. Тот же флаг нужен в ручных командах `pg_restore` (§7).

Через хост-скрипт (интерактивный, с предупреждениями и подтверждением вводом имени БД):

```bash
sudo -u arv /opt/arv/app/deploy/backup/restore.sh --backup-id 139 --target-db vertex_ar_recovered
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
   Нужны как минимум: DATABASE_URL, SECRET_KEY, STORAGE_BASE_PATH.
   ⚠️ Критичен именно SECRET_KEY. Ключ шифрования OAuth-токенов выводится как
      `TOKEN_ENCRYPTION_KEY or SECRET_KEY` (app/core/config.py::token_encryption_secret),
      а на проде TOKEN_ENCRYPTION_KEY НЕ задан — значит ключ целиком определяется
      SECRET_KEY. Тот же SECRET_KEY подписывает JWT и подписи медиа-URL.
      Потеря/замена SECRET_KEY ⇒ нерасшифровываемые токены (все компании
      переподключают Яндекс Диск вручную) + разлогин всех сессий.

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
   gunzip -c backup_20260915_215426.sql.gz > /tmp/restore.dump
   sudo -u postgres pg_restore -j4 --no-owner --exit-on-error -d vertex_ar /tmp/restore.dump
   ⚠️ --no-owner ОБЯЗАТЕЛЕН, если восстанавливаете не под суперпользователем
      (см. §6.2). Без него pg_restore упадёт на
      `ALTER TABLE public.ai_jobs OWNER TO postgres` →
      `ERROR: must be able to SET ROLE "postgres"`, а --exit-on-error
      откатит восстановление целиком: в БД останется одна таблица.
      От владельца объектов зависит также, сможет ли приложение писать
      в восстановленную БД.

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

- **Секреты первыми.** Дамп БД не самодостаточен: `companies.yandex_disk_token` и `storage_connections` зашифрованы ключом Fernet, производным от `SECRET_KEY` (см. §7 шаг 1), JWT подписываются им же. Восстановили БД без `.env` — получили «мёртвые» токены: пользователи видят подключённые хранилища, но они не работают. Проверка — §6.5, последний пункт.
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

## 10. Известные ограничения (проверено на хосте 2026-09-15)

| # | Ограничение | Статус | Последствие | Как закрыть |
|---|---|---|---|---|
| 1 | **Медиа не бэкапится** — `media: never run`, `restic` не установлен, `BACKUP_MEDIA_ENABLED` не задан | ❌ открыто | Потеря сервера = потеря всех оригиналов фото/видео (217 МБ). Невосстановимо | Установить `restic` (см. блокер apt), задать `BACKUP_RESTIC_REPOSITORY` + `BACKUP_RESTIC_PASSWORD_FILE`, включить таймер |
| 2 | **Секреты не бэкапятся** — `secrets: never run`, `age` не установлен | ❌ открыто | `.env` существует в одном экземпляре на сервере. Потеря `SECRET_KEY` = нерасшифровываемые OAuth-токены + разлогин всех сессий | Хранить `.env` в менеджере паролей; включить таймер **только** вместе с шифрованием (иначе `.env` уедет в облако открытым текстом) |
| 3 | **Дампы не шифруются** — `encrypted = f` у всех строк | ❌ открыто | Дамп с `users.hashed_password` лежит в облаке открытым текстом | Задать `BACKUP_AGE_RECIPIENT`; приватный ключ — **вне** сервера, до включения шифрования |
| 4 | **Таймер `arv-backup-db` не установлен** | ⏸ решение за оператором | Работает только планировщик внутри приложения: упало приложение — остановились и бэкапы. Но включить таймер при работающем APScheduler = **два дампа в сутки** | Либо оставить APScheduler, либо включить таймер и выключить `backup_enabled` в `system_settings` |
| 5 | ~~Проверки не автоматизированы~~ | ✅ **закрыто** | — | `arv-backup-verify.timer` (вс 05:00) и `arv-backup-drill.timer` (1-е 06:00) установлены и проверены боевым запуском |
| 6 | ~~`drill` не может создаться БД~~ | ✅ **закрыто** | — | `ALTER ROLE vertex_ar CREATEDB` выдано 2026-09-15; drill проходит |
| 7 | **Второго off-site нет** — `BACKUP_SECONDARY_RCLONE_REMOTE` не задан | ❌ открыто | Бэкап лежит на том же Яндекс Диске, что и прод-медиа. Один аккаунт = общая точка отказа | Настроить rclone-remote другого провайдера (B2/Selectel) |
| 8 | ~~Staging-каталог не создан~~ | ✅ **закрыто** | — | `/var/backups/arv` создан (0700, `arv:arv`) |
| 9 | **Автоматический restore требует живую БД** — `download_backup` читает `companies` из БД | ⚠️ by design | При полной потере БД — только ручной путь (§7) | Дублировать доступ к папке бэкапов и `.env` в офсайт-хранилище оператора |
| 10 | **apt заблокирован ~200 дней** — зависший `apt-get update` (PID 2865430) держит лок | ❌ открыто | Не ставятся пакеты, **не приходят обновления безопасности ОС** | `sudo kill 2865430`, затем `apt-get update` — решение за оператором |
| 11 | `backup_company_id=4` — единственный получатель | ⚠️ by design | Бэкапы только для VertexART | См. §13.2 п.14 основного документа |

**Итог.** Бэкап БД теперь **проверен и восстанавливаем**: `verify` и `drill` автоматизированы, полное восстановление пройдено end-to-end (§1). Осталось то, что требует решений оператора: медиа и секреты (1, 2, 3), устойчивость (7) и заблокированный apt (10).

Порядок закрытия: **10** (без apt не поставить `restic`/`age`/`rclone` — он блокирует пункты 1, 2, 3, 7) → **1 → 2 → 3** → **7** → **4**. Обратите внимание на связку 2+3: включать бэкап секретов **до** шифрования нельзя — `.env` с `SECRET_KEY` уедет на Яндекс Диск открытым текстом.

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
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; /opt/arv/venv/bin/python -m app.cli.backup restore 139 --target-db vertex_ar_recovered'
# или интерактивно:
sudo -u arv /opt/arv/app/deploy/backup/restore.sh --backup-id 139 --target-db vertex_ar_recovered
# список последних бэкапов:
sudo -u arv /opt/arv/app/deploy/backup/restore.sh --list

# --- ручной путь (когда БД потеряна) ---
sudo -u postgres pg_restore -j4 --no-owner --exit-on-error -d vertex_ar /tmp/restore.dump
pg_restore --list /tmp/restore.dump | head -50      # посмотреть оглавление без восстановления

# --- диагностика ---
sudo -n journalctl -u arv.service -p warning -n 50 --no-pager
sudo -u postgres psql -d vertex_ar -c "SELECT * FROM backup_history ORDER BY id DESC LIMIT 5"
df -h /var/backups /opt/arv

# --- уже сделано на проде (2026-09-15) ---
sudo install -d -m 0700 -o arv -g arv /var/backups/arv
sudo -u postgres psql -c 'ALTER ROLE vertex_ar CREATEDB'
sudo install -m 0644 /opt/arv/app/deploy/systemd/arv-backup-* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now arv-backup-verify.timer arv-backup-drill.timer
sudo chmod 0755 /opt/arv/app/deploy/backup/*.sh     # без этого юниты падают с 203/EXEC
systemctl list-timers 'arv-backup-*'

# --- ещё не сделано: apt заблокирован зависшим update (~200 дней) ---
sudo fuser -v /var/lib/apt/lists/lock       # покажет PID 2865430
sudo kill 2865430 && sudo apt-get update    # решение за оператором
sudo apt-get install -y age restic rclone   # после разблокировки

# проверить юниты боевым запуском (безопасно, прод не трогают)
sudo systemctl start arv-backup-verify.service && sudo journalctl -u arv-backup-verify -n 20 --no-pager
sudo systemctl start arv-backup-drill.service  && sudo journalctl -u arv-backup-drill  -n 20 --no-pager
```

**Значения по умолчанию, о которые спотыкаются:**
`BACKUP_STAGING_DIR=/var/backups/arv` · `BACKUP_RESTORE_JOBS=4` · `BACKUP_DRILL_DB_PREFIX=arv_drill` · `BACKUP_MAX_AGE_HOURS=26` · таймауты: decrypt/restore 3600 с, `--list` 600 с · артефакт: `backup_<ts>.sql.gz` (внутри — custom-format `-Fc`, восстанавливается **только** через `pg_restore`) · `--trigger` — **top-level** аргумент CLI, до подкоманды.
