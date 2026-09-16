# Runbook: восстановление системы из бэкапа

**Проект:** V-Portal / ARV · **Прод:** `ar.neuroimagen.ru` (`192.144.12.68`, пользователь `aruser`)
**Пути:** приложение `/opt/arv/app`, venv `/opt/arv/venv`, медиа `/opt/arv/storage`, staging `/var/backups/arv`
**БД:** PostgreSQL 16, БД `vertex_ar`, роль `vertex_ar`, `127.0.0.1:5432`
**Связанный документ:** `docs/BACKUP_AND_RECOVERY.md` (§7 — проверка целостности, §10 — концептуальный порядок восстановления). Этот файл — операционная, привязанная к хосту версия §10.

---

## 0. TL;DR — что нужно знать до начала

1. **Восстанавливаются все три класса данных:** БД (ежедневно), медиа-оригиналы (ежедневно, `restic`) и секреты/конфиг (еженедельно, `tar`+`age`). См. §1.
2. **Три уровня проверки, от дешёвого к опасному:** `verify` → `drill` → `restore`. Первые два прод **не трогают**. Третий пишет в БД.
3. **Код отказывается восстанавливать поверх продовой БД.** `restore_to()` сравнивает имя целевой БД с именем из `DATABASE_URL` и падает с `RuntimeError`, если они совпадают. Восстановление идёт **всегда в отдельную БД**, а переключение прода на неё — отдельный осознанный шаг (§6).
4. **Целевую БД нужно создать заранее.** `restore_to()` её **не создаёт** (в отличие от drill). Создание — на операторе.
5. **Порядок обязателен: секреты → БД → медиа.** OAuth-токены в дампе зашифрованы ключом, производным от `SECRET_KEY`; без `.env` восстановленная БД содержит нерасшифровываемые токены.
6. ⚠️ **Главное ограничение:** штатный `restore` скачивает дамп с Yandex Disk, используя токен из **самой БД** (`companies.yandex_disk_token` → расшифровка ключом из `.env`). Значит при **полной потере БД** автоматический путь не работает — нужен ручной (§7).
7. **Ключ шифрования бэкапов (`age`) на прод-сервере не хранится — намеренно.** Дампы и архив секретов шифруются (X25519), приватный ключ лежит **вне** сервера (docs/BACKUP_AND_RECOVERY.md §"Encryption": получив root на `arv`, злоумышленник не должен получить и ключи). Следствия, которые нужно знать заранее:
   - без ключа зашифрованный артефакт не открыть — при восстановлении ключ обязателен (§3, §6, §7);
   - автоматические `verify` и `drill` на хосте **не могут** открыть архив и честно сообщают `toc=skipped` / `verification=no_identity`, а не ложный провал. Это сделано специально: постоянно красный алерт перестают читать;
   - значит `drill` в автоматическом режиме **не доказывает** пригодность зашифрованного бэкапа. Раз в месяц его надо прогонять вручную с примонтированным ключом (§4).
8. **`SECRET_KEY` — самый критичный секрет на хосте.** `TOKEN_ENCRYPTION_KEY` на проде не задан, поэтому ключ шифрования OAuth-токенов выводится из `SECRET_KEY`; им же подписываются JWT и медиа-URL. Он лежит в архиве секретов (§1, A3).
9. **Глубина восстановления задаётся GFS 7/4/12/3, а не настройками в админке.** `backup_max_copies`/`backup_retention_days` в UI **не действуют** (§1.1). На 2026-09-16 по БД доступно ~7 точек, по медиа и секретам — по одной. Перед восстановлением брать актуальный список (§1.1), а не id из примеров: **id подвижны**, ротация удаляет и артефакт, и строку истории.
10. **Восстановление — одна команда** (§6.0): `recover.sh --backup-id N --target-db X` восстанавливает, `--cutover` переключает прод с автооткатом при неудаче. Ручные шаги остались ниже как запасной путь. Артефакт можно **скачать вручную** — из админки (страница «Бэкапы», только супер-админ) или `backup download` (§3.1), не заходя в веб-интерфейс Яндекс Диска.

---

## 1. Что реально можно восстановить сегодня

| Класс | Данные | Бэкапится? | Как восстановить |
|---|---|---|---|
| **A1** | PostgreSQL `vertex_ar` | ✅ **Да** — ежедневно 03:00 (APScheduler внутри приложения), `company_id=4`. Дамп шифруется (`age`). ⚠️ `arv-backup-db.timer` **не установлен** — бэкап делает планировщик внутри приложения; таймер теперь безопасно добавить (общий `flock`, §10 п. 4) | `python -m app.cli.backup restore <id> --target-db <db>` (нужен ключ — §3) |
| **A2** | Оригиналы медиа `/opt/arv/storage` | ✅ **Да** — ежедневно 03:30, `arv-backup-media.timer`, restic-снапшоты (дедупликация + шифрование на клиенте) | `restic restore <snapshot> --target /opt/arv/storage` (§7 шаг 7) |
| **A3** | `.env`, `/etc/letsencrypt` (частично), `deploy/` | ✅ **Да** — еженедельно вс 04:00, `arv-backup-secrets.timer`, `tar` + `age` | Расшифровать архив и распаковать (§7 шаг 1) |
| **B** | Производные медиа (`marker.mind`, `qr_code.png`, thumbnails) | ❌ Нет | Регенерируются из A2 |
| **C** | Redis (JWT-blacklist, OAuth-state, rate-limit) | Не нужно | Эфемерны, пересоздаются сами |
| **D** | Код | ✅ git `github.com/fegerV/ARV` | `git checkout <commit>` |

**Практический вывод.** Все три класса восстановимы, но с оговорками, которые надо знать до инцидента:

- **Ключ `age` обязателен.** Без него ни дамп, ни архив секретов не открыть. Хранить вне сервера, дублировать у ответственного.
- **TLS-сертификаты в архив не попадают.** `/etc/letsencrypt/live`, `archive`, `accounts`, `keys`, `csr` — режим `0700 root`, сервисный аккаунт `arv` их прочитать не может (см. §10). В архиве только `cli.ini` и `renewal/`. Сертификат **перевыпускается** `certbot`; чтобы забрать и его, запускать `backup-secrets.sh` от root.
- **Медиа-снапшоты лежат на том же диске, что и прод.** `/var/backups/arv/restic` и `/opt/arv/storage` — один и тот же `/dev/vda2`. От потери диска это не спасает; нужен второй off-site (§10).

### Состояние прода, проверено на хосте 2026-09-16

> ⚠️ **id бэкапов подвижны.** Ротация удаляет не только артефакт, но и строку в `backup_history` (§1.1). Любой конкретный id из таблицы ниже — снимок на дату, а не постоянная ссылка. Перед восстановлением **всегда** брать актуальный список: `deploy/backup/restore.sh --list`.

