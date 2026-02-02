"""Проверка таблиц SQLite БД (vertex_ar.db)."""
import os
import sqlite3
import sys

DB_PATH = os.environ.get("SQLITE_DB", "vertex_ar.db")


def main() -> None:
    if not os.path.exists(DB_PATH):
        print(f"Файл {DB_PATH} не найден.")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [r[0] for r in cur.fetchall()]
    print(f"Таблицы: {len(tables)}")
    for t in tables:
        cur = conn.execute(f'SELECT COUNT(*) FROM "{t}"')
        n = cur.fetchone()[0]
        print(f"  {t}: {n} записей")
    conn.close()


if __name__ == "__main__":
    main()
