"""
migrate.py — اضافه کردن ستون‌های پریمیوم به جدول users موجود
اجرا: python migrate.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("studybot.db")

MIGRATIONS = [
    # ستون‌هایی که ممکنه در جدول قدیمی باشن ولی در model جدید نیستن
    # → نگهشون می‌داریم تا داده از دست نره

    # ستون‌هایی که باید اضافه بشن اگه نیستن:
    ("subscriptions", None),  # جدول جدید — از SQLAlchemy ساخته می‌شه
]

COLUMNS_TO_ADD = {
    "users": [
        # (column_name, definition)
        ("is_premium",     "INTEGER NOT NULL DEFAULT 0"),
        ("premium_expire", "TEXT"),
        ("plan_type",      "TEXT"),
        ("telegram_id",    "INTEGER"),
        ("is_active",      "INTEGER NOT NULL DEFAULT 1"),
        ("daily_goal_minutes", "INTEGER NOT NULL DEFAULT 60"),
        ("updated_at",     "TEXT"),
    ]
}


def get_existing_columns(cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def get_existing_tables(cursor) -> set[str]:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cursor.fetchall()}


def run():
    if not DB_PATH.exists():
        print(f"❌ فایل {DB_PATH} پیدا نشد — اول python main.py رو اجرا کن تا دیتابیس ساخته بشه.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    tables = get_existing_tables(cur)
    print(f"📋 جداول موجود: {tables}")

    for table, columns in COLUMNS_TO_ADD.items():
        if table not in tables:
            print(f"⚠️  جدول {table} وجود نداره — رد شد")
            continue

        existing = get_existing_columns(cur, table)
        for col_name, col_def in columns:
            if col_name not in existing:
                sql = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"
                cur.execute(sql)
                print(f"✅ اضافه شد: {table}.{col_name}")
            else:
                print(f"⏭️  موجوده: {table}.{col_name}")

    conn.commit()
    conn.close()
    print("\n🎉 Migration کامل شد!")


if __name__ == "__main__":
    run()