| Факт | Значение |
|---|---|
| БД | backup **148**, `encrypted=t`, 69 129 Б, `backups/backup_20260915_233642.sql.gz.age` |
| Медиа | backup **141**, `encrypted=t`, 225 702 549 Б, снапшот restic, репозиторий 195 МБ при 217 МБ исходников |
| Секреты | backup **144**, `encrypted=t`, 11 741 Б, `target=local` (второго off-site нет) |
| Восстановление БД проверено | **да** — `restore 143 --target-db vertex_ar_enc_probe` → `ok: True`, 15 таблиц; счётчики и `alembic_version` совпали с продом; прод не тронут, временная БД удалена. ⚠️ Артефакт 143 к 2026-09-16 уже удалён ротацией — доказательство относится к *методу*, а не к конкретному файлу; метод воспроизводится на любом текущем id |
| Расшифровка архива секретов проверена | **да** — `age --decrypt` ключом оператора, внутри `app/.env` (с `SECRET_KEY`), `etc/letsencrypt/renewal/…`, `deploy/**` |
| `verification_status` (db) | **`ok`**; медиа — **`ok`** (`restic check --read-data-subset=5%`) |
| `restore_test_status` | `NULL` — drill на зашифрованном бэкапе автоматически не проходит, нужен ручной прогон с ключом (§4) |
| Шифрование дампа | `encrypted = t` (`BACKUP_AGE_RECIPIENT` задан) |
| Размер БД / медиа | 10 МБ / 217 МБ (`/opt/arv/storage`) |
| Свободно на диске | 19 ГБ |
| Роль `vertex_ar` | `rolcreatedb = t` |
| Владельцы объектов в `public` | все → `vertex_ar` (нормализовано 2026-09-15) |
| `pg_restore` / `age` / `restic` / `rclone` | 16.11 / 1.1.1 / 0.16.4 / 1.60.1 — установлены |
| `/var/backups/arv` | создан (0700, `arv:arv`); restic-репозиторий внутри |
| systemd-таймеры | `arv-backup-media.timer` (ежедневно 03:30), `arv-backup-secrets.timer` (вс 04:00), `arv-backup-verify.timer` (вс 05:00), `arv-backup-drill.timer` (1-е 06:00) — установлены и проверены боевым запуском |
| `arv-backup-db.timer` | **не установлен** — дамп делает APScheduler внутри приложения. С 2026-09-16 таймер можно добавить без риска дублей: оба берут один `flock` (§10 п. 4, 18) |
| Второй off-site | **механизм проверен, получателя нет** — см. §1.1 и §10 п. 7 |

> ✅ **apt разблокирован (2026-09-16).** До этого лок-файл `/var/lib/apt/lists/lock` ~200 дней держал зависший `apt-get -qq -y update` (`apt-daily.service` в состоянии `activating` с 2026-02-28), из-за чего `apt-get install` не работал и **обновления безопасности ОС не приходили**. Устранено: `systemctl stop apt-daily.service` (таймер перезапустил его корректно) → `systemctl reset-failed` → `apt-get update`. После этого установлены `age 1.1.1`, `restic 0.16.4`, `rclone 1.60.1`.
>
> ⏸ **Остаточный риск:** после разблокировки apt видит **284 обновляемых пакета**, включая обновления безопасности за ~200 дней. Они **сознательно не применялись**: массовый `apt-get upgrade` на живом проде — отдельное окно обслуживания с планом отката, а не побочный эффект настройки бэкапов. Это задача оператора.

> ⚠️ **Скрипты в репозитории лежали без флага выполнения** (`100644`), поэтому systemd не мог их запустить: `status=203/EXEC` и пустой журнал. Исправлено коммитом `5e98147` (`git update-index --chmod=+x`). Инструкция по установке предполагает `install -m 0755`, но это копирование поверх того же пути — флаг обязан быть в репозитории. Если разворачиваете на новом хосте и юниты падают с `203/EXEC` — проверить `ls -l deploy/backup/*.sh`.

> **Что здесь было сломано и исправлено (2026-09-15/16).** Бэкап исправно создавался и выгружался на Яндекс Диск, но **вернуть его было нельзя** — падали все три уровня: `verify`, `drill`, `restore`. При включении медиа, секретов и шифрования вскрылись ещё семь дефектов, каждый из которых ломал восстановление или тихо ослаблял защиту. Все исправлены и проверены на проде:
>
> | Коммит | Причина | Симптом | Проверка |
> |---|---|---|---|
> | `6f60cc5` | `download_backup()` вызывал `provider.save_file()` — метод **загрузки** (открывает первый аргумент как локальный файл) вместо `get_file()` | `FileNotFoundError: 'backups/backup_....sql.gz'` → `verify`/`drill`/`restore` падали всегда | `verify` → `checksum=ok toc=ok entries=150` |
> | `2b23b77` | `pg_restore` вызывался без `--no-owner`; дамп записывает владельцем `ai_jobs` роль `postgres`, а приложение подключается как `vertex_ar` | `ERROR: must be able to SET ROLE "postgres"`, и из-за `--exit-on-error` восстановление откатывалось целиком | `restore 139` → `ok: True`, 15 таблиц |
> | `99f17d3` | `verify` не фильтровал по типу бэкапа: медиа-строки (без `yd_path` и `checksum`) попадали в проверки `pg_restore`; зашифрованный артефакт без ключа давал ложный провал; `restic check` не вызывался ниоткуда | еженедельный `verify` красный навсегда; медиа-бэкапы никогда не проверялись | `verify` → `toc=skipped`, rc=0; `verify-media` → ok |
> | `99f17d3` | `MediaBackupService.run_backup()` читал свою строку **после** `finally`, который закрывал сессию | `RuntimeError: greenlet is being finalized` + SAWarning в журнале каждого запуска | юнит-тесты на владеемую сессию |
> | `6ec06bc` | `cmd_db` передавал `company_id=None`, а дамп уходит через Яндекс Диск **компании** | `Yandex Disk provider not available for company_id=None` → `arv-backup-db.timer` был нерабочим by design | `backup 143` → `encrypted=True`, company_id=4 |
> | `40b2ba4` | `tarfile.add('/etc/letsencrypt')` рекурсивно заходил в `0700 root` каталоги; архив создавался с umask (0644) и содержал `.env`; при падении до шифрования plaintext-архив оставался на диске | `PermissionError: '/etc/letsencrypt/accounts'`; **на хосте остался world-readable `secrets_*.tar.gz` с `SECRET_KEY`** | архив `-rw-------`, plaintext не остаётся, `age --decrypt` проходит |
> | `1b83ed9` | `cmd_secrets` не писал строку в `backup_history`; `status` применял суточный лимит устаревания к недельной задаче | `secrets: never run` навсегда; ложный `STALE` 6 дней из 7 | `status` → `secrets: status=success (limit 192h)`, rc=0 |
>
> Оба первых дефекта жили незамеченными, потому что ни один бэкап никогда не проверялся: `verification_status` и `restore_test_status` были NULL у всех строк, а таймеры `verify`/`drill` не установлены. **Вывод для эксплуатации: непроверенный бэкап — это гипотеза, а не бэкап.**

**Проверенный результат полного восстановления** (`restore 143` в отдельную БД, прод не тронут):

```
tables           15 = 15        companies  4 = 4
projects          5 = 5         ar_content 61 = 61
videos           71 = 71        users       2 = 2
alembic: 20260914_1400_backup_verification (совпадает)
orphan_ar_content: 0            null_company_id: 0
```

