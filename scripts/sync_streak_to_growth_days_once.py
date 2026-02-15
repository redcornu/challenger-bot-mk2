#!/usr/bin/env python3
"""One-time migration: set streak to growth_days for all challenges."""

import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv


MIGRATION_KEY = "one_time_sync_streak_to_growth_days_20260215"


def get_db_path() -> str:
    load_dotenv()
    return os.getenv("DB_PATH", "data/bot.db")


def ensure_system_config_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )


def main() -> int:
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"ERROR: database not found: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        ensure_system_config_table(cursor)

        cursor.execute("SELECT value FROM system_config WHERE key = ?", (MIGRATION_KEY,))
        already_applied = cursor.fetchone()
        if already_applied:
            print("SKIP: migration already applied once.")
            print(f"INFO: key={MIGRATION_KEY}, value={already_applied[0]}")
            return 0

        cursor.execute(
            """
            UPDATE duck_challenge
            SET streak = growth_days
            WHERE COALESCE(streak, -1) <> COALESCE(growth_days, -1)
            """
        )
        affected_rows = cursor.rowcount

        applied_at = datetime.now().isoformat(timespec="seconds")
        meta = f"applied_at={applied_at}, affected_rows={affected_rows}"
        cursor.execute(
            "INSERT INTO system_config (key, value) VALUES (?, ?)",
            (MIGRATION_KEY, meta),
        )

        conn.commit()
        print("DONE: streak synced to growth_days.")
        print(f"INFO: affected_rows={affected_rows}")
        print(f"INFO: migration_key={MIGRATION_KEY}")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: migration failed: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