### 1.1 Сколько точек восстановления есть на самом деле (ротация)

На вопрос «на какой момент я могу откатиться» отвечает **не** то, что показано в админке.

**Что применяется фактически.** Ротация работает по **GFS-лестнице: 7 ежедневных / 4 недельных / 12 месячных / 3 годовых** (`app/services/backup_rotation.py`). Хранится самый новый артефакт каждого из N последних дней / ISO-недель / месяцев / лет.

**Что в админке показано, но не работает.** В `system_settings` прод лежат `backup_max_copies=30` и `backup_retention_days=30`, и в UI они выглядят действующими. **Они игнорируются.** `BackupService._gfs_limits()` отступает на легаси-правило только если все четыре GFS-поля равны `None` — а схема `BackupSettings` объявляет их как `int = 7/4/12/3`, поэтому `None` не бывает никогда, и легаси-ветка недостижима. Проверено на хосте: в БД ключей `backup_keep_*` нет, значит подставляются дефолты 7/4/12/3, и ротация идёт по GFS.

> ⚠️ **Практическое следствие:** оператор, выставивший в админке «хранить 30 копий», получит 7 ежедневных. Планируя окно хранения — считайте по GFS, а не по UI.
>
> **Как изменить окно.** Штатного способа нет:
> - `backup_max_copies` / `backup_retention_days` в UI — **мертвы** (см. выше);
> - `backup_keep_daily/weekly/monthly/yearly` в схему заведены, но **в UI и API не выводятся** (проверено: `grep backup_keep app/api/ templates/` — пусто), т.е. через интерфейс их не задать;
> - `BACKUP_KEEP_*` в `.env` читаются только как fallback при `value is None`, а значение из БД никогда не `None` → **тоже не действуют**.
>
> Единственный рабочий путь — записать ключи `backup_keep_*` прямо в `system_settings` (тогда `settings_dict.get()` их вернёт, и `_gfs_limits` их подхватит). Это изменение поведения хранения на проде — согласовать с оператором, а не делать «попутно».

**Ротация удаляет и строку истории.** `_rotate_backups()` вызывает `session.delete(record)` (backup_service.py:743) — вместе с артефактом исчезает и запись в `backup_history`. Поэтому `backup_history` перечисляет только **выжившие** бэкапы: по ней нельзя узнать, что вообще было и когда. Это нормально для метаданных об удалённом файле, но означает, что «список бэкапов за всё время» в системе отсутствует.

**Сколько есть сейчас** (2026-09-16, `status='success'`):

| Тип | Успешных строк | Диапазон |
|---|---|---|
| db | 7 | 2026-08-21 … 2026-09-15 |
| media | 1 | 2026-09-15 |
| secrets | 1 | 2026-09-15 |

То есть **по БД глубина уже ~7 дней**, по медиа и секретам — **пока одна точка**. Медиа живёт под своим окном `restic forget` (см. §7 шаг 7), секреты — недельная задача без настроенной ротации: старые архивы накапливаются в `/var/backups/arv` и их надо чистить вручную (архив 11 КБ, но это копия `SECRET_KEY`).

**Проверить актуальный список перед восстановлением:**

```bash
sudo -u arv /opt/arv/app/deploy/backup/restore.sh --list
sudo -u postgres psql -d vertex_ar -tAc \
  "SELECT id, backup_type, to_char(started_at,'YYYY-MM-DD HH24:MI') , size_bytes, encrypted
   FROM backup_history WHERE status='success' ORDER BY id DESC"
```

### 1.2 Второй off-site: механизм проверен

`BACKUP_SECONDARY_RCLONE_REMOTE` (пусто на проде) включает вторую независимую копию через `rclone copyto` в `BackupService._copy_to_secondary()`. **Механизм проверен на хосте 2026-09-16 боевым прогоном** с получателем, указывающим на локальный каталог: бэкап получил `target=primary+secondary`, артефакт лёг по второму пути байт-в-байт (69 129 Б), `rclone` отработал. Тестовый каталог удалён, метаданные строки приведены к реальности.

Что это значит: **код второй копии рабочий**, и от оператора требуется только получатель и креды — создать rclone-remote другого провайдера и прописать его в `BACKUP_SECONDARY_RCLONE_REMOTE`. Если вторая копия падает, бэкап **не** становится красным (`rec.status` остаётся `success`, `target=primary`), но инкрементируется отдельный счётчик `record_failure(backup_type, "secondary")` — на него и надо ставить алерт (§10 п. 7).

⚠️ Локальный каталог **не** является off-site: он на том же `/dev/vda2`. Проверка выше доказывает механизм, а не решает задачу 3-2-1.

---

## 2. Шаг 0 — проверка готовности (перед любым восстановлением)

Выполнять **от `aruser`**; команды, требующие конфигурации приложения, запускать из-под `arv` с подгруженным `.env`.

### 2.1 Состояние бэкапов и таймеров

```bash
# последний прогон по каждому типу + статус верификации
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup status'

# ⚠️ планировщик внутри приложения реально зарегистрировал задачу?
# init_scheduler() глотает исключения (app/core/scheduler.py), поэтому при сбое
# чтения настроек приложение стартует БЕЗ задачи бэкапа — молча.
sudo -n journalctl -u arv.service --since '-14 days' --no-pager \
  | grep -E 'backup_scheduler_(configured|skipped)|scheduler_(started|init_failed)'
# ожидаемо: backup_scheduler_configured cron='0 3 * * *' company_id=4
#           + scheduler_started
# плохо:    scheduler_init_failed  → бэкапы НЕ идут, хотя приложение работает
#           backup_scheduler_skipped reason=disabled_or_no_company → см. §10 п. 4

# установлены ли systemd-таймеры бэкапа (ожидаемо: media, secrets, verify, drill)
systemctl list-timers 'arv-backup-*' --all
ls -1 /etc/systemd/system/arv-backup-* 2>/dev/null || echo "таймеры не установлены"

# история последних попыток
sudo -u postgres psql -d vertex_ar -tAc "
  SELECT id, backup_type, status, encrypted, size_bytes, yd_path, finished_at
  FROM backup_history ORDER BY id DESC LIMIT 10"

# ⚠️ признак «дублирующегося планировщика» (дефект найден и исправлен 2026-09-16,
# см. §10 п. 18). Больше одной строки db-бэкапа за сутки = дубликаты, которые
# пишут в один и тот же ключ и уничтожают артефакт друг друга.
sudo -u postgres psql -d vertex_ar -tAc "
  SELECT date(started_at) AS day, count(*) AS db_backups
  FROM backup_history WHERE backup_type='db'
  GROUP BY 1 HAVING count(*) > 1 ORDER BY 1 DESC LIMIT 10"
# ожидаемо: пусто

# ✅ здоровая работа защиты: один из воркеров проиграл гонку и пропустил прогон
sudo -n journalctl -u arv.service --since '-14 days' --no-pager \
  | grep -E 'backup_lock_unavailable|another_process_is_running_it'
# ожидаемо: scheduled_backup_skipped reason=another_process_is_running_it
#           (по одной записи на каждый прогон 03:00 — это НОРМА, воркеров два)
# плохо:    backup_lock_unavailable → каталог /var/lock недоступен для arv;
#           бэкап всё равно выполнится (защита намеренно fail-open), но
#           дедупликация не работает — разбираться до следующего прогона
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

Что смотреть: `BACKUP_AGE_RECIPIENT` (задан → дампы шифруются), `BACKUP_AGE_IDENTITY_FILE` (нужен только для расшифровки/verify/drill, на проде **не задан** — ключа на сервере нет), `BACKUP_MEDIA_ENABLED`, `BACKUP_RESTIC_REPOSITORY`, `BACKUP_SECONDARY_RCLONE_REMOTE` (пусто → второго off-site нет), `STORAGE_BASE_PATH`.

На проде на 2026-09-16 заданы:

```
BACKUP_MEDIA_ENABLED=true
BACKUP_RESTIC_REPOSITORY=/var/backups/arv/restic
BACKUP_RESTIC_PASSWORD_FILE=/etc/arv/restic-password
BACKUP_AGE_RECIPIENT=age1…          # публичный ключ, приватного на хосте нет
```

`BACKUP_SECONDARY_RCLONE_REMOTE` пуст → второго off-site нет (§10). `TOKEN_ENCRYPTION_KEY` отсутствует — ключ шифрования токенов выводится из `SECRET_KEY` (§7 шаг 1). **`SECRET_KEY` — самый критичный секрет на этом хосте**, он же лежит в архиве секретов (A3).

### 2.5 Место на диске

```bash
df -h / /var/backups /opt/arv
```

Восстановление требует места под staging-артефакт + распакованный `.dump` + саму БД. Ориентир: **3× размер дампа**.

---

## 3. Сценарий A — «бэкап вообще живой?» (безопасно, ~секунды)

Две независимые проверки: SHA-256 скачанного артефакта против записанного в БД и `pg_restore --list` по распакованному архиву. Прод не затрагивается.

```bash
# 1) база: checksum + оглавление архива
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup verify --limit 3'

# 2) медиа: restic check (перечитывает и перехеширует срез репозитория)
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup verify-media'
```

Ожидаемый вывод без ключа на хосте (обычное состояние прода):

```
backup 148 (db): checksum=ok toc=skipped entries=0
media repository check (read-data-subset=5%): ok
```

Три возможных исхода для `db`:

| Вывод | Что значит | Действие |
|---|---|---|
| `checksum=ok toc=ok` | артефакт цел **и** читается как `pg_dump`-архив | всё хорошо |
| `checksum=ok toc=skipped` | артефакт цел, но **открыть нельзя** — он зашифрован, а ключа на хосте нет (by design) | это **не** ошибка, rc=0. Чтобы всё-таки проверить оглавление, примонтировать ключ и повторить (см. ниже) |
| `checksum=FAIL` | байты не доехали/повреждены на Яндекс Диске | **этот артефакт восстанавливать нельзя**, брать предыдущий успешный id |
| `toc=FAIL` | архив нечитаем как custom-format (обрыв, несовместимая версия `pg_dump`) | то же |

Чтобы получить `toc=ok` на зашифрованном бэкапе, нужно на время проверки примонтировать ключ:

```bash
# ключ должен быть 0600 и принадлежать arv
sudo install -m 0600 -o arv -g arv /путь/к/arv-backup-age.key /tmp/arv-age-id.key
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  BACKUP_AGE_IDENTITY_FILE=/tmp/arv-age-id.key \
  /opt/arv/venv/bin/python -m app.cli.backup verify --limit 1'
sudo shred -u /tmp/arv-age-id.key      # сразу убрать
```

Ожидаемо: `backup 148 (db): checksum=ok toc=ok entries=150`

Результат пишется в `backup_history.verified_at` / `verification_status` (`ok` | `no_identity` | `list_failed` | `checksum_mismatch`).

---

### 3.1 Скачать артефакт вручную (без восстановления)

Иногда нужен сам файл, а не восстановленная БД: унести копию в офсайт, отдать в аудит, восстановить на другой машине. Раньше для этого приходилось заходить в веб-интерфейс Яндекс Диска — то есть в тот самый интерфейс, который недоступен, когда потеряна БД с токеном хранилища.

**Из админки.** Страница «Бэкапы» → иконка скачивания в строке. Доступна только супер-админу (артефакт БД содержит данные всех компаний, архив секретов — `SECRET_KEY`). Отдаётся артефакт **в том виде, в котором он сохранён** — зашифрованным. Это не недоработка: расшифрованный дамп, положенный в загрузки, — это утечка, а зашифрованный бесполезен без ключа, который лежит в другом месте.

**Из CLI** (когда веб недоступен):

```bash
# в текущий каталог
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup download 148 --output /tmp/'

# в конкретный файл
... backup download 148 --output /tmp/backup_148.sql.gz.age

# расшифровать сразу — ТОЛЬКО если ключ примонтирован (см. §3)
... backup download 148 --output /tmp/ --decrypt
```

Что нужно знать:

| Ситуация | Поведение |
|---|---|
| Бэкап `db` | тянется с Яндекс Диска, отдаётся `backup_<ts>.sql.gz.age` |
| Бэкап `secrets` | лежит локально в staging, отдаётся `secrets_<ts>.tar.gz.age`; файл создаётся с правами `0600` |
| Бэкап `media` | **не скачивается**: это снапшот `restic`, а не файл. CLI вернёт код 2 и подскажет `restic restore`, админка покажет подсказку вместо кнопки |
| `--decrypt` без ключа на хосте | код 2 / HTTP 400 с объяснением. **Не** отдаёт зашифрованный файл под именем, будто он расшифрован |

Дальше зашифрованный артефакт открывается там, где лежит приватный ключ:

```bash
age --decrypt --identity /путь/к/arv-backup-age.key -o dump.gz backup_148.sql.gz.age
```

> ⚠️ **Скачанный артефакт — это копия всей базы (или `SECRET_KEY`).** Не оставлять в общих каталогах, не пересылать по открытым каналам, удалять после использования. CLI выставляет `0600`, но за дальнейшую судьбу файла отвечает оператор.

---

## 4. Сценарий B — учебное восстановление (drill, безопасно)

Восстанавливает **последний** бэкап в одноразовую БД `arv_drill_<ts>` на том же кластере, считает таблицы и **дропает её в `finally`** — даже при падении мусор не останется. Это единственная проверка, доказывающая, что бэкап *пригоден*, а не просто существует.

> ⚠️ **Автоматический `drill` на зашифрованном бэкапе не работает.** Ключа на хосте нет by design, поэтому `arv-backup-drill.timer` (1-е число, 06:00) сообщает `skipped` / `no_identity` и **не** трогает метрику drill. Это честный сигнал: «ни один прогон ещё не доказал пригодность бэкапа», а не ложный провал. **Раз в месяц drill нужно прогонять вручную с примонтированным ключом** — иначе единственная проверка, которая реально что-то доказывает, не выполняется вообще.

```bash
# ключ на время прогона
sudo install -m 0600 -o arv -g arv /путь/к/arv-backup-age.key /tmp/arv-age-id.key

sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  BACKUP_AGE_IDENTITY_FILE=/tmp/arv-age-id.key \
  /opt/arv/venv/bin/python -m app.cli.backup drill --backup-type db'

sudo shred -u /tmp/arv-age-id.key
```

Ожидаемо: `drill on backup 148: {'ok': True, 'tables_restored': 15, 'duration_seconds': N, 'drill_database': 'arv_drill_...'}`

Без ключа ожидаемо (и это не ошибка):

```
drill on backup 148: {'ok': False, 'skipped': True, 'reason': 'backup is encrypted and BACKUP_AGE_IDENTITY_FILE is not available on this host; mount the age identity to verify it'}
```

`ok: False` без `skipped` → смотреть `error` в выводе и журнал:
`journalctl -u arv-backup-drill.service -n 100 --no-pager` (если таймер установлен) или stderr ручного запуска.

Проверить, что мусора не осталось: `sudo -u postgres psql -tAc "SELECT datname FROM pg_database WHERE datname LIKE 'arv_drill%'"` — пусто.

> **Эквивалент через хост-скрипт:** `sudo -u arv /opt/arv/app/deploy/backup/restore-drill.sh` (то же самое + `flock` против параллельного запуска).

**Рекомендация: прогнать drill до инцидента.** Восстановление, которое ни разу не репетировали, — это гипотеза.

---

## 5. Сценарий C — частичное восстановление

Прод работает, потерян фрагмент данных. **Прод-БД не трогаем** — восстанавливаем в отдельную БД и забираем из неё нужное.

```bash
# 1. ключ на время восстановления (без него зашифрованный дамп не открыть)
sudo install -m 0600 -o arv -g arv /путь/к/arv-backup-age.key /tmp/arv-age-id.key

# 2. восстановить нужный бэкап — --create-db создаст целевую БД сам
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  BACKUP_AGE_IDENTITY_FILE=/tmp/arv-age-id.key \
  /opt/arv/venv/bin/python -m app.cli.backup restore 148 --target-db vertex_ar_recovered --create-db'

# 3. вытащить нужное и перенести в прод точечно, например:
sudo -u postgres psql -d vertex_ar_recovered -c \
  "COPY (SELECT * FROM ar_content WHERE id = 1234) TO STDOUT WITH CSV HEADER" > /tmp/one_row.csv
# ... вставить в прод явными INSERT'ами, предварительно посмотрев, что именно перезаписывается

# 4. убрать временную БД и ключ, когда они больше не нужны
sudo -u postgres dropdb vertex_ar_recovered
sudo shred -u /tmp/arv-age-id.key
```

`--create-db` появился, чтобы убрать самый частый срыв процедуры: раньше `restore` падал на несуществующей целевой БД, и её приходилось создавать отдельной командой от `postgres`. Без флага поведение прежнее — цель создаёт оператор.

Типовые случаи:

| Что случилось | Действие |
|---|---|
| Удалён один AR-контент | восстановить в `vertex_ar_recovered` → перенести строки `ar_content` / `videos` точечными `INSERT` |
| Ошибочно удалены проекты | то же, но сначала выгрузить список id; либо PITR (§10.2 в основном документе), если WAL включён |
| Испорчен/удалён один файл медиа | **есть чем**: `restic restore <snapshot> --include /VertexAR/<project>/<order> --target /tmp/out` (§7 шаг 7), затем вернуть файл на место и `chown arv:arv`. Снапшоты ежедневные — откат возможен на любой день в пределах GFS-окна |
| Потерян/испорчен `.env` | достать из недельного архива секретов (§7 шаг 1). **Не редактировать вручную**: `SECRET_KEY` не восстановить, а без него OAuth-токены в БД нечитаемы |
| Утёк/сгорел Redis | ничего не делать, `systemctl restart redis` |

---

## 6. Сценарий D — полное восстановление с переключением прод-БД

Самый частый «настоящий» сценарий: текущая БД повреждена или данные испорчены, нужно откатиться на вчерашнее состояние. **Прод останавливать обязательно** — иначе приложение будет писать поверх восстановленного.

### 6.0 Быстрый путь: одна команда

Раньше этот сценарий состоял из семи ручных шагов (создать БД, примонтировать ключ, восстановить, `alembic`, править `.env`, перезапуск, smoke) — и каждый шаг был возможностью ошибиться в самый неподходящий момент. Теперь это одна команда, запускаемая **от `aruser`** (остановка сервиса требует sudo, а `.env` и CLI — пользователя `arv`; скрипт сам переключается между ними):

```bash
# 1. восстановить в отдельную БД и посмотреть, что получилось
sudo -u aruser /opt/arv/app/deploy/backup/recover.sh \
    --backup-id 148 --target-db vertex_ar_recovered

# 2. убедиться, что данные на месте, и переключить прод
sudo -u aruser /opt/arv/app/deploy/backup/recover.sh \
    --cutover --target-db vertex_ar_recovered
```

`--cutover` по шагам: снимает дамп **текущей** БД в staging (даже повреждённая БД — единственная копия того, что случилось после бэкапа) → останавливает `arv.service` → бэкапит `.env` и переписывает `DATABASE_URL` → запускает сервис → smoke-тест → печатает команду отката.

Что скрипт делает намеренно:

- **отказывается** работать, если `--target-db` совпадает с живой БД;
- **отказывается** переключаться на БД, где нет таблиц в схеме `public`;
- при падении `arv.service` после переключения **сам откатывает** `.env` и поднимает сервис;
- требует ввести имя целевой БД руками (кроме `--yes`);
- если не удалось переписать `DATABASE_URL` — возвращает `.env` и стартует сервис обратно.

Коды возврата: `0` успех · `1` упало восстановление · `2` ошибка аргументов · `3` оператор отказался · `4` упал переключение · `77` окружение непригодно (нет sudo).

Ниже — тот же процесс руками, для случая, когда скрипт недоступен или нужен пошаговый контроль.

### 6.1 Сохранить текущее состояние (не пропускать)

```bash
# даже если БД «сломана» — сохранить её как есть, чтобы был путь назад
sudo -u postgres pg_dump -Fc -Z0 vertex_ar > /var/backups/arv/before_restore_$(date -u +%Y%m%d_%H%M%S).dump
sudo -u postgres psql -tAc "SELECT pg_size_pretty(pg_database_size('vertex_ar'))"
```

Если дамп не снимается (БД недоступна) — хотя бы зафиксировать текущий `DATABASE_URL` и не удалять каталог данных до успешной проверки.

### 6.2 Создать целевую БД и восстановить

```bash
# ключ обязателен: дампы шифруются
sudo install -m 0600 -o arv -g arv /путь/к/arv-backup-age.key /tmp/arv-age-id.key

# --create-db создаёт целевую БД (раньше это был отдельный createdb от postgres)
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  BACKUP_AGE_IDENTITY_FILE=/tmp/arv-age-id.key \
  /opt/arv/venv/bin/python -m app.cli.backup restore 148 --target-db vertex_ar_recovered --create-db'

sudo shred -u /tmp/arv-age-id.key
```

Ожидаемо: `restore ok: 15 tables -> vertex_ar_recovered in 1s (database was created)`, после чего CLI сам печатает оставшиеся шаги переключения — чтобы не искать их в ранбуке в момент инцидента.

> `--create-db` идемпотентен: если БД уже есть, она **не** пересоздаётся и не перезаписывается. Если восстановление упало, созданная БД намеренно **не** удаляется — это улика для разбора; убрать её можно явно (`dropdb`).

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

> `alembic upgrade head` нужен **только** если код новее бэкапа. Дамп уже содержит и схему, и строку `alembic_version` — при восстановлении свежего бэкапа на тот же код ревизия совпадает и команда ничего не делает. Проверить: `sudo -u postgres psql -d <db> -tAc "SELECT version_num FROM alembic_version"`.

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
1. Секреты первыми (класс A3). Взять недельный архив секретов и ключ age
   (оба — вне сервера, в менеджере паролей оператора):

       age --decrypt --identity /путь/к/arv-backup-age.key \
           --output /tmp/secrets.tar.gz /путь/к/secrets_<ts>.tar.gz.age
       tar xzf /tmp/secrets.tar.gz -C /            # кладёт app/.env и etc/letsencrypt/…
       # .env должен оказаться в /opt/arv/app/.env, права 0600, владелец arv:arv
       sudo install -m 0600 -o arv -g arv app/.env /opt/arv/app/.env

   Нужны как минимум: DATABASE_URL, SECRET_KEY, STORAGE_BASE_PATH.
   ⚠️ Критичен именно SECRET_KEY. Ключ шифрования OAuth-токенов выводится как
      `TOKEN_ENCRYPTION_KEY or SECRET_KEY` (app/core/config.py::token_encryption_secret),
      а на проде TOKEN_ENCRYPTION_KEY НЕ задан — значит ключ целиком определяется
      SECRET_KEY. Тот же SECRET_KEY подписывает JWT и подписи медиа-URL.
      Потеря/замена SECRET_KEY ⇒ нерасшифровываемые токены (все компании
      переподключают Яндекс Диск вручную) + разлогин всех сессий.
   Если архива нет — .env только из резервной копии оператора. Восстанавливать
   SECRET_KEY «на глаз» нельзя.

2. Скачать дамп БД ВРУЧНУЮ — через веб-интерфейс Яндекс Диска, не через CLI.
   ⚠️ Ни `backup download` (§3.1), ни кнопка скачивания в админке здесь НЕ помогут:
      обе читают строку из `backup_history`, то есть из той самой потерянной БД.
      Это ограничение осознанное — оно и есть причина, по которой ручной путь
      остаётся в ранбуке. Поэтому папку бэкапов стоит продублировать в офсайт (§10 п. 7).
   - войти в аккаунт Yandex, на который указывает prod-хранилище;
   - папка бэкапов: /vertexart/backups/ (последний успешный артефакт, напр.
     backup_20260915_231904.sql.gz.age);
   - скачать файл и расшифровать:
       age --decrypt --identity /путь/к/arv-backup-age.key \
           --output /tmp/restore.dump.gz backup_20260915_231904.sql.gz.age

3. Создать БД и роль:
   sudo -u postgres psql -c "CREATE ROLE vertex_ar LOGIN PASSWORD '<из .env>'"
   sudo -u postgres createdb -O vertex_ar vertex_ar

4. Восстановить:
   gunzip -c /tmp/restore.dump.gz > /tmp/restore.dump
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
   (в каждом дампе есть колонка backup_history.app_commit)

7. Восстановить медиа из restic. Репозиторий и пароль-файл описаны в .env:
   BACKUP_RESTIC_REPOSITORY / BACKUP_RESTIC_PASSWORD_FILE.
   ⚠️ На проде репозиторий лежит на ТОМ ЖЕ диске, что и медиа
      (/var/backups/arv/restic). Если диск потерян — восстанавливать нечего;
      нужна копия репозитория с другого носителя (см. §10).

       sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; set +a; \
         restic snapshots'                              # найти нужный снапшот
       sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; set +a; \
         restic restore <snapshot_id> --target /opt/arv/storage'
       sudo chown -R arv:arv /opt/arv/storage
       sudo chmod -R a+rX /opt/arv/storage

   Точечно один AR-контент (обычный случай частичной потери):
       restic restore <snapshot_id> \
         --include /VertexAR/<project_slug>/<order_number> --target /tmp/out

8. TLS: сертификаты в архив секретов НЕ попадают (/etc/letsencrypt/live —
   0700 root). Перевыпустить:  certbot renew --force-renewal  (или `certbot certonly`).
   Альтернатива: снять live/archive с живого хоста от root вручную.

9. Поднять сервисы и пройти чек-лист §6.5.
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

## 10. Известные ограничения (проверено на хосте 2026-09-16)

| # | Ограничение | Статус | Последствие | Как закрыть |
|---|---|---|---|---|
| 1 | ~~Медиа не бэкапится~~ | ✅ **закрыто** | — | restic-снапшоты ежедневно 03:30 (`arv-backup-media.timer`), `restic check` еженедельно |
| 2 | ~~Секреты не бэкапятся~~ | ✅ **закрыто** | — | `arv-backup-secrets.timer` (вс 04:00), `tar` + `age`; **но** архив остаётся на хосте — см. п. 7 |
| 3 | ~~Дампы не шифруются~~ | ✅ **закрыто** | — | `BACKUP_AGE_RECIPIENT` задан; приватный ключ **вне** сервера |
| 4 | **Таймер `arv-backup-db` не установлен** | ⏸ решение за оператором | Работает только планировщик внутри приложения: упало приложение — остановились и бэкапы. ~~Включить таймер = два дампа в сутки~~ — **этот риск снят** (2026-09-16): и таймер, и APScheduler берут один и тот же `flock` на `/var/lock/arv-db.lock`, поэтому лишний прогон просто пропускается (§10 п. 18) | Теперь это выбор **только про надёжность**, без риска дублей: таймер переживает падение приложения, APScheduler — нет. Разумный вариант: включить таймер и оставить APScheduler как есть (дубли отсекаются локом). CLI работает без `--company-id`, так что таймер работоспособен |
| 5 | ~~Проверки не автоматизированы~~ | ✅ **закрыто** | — | `arv-backup-verify.timer` (вс 05:00, БД **и** медиа) и `arv-backup-drill.timer` (1-е 06:00) установлены и проверены боевым запуском |
| 6 | ~~`drill` не может создаться БД~~ | ✅ **закрыто** | — | `ALTER ROLE vertex_ar CREATEDB` выдано 2026-09-15 |
| 7 | 🔴 **Второго off-site нет** — `BACKUP_SECONDARY_RCLONE_REMOTE` не задан (механизм при этом проверен, §1.2) | ❌ **открыто — главный оставшийся риск** | Бэкап БД уходит на тот же Яндекс Диск, что и прод-медиа; restic-репозиторий (195 МБ) и архив секретов лежат на **том же диске** `/dev/vda2`, что и прод. Одна точка отказа накрывает всё сразу: потеря аккаунта или диска = потеря и данных, и бэкапов | Осталось только создать получателя: rclone-remote другого провайдера (B2/Selectel) → `BACKUP_SECONDARY_RCLONE_REMOTE`; вынести `BACKUP_RESTIC_REPOSITORY` на внешний backend (`s3:…`), а не в `/var/backups/arv`. Код второй копии уже проверен боевым прогоном (§1.2) |
| 8 | ~~Staging-каталог не создан~~ | ✅ **закрыто** | — | `/var/backups/arv` создан (0700, `arv:arv`) |
| 9 | **Автоматический restore требует живую БД** — `download_backup` читает `companies` из БД | ⚠️ by design | При полной потере БД — только ручной путь (§7) | Дублировать доступ к папке бэкапов и `.env` в офсайт-хранилище оператора |
| 10 | **apt разблокирован, но пакеты не обновлены** — 284 обновляемых, включая безопасность за ~200 дней | ⏸ решение за оператором | Уязвимости ОС не закрыты | Отдельное окно обслуживания с планом отката (`apt-get upgrade`), а не побочный эффект настройки бэкапов |
| 11 | `backup_company_id=4` — единственный получатель | ⚠️ by design | Бэкапы только для VertexART | См. §13.2 п.14 основного документа |
| 12 | **`drill` не проходит автоматически на зашифрованном бэкапе** | ⚠️ by design | Таймер сообщает `no_identity` и не трогает метрику drill — честно, но пригодность бэкапа автоматически **не** доказывается | Прогонять `drill` вручную раз в месяц с примонтированным ключом (§4). Иначе единственная реальная проверка не выполняется |
| 13 | **TLS-сертификаты в архив секретов не попадают** — `/etc/letsencrypt/live`, `archive`, `accounts`, `keys`, `csr` имеют режим `0700 root` | ⚠️ by design | В архиве только `cli.ini` и `renewal/`. При полной потере хоста сертификат нужно перевыпускать | `certbot renew --force-renewal`; либо запускать `deploy/backup/backup-secrets.sh` от root, чтобы забрать и `live/archive` |
| 14 | **Планировщик бэкапа может молча не запуститься** — `init_scheduler()` ловит исключение и логирует `scheduler_init_failed`, приложение при этом стартует нормально | ⚠️ by design (но тихо) | A1 не бэкапится вообще, а «приложение работает» — внешне всё в порядке. Заметно только по `status` через 26 ч или по журналу | Проверка в §2.1 (`grep backup_scheduler_*`). Радикальное лечение — включить `arv-backup-db.timer` вместо APScheduler (см. п. 4) |
| 15 | **Настройки хранения в админке не управляют хранением** — `backup_max_copies=30` / `backup_retention_days=30` показываются, но игнорируются; действует GFS 7/4/12/3 | ❌ **дефект, решение за оператором** | Оператор считает, что у него 30 точек хранения, а фактически 7 ежедневных. Окно восстановления по БД — ~7 дней (§1.1). Изменить окно через UI **нельзя**: `backup_keep_*` не выведены в UI/API, а `BACKUP_KEEP_*` в `.env` не действуют | Считать окно по GFS. Рабочий путь — записать `backup_keep_*` в `system_settings` напрямую. Корректная починка (продуктовое решение): вывести GFS-поля в UI, сделать их `int \| None = None` и убрать мёртвые настройки |
| 16 | **Ротация удаляет строку `backup_history` вместе с артефактом** — `session.delete(record)` | ⚠️ by design | Списка «все бэкапы за всё время» в системе нет; по истории видно только выжившие. Нельзя доказать, что бэкап за конкретную дату когда-то существовал | Вести внешний журнал (или не удалять строку, а помечать `rotated_at`), если это требование аудита |
| 17 | **Скачивание требует живую БД** — и `backup download`, и кнопка в админке читают строку `backup_history` | ⚠️ by design (то же, что п. 9) | При полной потере БД скачать артефакт можно **только** через веб-интерфейс Яндекс Диска | Дублировать папку бэкапов в офсайт-хранилище оператора (§10 п. 7) — тогда файл доступен без БД |
| 18 | ~~Каждый воркер запускал свой бэкап, и копии уничтожали друг друга~~ | ✅ **закрыто** (2026-09-16) | Бэкап **150** имел `status=success`, но его артефакт отдавал 404: два воркера gunicorn считали одно имя файла, загрузили в один ключ, записали две строки истории, а ротация удалила строку вместе с артефактом — оставшаяся строка врала про `success` | Исправлено `JobLock` (общий `flock` на `/var/lock/arv-db.lock` — тот же файл, что и в `backup-db.sh`) + микросекунды в имени артефакта. Проверка — в §2.1 |
| 19 | 🔴 **`/tmp/ARV_deploy.tar.gz` — утечка секретов прода** (305 МБ, `aruser:aruser`, режим `-rw-rw-r--`, т.е. **читаем любым локальным пользователем**, лежит с 2026-08-26) | ❌ **открыто — решение за оператором** | Внутри `.env` с `SECRET_KEY`, `DATABASE_URL`, `ADMIN_DEFAULT_PASSWORD`, `YANDEX_OAUTH_CLIENT_SECRET` и `ssl/privkey.pem` (приватный ключ TLS). Скомпрометированы подпись JWT, ключ шифрования OAuth-токенов (выводится из `SECRET_KEY`), пароль БД, TLS-ключ | Удалить файл **и** ротировать `SECRET_KEY`, пароль БД, перевыпустить сертификат — удаление файла само по себе утечку за 3 недели не отменяет. ⚠️ См. ниже про последствия ротации `SECRET_KEY` для восстановления |

> ⚠️ **Ротация `SECRET_KEY` (п. 19) ломает OAuth-токены в БД.** `token_encryption_secret = TOKEN_ENCRYPTION_KEY or SECRET_KEY`, а `TOKEN_ENCRYPTION_KEY` на проде не задан. Значит все `companies.yandex_disk_token` в БД зашифрованы ключом, производным от **текущего** `SECRET_KEY`. Если его сменить, восстановленная из бэкапа БД будет содержать **нерасшифровываемые** токены → перестанет работать скачивание бэкапов (`download_backup` читает токен из БД) и медиа-прокси.
>
> Порядок при ротации: **сначала вынести `TOKEN_ENCRYPTION_KEY` в `.env`** (зафиксировать текущий ключ шифрования отдельной переменной), **потом** менять `SECRET_KEY`. Иначе единственный путь назад — перевыпуск OAuth-токена Яндекс Диска через админку. Это же требование действует при любом восстановлении (§0 п. 5): `.env` восстанавливать **до** БД.

**Итог.** Бэкап БД, медиа и секретов **создаётся, шифруется, проверяется и восстанавливается**: `verify` автоматизирован (БД + медиа), полное восстановление зашифрованного дампа пройдено end-to-end (§1), архив секретов расшифрован и проверен на содержимое. Все дефекты, которые делали восстановление невозможным, исправлены (§1).

Отдельно стоит помнить **п. 18** — это был дефект особого рода: он не ломал бэкап, он делал **ложно успешный** бэкап. Строка в истории говорила `success`, а файла не было. Такое не видно ни по `status`, ни по алертам, и обнаруживается только `verify` (который и показал `checksum=FAIL`). Поэтому при любом сомнении в свежести бэкапа — сначала `verify --limit N` (§3), и только потом восстановление.

Осталось **одно по-настоящему важное** ограничение — **п. 7**: всё лежит в одном месте. Бэкап, который живёт на том же диске и в том же аккаунте, что и данные, защищает от ошибки оператора, но не от потери диска или аккаунта. Это следующий шаг, и он требует решения оператора (какой провайдер, какие креды).

Остальные открытые пункты — решения оператора, а не дефекты: **4** (таймер vs APScheduler — риск дублей снят, остался выбор по надёжности), **10** (обновление ОС), **12** (ручной drill), **13** (сертификаты), **14** (тихий отказ планировщика — лечится п. 4), **16** (журнал ротации — нужен только для аудита). Отдельно **п. 15** — единственный настоящий дефект в списке: админка обещает одно окно хранения, а действует другое (§1.1).

---

## 11. Шпаргалка: команды

```bash
# --- состояние ---
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; /opt/arv/venv/bin/python -m app.cli.backup status'
systemctl list-timers 'arv-backup-*' --all

# --- проверки (безопасные, прод не трогают) ---
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; /opt/arv/venv/bin/python -m app.cli.backup verify --limit 3'
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; /opt/arv/venv/bin/python -m app.cli.backup verify-media'
# с ключом — тогда toc не skipped:
#   BACKUP_AGE_IDENTITY_FILE=/tmp/arv-age-id.key ... verify --limit 1
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; /opt/arv/venv/bin/python -m app.cli.backup drill --backup-type db'

# --- ВОССТАНОВЛЕНИЕ ОДНОЙ КОМАНДОЙ (рекомендуемый путь) ---
# запускать от aruser: остановка сервиса требует sudo, .env и CLI — пользователя arv
sudo -u aruser /opt/arv/app/deploy/backup/recover.sh --backup-id 148 --target-db vertex_ar_recovered
sudo -u aruser /opt/arv/app/deploy/backup/recover.sh --cutover --target-db vertex_ar_recovered

# --- скачать артефакт вручную (не восстанавливая) ---
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  /opt/arv/venv/bin/python -m app.cli.backup download 148 --output /tmp/'
# или из админки: страница «Бэкапы» → иконка скачивания (только супер-админ)

# --- восстановление в отдельную БД вручную (опасно: пишет данные) ---
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; cd /opt/arv/app; \
  BACKUP_AGE_IDENTITY_FILE=/tmp/arv-age-id.key \
  /opt/arv/venv/bin/python -m app.cli.backup restore 148 --target-db vertex_ar_recovered --create-db'
# или интерактивно:
sudo -u arv /opt/arv/app/deploy/backup/restore.sh --backup-id 148 --target-db vertex_ar_recovered
# список последних бэкапов:
sudo -u arv /opt/arv/app/deploy/backup/restore.sh --list

# --- медиа из restic ---
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; set +a; restic snapshots'
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; set +a; \
  restic restore <snapshot_id> --target /opt/arv/storage'
sudo chown -R arv:arv /opt/arv/storage && sudo chmod -R a+rX /opt/arv/storage

# --- ручной путь (когда БД потеряна) ---
age --decrypt --identity /путь/к/arv-backup-age.key -o /tmp/dump.gz <artifact>.sql.gz.age
gunzip -c /tmp/dump.gz > /tmp/restore.dump
sudo -u postgres pg_restore -j4 --no-owner --exit-on-error -d vertex_ar /tmp/restore.dump
pg_restore --list /tmp/restore.dump | head -50      # посмотреть оглавление без восстановления

# --- диагностика ---
sudo -n journalctl -u arv.service -p warning -n 50 --no-pager
sudo -n journalctl -u arv-backup-media -n 30 --no-pager
sudo -n journalctl -u arv-backup-secrets -n 30 --no-pager
sudo -u postgres psql -d vertex_ar -c "SELECT * FROM backup_history ORDER BY id DESC LIMIT 5"
df -h /var/backups /opt/arv

# --- уже сделано на проде (2026-09-15/16) ---
sudo install -d -m 0700 -o arv -g arv /var/backups/arv
sudo -u postgres psql -c 'ALTER ROLE vertex_ar CREATEDB'
sudo install -m 0644 /opt/arv/app/deploy/systemd/arv-backup-* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now arv-backup-media.timer arv-backup-secrets.timer \
                           arv-backup-verify.timer arv-backup-drill.timer
sudo chmod 0755 /opt/arv/app/deploy/backup/*.sh     # без этого юниты падают с 203/EXEC
systemctl list-timers 'arv-backup-*'

# restic-репозиторий для медиа
sudo mkdir -p /etc/arv && sudo sh -c 'openssl rand -base64 32 > /etc/arv/restic-password'
sudo chown arv:arv /etc/arv/restic-password && sudo chmod 600 /etc/arv/restic-password
sudo -u arv bash -c 'set -a; . /opt/arv/app/.env; set +a; \
  restic init --repo /var/backups/arv/restic --password-file /etc/arv/restic-password'

# шифрование дампов: публичный ключ на хост, приватный — НИКОГДА
sudo -u arv age-keygen            # приватный ключ печатается, на диск не пишется
# → в .env: BACKUP_AGE_RECIPIENT=age1…

# apt был заблокирован зависшим update ~200 дней (устранено 2026-09-16)
sudo systemctl stop apt-daily.service && sudo systemctl reset-failed
sudo apt-get update && sudo apt-get install -y age restic rclone

# проверить юниты боевым запуском (безопасно, прод не трогают)
sudo systemctl start arv-backup-verify.service  && sudo journalctl -u arv-backup-verify  -n 20 --no-pager
sudo systemctl start arv-backup-media.service   && sudo journalctl -u arv-backup-media   -n 20 --no-pager
sudo systemctl start arv-backup-secrets.service && sudo journalctl -u arv-backup-secrets -n 20 --no-pager

# --- тесты: только через раннер, иначе они идут против живого .env ---
cd /opt/arv/app && ARV_PYTHON=/opt/arv/venv/bin/python bash scripts/run_tests.sh tests -q --no-cov
```

**Значения по умолчанию, о которые спотыкаются:**
`BACKUP_STAGING_DIR=/var/backups/arv` · `BACKUP_RESTORE_JOBS=4` · `BACKUP_DRILL_DB_PREFIX=arv_drill` · `BACKUP_MAX_AGE_HOURS=26` · `BACKUP_SECRETS_MAX_AGE_HOURS=192` (секреты недельные — суточный лимит давал бы ложный `STALE` 6 дней из 7) · **хранение: GFS `7/4/12/3` (`DEFAULT_KEEP_DAILY/WEEKLY/MONTHLY/YEARLY`), `backup_max_copies` и `backup_retention_days` из админки НЕ действуют (§1.1)** · таймауты: decrypt/restore 3600 с, `--list` 600 с, media-снапшот 6 ч · артефакт БД: `backup_<ts>.sql.gz.age` (внутри — custom-format `-Fc`, восстанавливается **только** через `pg_restore`) · `--trigger` — **top-level** аргумент CLI, до подкоманды · `verify` проверяет **только** тип `db`; медиа проверяется `verify-media` (`restic check`), потому что у медиа-строки нет ни `yd_path`, ни `checksum` · `arv` **не** имеет NOPASSWD sudo (в отличие от `aruser`), поэтому `sudo -u postgres psql` из-под `arv` не сработает.
